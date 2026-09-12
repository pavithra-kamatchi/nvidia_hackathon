from datetime import datetime
from typing import List

from pydantic import BaseModel


class Assignment(BaseModel):
    assignment_id: str
    incident_id: str
    assigned_station_ids: List[str]
    rationale: str
    escalate_to_911: bool
    requires_multi_station: bool
    status: str
    accepted_station_ids: List[str]
    rejected_station_ids: List[str]
    created_at: datetime
