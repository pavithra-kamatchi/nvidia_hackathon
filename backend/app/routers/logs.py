from typing import List, Optional

from fastapi import APIRouter

from app.repositories.collections import log_repo
from app.schemas.log import LogEntry

router = APIRouter(tags=["logs"])


@router.get("/logs", response_model=List[LogEntry])
async def list_logs(incident_id: Optional[str] = None):
    query = {"incident_id": incident_id} if incident_id else {}
    return await log_repo.list(query, sort_field="timestamp")
