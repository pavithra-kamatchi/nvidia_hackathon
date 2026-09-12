from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, model_validator

from app.schemas.assignment import Assignment
from app.schemas.common import Coordinate, Urgency
from app.schemas.incident import Incident
from app.schemas.triage import Assessment, Detection


class PerceptionHandoff(BaseModel):
    detection_id: str
    timestamp: datetime
    location: Coordinate
    human_detected: bool
    number_of_people: int = Field(ge=0)
    injury_status: str
    visible_hazards: Union[str, List[str]]
    observations: str
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def check_human_count(self):
        if not self.human_detected and self.number_of_people != 0:
            raise ValueError("number_of_people must be zero when human_detected is false")
        return self


class TriageHandoff(BaseModel):
    urgency: Urgency
    incident_type: str
    location: Coordinate
    observations: str
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human_verification: bool


class AgentHandoffRequest(BaseModel):
    perception: PerceptionHandoff
    triage: TriageHandoff

    @model_validator(mode="after")
    def check_matching_locations(self):
        p, t = self.perception.location, self.triage.location
        if abs(p.latitude - t.latitude) > 1e-6 or abs(p.longitude - t.longitude) > 1e-6:
            raise ValueError("Perception and Triage locations must match")
        return self


class AgentHandoffResponse(BaseModel):
    detection: Detection
    assessment: Assessment
    incident: Incident
    assignment: Optional[Assignment] = None
    warnings: List[str]
