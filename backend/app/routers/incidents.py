from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.monitoring import monitoring_agent
from app.repositories.collections import assignment_repo, incident_repo, station_repo
from app.schemas.common import IncidentStatus, Urgency
from app.schemas.incident import Incident

router = APIRouter(tags=["incidents"])


@router.get("/incidents", response_model=List[Incident])
async def list_incidents(status: Optional[IncidentStatus] = None, urgency: Optional[Urgency] = None):
    query = {}
    if status is not None:
        query["status"] = status.value
    if urgency is not None:
        query["urgency"] = urgency.value
    return await incident_repo.list(query, sort_field="last_updated")


@router.get("/incidents/{incident_id}", response_model=Incident)
async def get_incident(incident_id: str):
    incident = await incident_repo.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


class ReviewRequest(BaseModel):
    approved: bool
    override_urgency: Optional[Urgency] = None
    notes: Optional[str] = None


@router.post("/incidents/{incident_id}/review", response_model=Incident)
async def review_incident(incident_id: str, payload: ReviewRequest):
    """Human-in-the-loop checkpoint for any incident sitting at
    awaiting_approval (forced there by high/unclear urgency or low
    confidence)."""
    incident = await incident_repo.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    if not payload.approved:
        incident.status = IncidentStatus.false_positive
    else:
        if payload.override_urgency is not None:
            incident.urgency = payload.override_urgency
        incident.status = IncidentStatus.in_progress if incident.urgency == Urgency.unclear else IncidentStatus.notified
        incident.needs_human_verification = False

    incident.last_updated = datetime.now(timezone.utc)
    await incident_repo.replace(incident)
    await monitoring_agent.log(
        "human_reviewed",
        f"Incident {incident_id} reviewed: approved={payload.approved}, notes={payload.notes or ''}".strip(),
        incident_id=incident_id,
        payload={"approved": payload.approved, "notes": payload.notes},
    )
    return incident


class DispatchRequest(BaseModel):
    station_ids: List[str]


@router.post("/incidents/{incident_id}/dispatch", response_model=Incident)
async def dispatch_incident(incident_id: str, payload: DispatchRequest):
    """Marks the incident (and its latest Assignment) as dispatched, and
    commits the chosen stations by adding this incident to their
    current_deployments."""
    incident = await incident_repo.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    assignments = await assignment_repo.list({"incident_id": incident_id}, sort_field="created_at")
    if assignments:
        assignment = assignments[0]
        assignment.status = "dispatched"
        assignment.accepted_station_ids = payload.station_ids
        await assignment_repo.replace(assignment)

    for station_id in payload.station_ids:
        station = await station_repo.get(station_id)
        if station is None:
            continue
        if incident_id not in station.current_deployments:
            station.current_deployments.append(incident_id)
            await station_repo.replace(station)

    incident.status = IncidentStatus.dispatched
    incident.last_updated = datetime.now(timezone.utc)
    await incident_repo.replace(incident)
    await monitoring_agent.log(
        "dispatched",
        f"Station(s) {payload.station_ids} dispatched to incident {incident_id}.",
        incident_id=incident_id,
        payload={"station_ids": payload.station_ids},
    )
    return incident


@router.post("/incidents/{incident_id}/resolve", response_model=Incident)
async def resolve_incident(incident_id: str):
    incident = await incident_repo.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident.status = IncidentStatus.resolved
    incident.last_updated = datetime.now(timezone.utc)
    await incident_repo.replace(incident)

    all_assignments = await assignment_repo.list({"incident_id": incident_id})
    for assignment in all_assignments:
        assignment.status = "resolved"
        await assignment_repo.replace(assignment)

    stations = await station_repo.list()
    for station in stations:
        if incident_id in station.current_deployments:
            station.current_deployments.remove(incident_id)
            await station_repo.replace(station)

    await monitoring_agent.log("resolved", f"Incident {incident_id} resolved.", incident_id=incident_id)
    await monitoring_agent.save_report(incident_id)
    return incident


@router.get("/incidents/{incident_id}/report")
async def get_incident_report(incident_id: str):
    incident = await incident_repo.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return await monitoring_agent.compile_report(incident_id)
