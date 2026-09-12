"""Agent 1 (Perception Agent) — person/pose localization.

SWAP-IN POINT: replace `MockPoseDetector` with a local inference wrapper
around a YOLO26/YOLOv11 checkpoint fine-tuned on C2A (+ VisDrone), loaded
from a local weights file (e.g. `ultralytics.YOLO("weights/c2a_yolo11.pt")`).
Everything downstream only depends on this class returning
`List[RawPoseDetection]`, so the swap requires no other changes.
"""

import hashlib
import random
from dataclasses import dataclass
from typing import List

from app.schemas.common import PoseLabel

_POSE_LABELS = list(PoseLabel)


@dataclass
class RawPoseDetection:
    pose: PoseLabel
    confidence: float


class MockPoseDetector:
    """Deterministic per-image mock: same image bytes always yield the same
    fake detections, so demo runs are reproducible without a real model."""

    def detect(self, image_bytes: bytes) -> List[RawPoseDetection]:
        rng = random.Random(hashlib.sha256(image_bytes).digest())
        num_people = rng.choices([0, 1, 2, 3], weights=[0.15, 0.45, 0.25, 0.15])[0]
        return [
            RawPoseDetection(
                pose=rng.choice(_POSE_LABELS),
                confidence=round(rng.uniform(0.55, 0.97), 2),
            )
            for _ in range(num_people)
        ]


pose_detector = MockPoseDetector()
