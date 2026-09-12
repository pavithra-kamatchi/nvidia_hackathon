"""Triage Agent, step B — second-level reasoning LLM.

SWAP-IN POINT: replace `MockReasoner` with a local Nemotron checkpoint call,
fed the image plus Agent 1/step-A's structured JSON (never the raw image
alone), prompted to always produce the `observation_and_reasoning` trace.
Everything downstream only depends on this class's return shape.
"""

from dataclasses import dataclass
from typing import List, Optional

from app.config import settings
from app.ml.detector import RawPoseDetection
from app.schemas.common import Urgency
from app.schemas.triage import Assessment, Detection


@dataclass
class ReasoningResult:
    urgency: Urgency
    incident_type: str
    observation_and_reasoning: str
    confidence: float
    needs_human_verification: bool


class MockReasoner:
    def assess(
        self,
        detection: Detection,
        poses: List[RawPoseDetection],
        prior_assessments: Optional[List[Assessment]] = None,
    ) -> ReasoningResult:
        prior_assessments = prior_assessments or []
        concerning_poses = [p.pose.value for p in poses if p.pose.value in ("lying", "kneeling", "bent")]

        reasons = []
        if detection.blood:
            urgency = Urgency.high
            incident_type = "injury"
            reasons.append("visible blood was flagged by the vision step")
        elif concerning_poses:
            urgency = Urgency.high if len(concerning_poses) >= 2 else Urgency.medium
            incident_type = "injury"
            reasons.append(f"{len(concerning_poses)} person(s) in non-upright posture ({', '.join(concerning_poses)})")
        elif detection.human and detection.visible_hazards != "none visible":
            urgency = Urgency.medium
            incident_type = "person_near_hazard"
            reasons.append(f"person present near reported hazard: {detection.visible_hazards}")
        elif detection.human:
            urgency = Urgency.low
            incident_type = "person_detected"
            reasons.append("person detected, no immediate hazard or injury signal")
        elif detection.visible_hazards != "none visible":
            urgency = Urgency.unclear
            incident_type = "hazard_no_person"
            reasons.append(f"hazard reported with no person in frame: {detection.visible_hazards}")
        else:
            urgency = Urgency.unclear
            incident_type = "unclear"
            reasons.append("no person or hazard clearly identified")

        if prior_assessments:
            last = prior_assessments[-1]
            if last.urgency != urgency:
                reasons.append(f"urgency changed from prior reading '{last.urgency.value}' to '{urgency.value}'")

        confidence = round(detection.confidence * 0.95, 2)

        needs_human_verification = (
            urgency in (Urgency.high, Urgency.unclear)
            or confidence < settings.confidence_threshold
        )

        observation_and_reasoning = (
            f"Detection confidence {detection.confidence:.2f}. " + "; ".join(reasons) + "."
        )

        return ReasoningResult(
            urgency=urgency,
            incident_type=incident_type,
            observation_and_reasoning=observation_and_reasoning,
            confidence=confidence,
            needs_human_verification=needs_human_verification,
        )


reasoner = MockReasoner()
