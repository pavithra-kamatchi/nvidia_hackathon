from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import Coordinate, PoseLabel


class Pose(BaseModel):
    """Agent 1 (Perception Agent) output: one entry per detected person."""

    pose: PoseLabel
    confidence: float
    image_url: str
    coordinate: Coordinate

    # System-managed fields needed to persist/link poses in Mongo. Not part of
    # the spec's minimal Pose shape, but required so poses can be stored and
    # traced back to the frame/detection they came from.
    pose_id: str
    timestamp: datetime
    detection_id: Optional[str] = None
