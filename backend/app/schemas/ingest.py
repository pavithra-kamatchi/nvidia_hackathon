from typing import Optional

from pydantic import BaseModel

from app.schemas.assignment import Assignment
from app.schemas.incident import Incident
from app.schemas.triage import Assessment, Detection


class IngestResponse(BaseModel):
    detection: Detection
    assessment: Assessment
    incident: Incident
    assignment: Optional[Assignment] = None
