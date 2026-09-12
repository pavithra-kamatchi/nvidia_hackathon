from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import Coordinate, IncidentStatus, Urgency


class Incident(BaseModel):
    incident_id: str
    location: Coordinate
    incident_type: str
    urgency: Urgency
    status: IncidentStatus
    number_of_people: int
    first_uploaded: datetime
    last_updated: datetime
    needs_human_verification: bool
    image_url: Optional[str] = None
