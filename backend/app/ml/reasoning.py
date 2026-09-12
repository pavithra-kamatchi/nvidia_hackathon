"""Local Nemotron reasoning adapter for incident triage.

Nemotron receives structured visual evidence and returns a concise assessment.
Deterministic checks remain authoritative for safety and provide a usable
fallback when the local model is stopped (for example, during YOLO training).
"""

import json
import logging
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse

from app.config import settings
from app.ml.detector import RawPoseDetection
from app.schemas.common import Urgency
from app.schemas.triage import Assessment, Detection

logger = logging.getLogger(__name__)
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass
class ReasoningResult:
    urgency: Urgency
    incident_type: str
    observation_and_reasoning: str
    confidence: float
    needs_human_verification: bool


def _require_local_endpoint() -> None:
    parsed = urlparse(settings.nemotron_url)
    if parsed.scheme != "http" or parsed.hostname not in _LOOPBACK_HOSTS:
        raise ValueError("NEMOTRON_URL must be a local loopback HTTP endpoint")


def _extract_json(content: str) -> dict:
    decoder = json.JSONDecoder()
    for index, character in enumerate(content):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(content[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("Local reasoner did not return a JSON object")


def _has_reported_hazard(visible_hazards: str) -> bool:
    hazard = visible_hazards.strip().lower()
    return hazard not in ("", "none", "none visible", "unclear", "unknown")


def _deterministic_assessment(
    detection: Detection,
    poses: List[RawPoseDetection],
    prior_assessments: Optional[List[Assessment]],
) -> ReasoningResult:
    concerning = [
        pose.pose.value
        for pose in poses
        if pose.pose.value in ("lying", "kneeling", "bent")
    ]
    has_hazard = _has_reported_hazard(detection.visible_hazards)
    reasons: List[str] = []

    if detection.blood:
        urgency, incident_type = Urgency.high, "injury"
        reasons.append("visible blood-like material was reported by the vision step")
    elif concerning:
        urgency = Urgency.high if len(concerning) >= 2 else Urgency.medium
        incident_type = "injury"
        reasons.append(f"{len(concerning)} non-upright pose detection(s): {', '.join(concerning)}")
    elif detection.human and has_hazard:
        urgency, incident_type = Urgency.medium, "person_near_hazard"
        reasons.append(f"a person was reported near this visible hazard: {detection.visible_hazards}")
    elif detection.human:
        urgency, incident_type = Urgency.low, "person_detected"
        reasons.append("a person was detected without a reported immediate hazard")
    elif has_hazard:
        urgency, incident_type = Urgency.unclear, "hazard_no_person"
        reasons.append(f"a hazard was reported without a person: {detection.visible_hazards}")
    else:
        urgency, incident_type = Urgency.unclear, "unclear"
        reasons.append("available evidence does not establish a person or visible hazard")

    confidence = round(min(detection.confidence * 0.95, 1.0), 2)
    if prior_assessments:
        # Repository results are newest-first.
        latest = prior_assessments[0]
        if latest.urgency != urgency:
            reasons.append(
                f"urgency changed from {latest.urgency.value} to {urgency.value}"
            )
    needs_human = (
        urgency in (Urgency.high, Urgency.unclear)
        or confidence < settings.confidence_threshold
    )
    return ReasoningResult(
        urgency=urgency,
        incident_type=incident_type,
        observation_and_reasoning="; ".join(reasons) + ".",
        confidence=confidence,
        needs_human_verification=needs_human,
    )


class LocalNemotronReasoner:
    def __init__(self) -> None:
        self._cache: Dict[str, ReasoningResult] = {}

    def assess(
        self,
        detection: Detection,
        poses: List[RawPoseDetection],
        prior_assessments: Optional[List[Assessment]] = None,
    ) -> ReasoningResult:
        _require_local_endpoint()
        # Triage currently invokes assess twice while resolving an existing
        # incident. Reuse the first answer to avoid duplicate GPU inference.
        if detection.detection_id in self._cache:
            return self._cache[detection.detection_id]

        fallback = _deterministic_assessment(detection, poses, prior_assessments)
        evidence = {
            "human": detection.human,
            "number_of_people": detection.number_of_people,
            "visible_blood": detection.blood,
            "visible_hazards": detection.visible_hazards,
            "observations": detection.observations,
            "vision_confidence": detection.confidence,
            "poses": [
                {"label": pose.pose.value, "confidence": pose.confidence}
                for pose in poses
            ],
            "previous_urgency": (
                prior_assessments[0].urgency.value if prior_assessments else None
            ),
        }
        prompt = (
            "Classify this emergency observation using only the supplied evidence. Do not make a "
            "medical diagnosis and do not claim facts not present in the evidence. Return exactly "
            "one JSON object with: urgency (high, medium, low, or unclear), incident_type (short "
            "snake_case string), reasoning (one or two concise evidence-based sentences), "
            "confidence (0 to 1), needs_human_verification (boolean). Use unclear and require human "
            "verification when evidence is insufficient or conflicting. Evidence: "
            + json.dumps(evidence)
        )
        body = json.dumps(
            {
                "model": settings.nemotron_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 260,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            settings.nemotron_url,
            data=body,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(
                request, timeout=settings.nemotron_timeout_seconds
            ) as response:
                response_body = json.load(response)
            payload = _extract_json(response_body["choices"][0]["message"]["content"])
            urgency = Urgency(str(payload["urgency"]).lower())
            incident_type = str(payload["incident_type"]).strip().lower().replace(" ", "_")
            reasoning = str(payload["reasoning"]).strip()
            confidence = float(payload["confidence"])
            model_requires_human = payload["needs_human_verification"]
            if not incident_type or not reasoning:
                raise ValueError("incident_type and reasoning cannot be empty")
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("confidence must be between 0 and 1")
            if not isinstance(model_requires_human, bool):
                raise ValueError("needs_human_verification must be boolean")

            # Deterministic safety rules override any less-cautious model result.
            evidence_conflict = (
                urgency == Urgency.low
                and (
                    detection.blood
                    or _has_reported_hazard(detection.visible_hazards)
                    or bool(poses)
                    and any(
                        pose.pose.value in ("lying", "kneeling", "bent") for pose in poses
                    )
                )
            )
            if evidence_conflict:
                if _has_reported_hazard(detection.visible_hazards) and not detection.blood:
                    urgency = Urgency.medium
                    if incident_type == "person_detected":
                        incident_type = "person_near_hazard"
                else:
                    urgency = Urgency.unclear
                reasoning += " The low-urgency classification conflicts with visible hazard or injury evidence."
            needs_human = (
                model_requires_human
                or evidence_conflict
                or urgency in (Urgency.high, Urgency.unclear)
                or confidence < settings.confidence_threshold
                or detection.confidence < settings.confidence_threshold
            )
            result = ReasoningResult(
                urgency=urgency,
                incident_type=incident_type,
                observation_and_reasoning=reasoning,
                confidence=confidence,
                needs_human_verification=needs_human,
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Local reasoner unavailable or invalid; using deterministic rules: %s", exc)
            result = fallback

        if len(self._cache) >= 256:
            self._cache.pop(next(iter(self._cache)))
        self._cache[detection.detection_id] = result
        return result


reasoner = LocalNemotronReasoner()
