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
    # AI classification is uncertain (high/unclear urgency or low confidence)
    # and needs an operator to confirm/override it before it reaches stations.
    needs_review = "needs_review"
    # Allocation proposed and posted to the dispatch queue; waiting for a
    # station to accept and commit to dispatching responders.
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
