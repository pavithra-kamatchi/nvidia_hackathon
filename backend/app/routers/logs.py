from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.agents.monitoring import monitoring_agent
from app.repositories.collections import incident_repo
from app.repositories.collections import log_repo
from app.schemas.log import LogEntry

router = APIRouter(tags=["logs"])


@router.get("/logs", response_model=List[LogEntry])
async def list_logs(incident_id: Optional[str] = None):
    query = {"incident_id": incident_id} if incident_id else {}
    return await log_repo.list(query, sort_field="timestamp")


@router.get("/incidents/{incident_id}/timeline", response_model=List[LogEntry])
async def incident_timeline(incident_id: str):
    if await incident_repo.get(incident_id) is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    entries = await log_repo.list({"incident_id": incident_id}, sort_field="timestamp")
    return list(reversed(entries))


@router.get("/incidents/{incident_id}/final-report")
async def final_report(incident_id: str):
    if await incident_repo.get(incident_id) is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return await monitoring_agent.compile_report(incident_id)
