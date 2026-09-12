from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class LogEntry(BaseModel):
    log_id: str
    timestamp: datetime
    incident_id: Optional[str] = None
    actor_type: str = "system"
    actor_id: Optional[str] = None
    event_type: str
    summary: str
    payload: Dict[str, Any]
