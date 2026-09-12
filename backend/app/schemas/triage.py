from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import Coordinate, Urgency


class Detection(BaseModel):
    """Output of the first-level VLM step inside the Triage Agent."""

    detection_id: str
    timestamp: datetime
    location: Coordinate
    human: bool
    blood: bool
    number_of_people: int
    injured: bool
    visible_hazards: str
    observations: str
    confidence: float = Field(ge=0.0, le=1.0)
    image_url: Optional[str] = None


class Assessment(BaseModel):
    """Output of the second-level reasoning step (Nemotron) inside the Triage Agent."""

    assessment_id: str
    incident_id: str
    detection_id: str
    timestamp: datetime
    urgency: Urgency
    incident_type: str
    observation_and_reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human_verification: bool
