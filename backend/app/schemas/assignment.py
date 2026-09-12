from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class Assignment(BaseModel):
    assignment_id: str
    incident_id: str
    assigned_station_ids: List[str]
    recommended_resources: Dict[str, int]
    priority: int
    rationale: str
    escalate_to_911: bool
    requires_multi_station: bool
    requires_additional_support: bool
    needs_human_approval: bool = True
    status: str
    accepted_station_ids: List[str]
    rejected_station_ids: List[str]
    created_at: datetime
    decision: Optional[str] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
