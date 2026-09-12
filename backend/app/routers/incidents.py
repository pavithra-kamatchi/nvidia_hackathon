from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.coordinator import coordinator_agent
from app.agents.monitoring import monitoring_agent
from app.agents.notification import notification_agent
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
    operator_id: str
    override_urgency: Optional[Urgency] = None
    notes: Optional[str] = None


@router.post("/incidents/{incident_id}/review", response_model=Incident)
async def review_incident(incident_id: str, payload: ReviewRequest):
    """Human-in-the-loop checkpoint for any incident sitting at
    needs_review (forced there by high/unclear urgency or low confidence).

    Approval confirms/overrides the AI classification and sends the incident
    through the Coordinator/Notification agents so it lands in the station
    dispatch queue (awaiting_approval); rejection marks it a false positive.
    """
    incident = await incident_repo.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    previous_status = incident.status.value
    if not payload.approved:
        incident.status = IncidentStatus.false_positive
        incident.last_updated = datetime.now(timezone.utc)
        await incident_repo.replace(incident)
    else:
        if payload.override_urgency is not None:
            incident.urgency = payload.override_urgency
        # Verifying the observation does not approve or notify the proposed
        # allocation. Those are separate, explicit human-controlled actions.
        incident.status = IncidentStatus.awaiting_approval
        incident.needs_human_verification = False
        incident.last_updated = datetime.now(timezone.utc)
        await incident_repo.replace(incident)
        assignment = await coordinator_agent.run(incident)
        incident = await notification_agent.run(incident, assignment)

    await monitoring_agent.log(
        "human_reviewed",
        f"Incident {incident_id} reviewed: approved={payload.approved}, notes={payload.notes or ''}".strip(),
        incident_id=incident_id,
        payload={"approved": payload.approved, "notes": payload.notes, "previous_status": previous_status},
        actor_type="human",
        actor_id=payload.operator_id,
    )
    return incident


class DispatchRequest(BaseModel):
    station_ids: List[str]


@router.post("/incidents/{incident_id}/dispatch")
async def dispatch_incident(incident_id: str, payload: DispatchRequest):
    """Backward-compatible simulation endpoint; never dispatches resources."""
    incident = await incident_repo.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    assignments = await assignment_repo.list({"incident_id": incident_id}, sort_field="created_at")
    if not assignments or assignments[0].decision != "approved":
        raise HTTPException(status_code=409, detail="Human approval is required before simulated dispatch")

    await monitoring_agent.log(
        "simulated_dispatch",
        f"Simulated dispatch to station(s) {payload.station_ids}; no real station or 911 call was made.",
        incident_id=incident_id,
        payload={"station_ids": payload.station_ids, "assignment_id": assignments[0].assignment_id},
    )
    return {
        "status": "simulated",
        "incident_id": incident_id,
        "message": "No real station notification, dispatch, or 911 call was made.",
    }


@router.post("/incidents/{incident_id}/resolve", response_model=Incident)
async def resolve_incident(incident_id: str):
    incident = await incident_repo.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    previous_status = incident.status.value
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

    await monitoring_agent.log(
        "resolved",
        f"Incident {incident_id} resolved.",
        incident_id=incident_id,
        payload={"previous_status": previous_status, "new_status": IncidentStatus.resolved.value},
    )
    await monitoring_agent.save_report(incident_id)
    return incident


@router.get("/incidents/{incident_id}/report")
async def get_incident_report(incident_id: str):
    incident = await incident_repo.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return await monitoring_agent.compile_report(incident_id)
