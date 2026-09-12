from enum import Enum

from pydantic import BaseModel


class Coordinate(BaseModel):
    latitude: float
    longitude: float


class Urgency(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"
    unclear = "unclear"


class IncidentStatus(str, Enum):
    new = "new"
    awaiting_approval = "awaiting_approval"
    notified = "notified"
    dispatched = "dispatched"
    in_progress = "in_progress"
    resolved = "resolved"
    false_positive = "false_positive"


class PoseLabel(str, Enum):
    lying = "lying"
    sitting = "sitting"
    bent = "bent"
    kneeling = "kneeling"
    upright = "upright"
