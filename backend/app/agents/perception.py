from datetime import datetime
from typing import List

from app.ml.detector import pose_detector
from app.repositories.collections import pose_repo
from app.schemas.common import Coordinate
from app.schemas.perception import Pose
from app.utils.ids import generate_id


class PerceptionAgent:
    """Agent 1. Stateless per-frame: no memory of prior frames, no urgency
    or incident-type decisions — those belong to the Triage Agent."""

    async def run(self, image_bytes: bytes, image_url: str, coordinate: Coordinate, timestamp: datetime) -> List[Pose]:
        raw_detections = pose_detector.detect(image_bytes)
        poses: List[Pose] = []
        for raw in raw_detections:
            pose = Pose(
                pose=raw.pose,
                confidence=raw.confidence,
                image_url=image_url,
                coordinate=coordinate,
                pose_id=generate_id("pose", timestamp),
                timestamp=timestamp,
            )
            await pose_repo.insert(pose)
            poses.append(pose)
        return poses


perception_agent = PerceptionAgent()
