"""Triage Agent, step A — first-level VLM.

SWAP-IN POINT: replace `MockVisionDescriber` with a local call to a small
VLM (e.g. Qwen3-VL-4B/2B) loaded from local weights, prompted with the crop +
full frame and constrained to JSON output matching `VisionDescription`.
Everything downstream only depends on this class's return shape.
"""

import hashlib
import random
from dataclasses import dataclass
from typing import List

from app.ml.detector import RawPoseDetection


@dataclass
class VisionDescription:
    human: bool
    blood: bool
    number_of_people: int
    visible_hazards: str
    observations: str
    confidence: float


class MockVisionDescriber:
    def describe(self, image_bytes: bytes, poses: List[RawPoseDetection]) -> VisionDescription:
        rng = random.Random(hashlib.sha256(image_bytes + b"vlm").digest())
        number_of_people = len(poses)
        human = number_of_people > 0
        blood = human and rng.random() < 0.2
        concerning_poses = [p.pose.value for p in poses if p.pose.value in ("lying", "kneeling", "bent")]

        if not human:
            visible_hazards = rng.choice(["none visible", "debris field", "downed power line"])
            observations = "No person detected in frame."
        else:
            visible_hazards = rng.choice(["structural debris nearby", "standing water", "none visible", "fire/smoke in background"])
            pose_desc = ", ".join(p.pose.value for p in poses)
            observations = f"Detected {number_of_people} person(s); pose(s): {pose_desc}."
            if concerning_poses:
                observations += f" {len(concerning_poses)} in a non-upright posture consistent with possible injury."
            if blood:
                observations += " Discoloration consistent with visible blood observed near subject."

        base_conf = sum(p.confidence for p in poses) / number_of_people if number_of_people else 0.75
        confidence = round(min(0.98, max(0.4, base_conf + rng.uniform(-0.05, 0.05))), 2)

        return VisionDescription(
            human=human,
            blood=blood,
            number_of_people=number_of_people,
            visible_hazards=visible_hazards,
            observations=observations,
            confidence=confidence,
        )


vision_describer = MockVisionDescriber()
