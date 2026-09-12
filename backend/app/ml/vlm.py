"""Local vision-language adapter used by the Triage Agent.

The adapter sends the actual image to the OpenAI-compatible Nemotron endpoint
running on the GB10. Network policy is enforced in code: only loopback HTTP
URLs are accepted. If local inference is unavailable or returns invalid JSON,
the fallback reports only facts supplied by the person detector and never
invents a hazard or injury.
"""

import base64
import json
import logging
import urllib.request
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse

from app.config import settings
from app.ml.detector import RawPoseDetection

logger = logging.getLogger(__name__)
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass
class VisionDescription:
    human: bool
    blood: bool
    number_of_people: int
    visible_hazards: str
    observations: str
    confidence: float


def _require_local_endpoint() -> None:
    parsed = urlparse(settings.nemotron_url)
    if parsed.scheme != "http" or parsed.hostname not in _LOOPBACK_HOSTS:
        raise ValueError("NEMOTRON_URL must be a local loopback HTTP endpoint")


def _image_mime(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


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
    raise ValueError("Local VLM did not return a JSON object")


def _bounded_confidence(value: object) -> float:
    confidence = float(value)
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    return confidence


class LocalNemotronVisionDescriber:
    def describe(self, image_bytes: bytes, poses: List[RawPoseDetection]) -> VisionDescription:
        _require_local_endpoint()
        if not image_bytes:
            return self._detector_only_fallback(poses, "Image was empty")

        pose_evidence = [
            {"pose": pose.pose.value, "confidence": pose.confidence}
            for pose in poses
        ]
        prompt = (
            "Analyze only visible evidence in this drone image. Do not make a medical diagnosis "
            "and do not infer hidden injuries. Detector results are supporting evidence and may be "
            "wrong: " + json.dumps(pose_evidence) + ". Return exactly one JSON object with keys: "
            "human (boolean), number_of_people (nonnegative integer), visible_blood (boolean; true "
            "only for clearly visible blood-like material), visible_hazards (string), observations "
            "(short factual string), confidence (number from 0 to 1). Use 'none visible' only when "
            "the image clearly shows no hazard; use 'unclear' when visibility is insufficient."
        )
        data_url = (
            f"data:{_image_mime(image_bytes)};base64,"
            + base64.b64encode(image_bytes).decode("ascii")
        )
        body = json.dumps(
            {
                "model": settings.nemotron_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                "temperature": 0,
                "max_tokens": 300,
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
                result = json.load(response)
            payload = _extract_json(result["choices"][0]["message"]["content"])
            human = payload["human"]
            visible_blood = payload.get("visible_blood", False)
            if not isinstance(human, bool) or not isinstance(visible_blood, bool):
                raise ValueError("human and visible_blood must be booleans")
            number_of_people = int(payload["number_of_people"])
            if number_of_people < 0 or (not human and number_of_people != 0):
                raise ValueError("invalid human count")
            hazards = str(payload["visible_hazards"]).strip()
            observations = str(payload["observations"]).strip()
            if not hazards or not observations:
                raise ValueError("hazards and observations cannot be empty")
            return VisionDescription(
                human=human,
                blood=visible_blood,
                number_of_people=number_of_people,
                visible_hazards=hazards,
                observations=observations,
                confidence=_bounded_confidence(payload["confidence"]),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Local VLM unavailable or invalid; using detector-only evidence: %s", exc)
            return self._detector_only_fallback(poses, "Local VLM result unavailable")

    @staticmethod
    def _detector_only_fallback(
        poses: List[RawPoseDetection], reason: str
    ) -> VisionDescription:
        count = len(poses)
        pose_names = ", ".join(pose.pose.value for pose in poses)
        observations = (
            f"Person detector reported {count} person(s)"
            + (f" with pose label(s): {pose_names}." if pose_names else ".")
            + f" {reason}; hazards and injury indicators were not assessed."
        )
        detector_confidence = (
            sum(pose.confidence for pose in poses) / count if count else 0.0
        )
        return VisionDescription(
            human=count > 0,
            blood=False,
            number_of_people=count,
            visible_hazards="unclear",
            observations=observations,
            confidence=round(min(detector_confidence, 0.69), 2),
        )


vision_describer = LocalNemotronVisionDescriber()
