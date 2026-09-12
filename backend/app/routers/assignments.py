from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.coordinator import coordinator_agent
from app.agents.monitoring import monitoring_agent
from app.repositories.collections import assignment_repo, incident_repo, station_repo
from app.schemas.assignment import Assignment
from app.schemas.common import IncidentStatus

router = APIRouter(tags=["assignments"])


async def _dispatch_stations(assignment: Assignment, station_ids: List[str]) -> None:
    """Deducts each newly-dispatching station's share of
    assignment.recommended_resources (split across multiple stations when
    more than one dispatches, since that dict is the *combined* total the
    incident needs, not a per-station amount), marks the station deployed to
    the incident, and records exactly what was taken in
    assignment.resource_commitments so resolve_incident can credit it back.

    Safe to call more than once for the same assignment (e.g. once from
    approval covering every recommended station, and again from a later
    per-station response): a station already present in
    resource_commitments is left untouched, so nothing is ever double-
    deducted, and remaining need is computed fresh from whatever hasn't been
    committed yet.
    """
    remaining = dict(assignment.recommended_resources)
    for station_id in assignment.assigned_station_ids:
        for responder_type, amount in assignment.resource_commitments.get(station_id, {}).items():
            remaining[responder_type] = remaining.get(responder_type, 0) - amount

    for station_id in station_ids:
        if station_id in assignment.resource_commitments:
            continue
        station = await station_repo.get(station_id)
        if station is None:
            continue

        sent = {}
        for responder_type in list(remaining.keys()):
            if responder_type not in station.responder_types:
                continue
            need = remaining.get(responder_type, 0)
            if need <= 0:
                continue
            take = min(station.available_responders.get(responder_type, 0), need)
            if take <= 0:
                continue
            sent[responder_type] = take
            station.available_responders[responder_type] -= take
            remaining[responder_type] -= take

        if assignment.incident_id not in station.current_deployments:
            station.current_deployments.append(assignment.incident_id)
        await station_repo.replace(station)
        assignment.resource_commitments[station_id] = sent


@router.get("/assignments/{assignment_id}", response_model=Assignment)
async def get_assignment(assignment_id: str):
    assignment = await assignment_repo.get(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.post("/incidents/{incident_id}/allocation", response_model=Assignment)
async def propose_allocation(incident_id: str):
    incident = await incident_repo.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    assignment = await coordinator_agent.run(incident)
    await monitoring_agent.log(
        "allocation_proposed",
        f"Allocation {assignment.assignment_id} proposed; human approval required.",
        incident_id=incident_id,
        payload={"assignment_id": assignment.assignment_id},
        actor_type="agent",
        actor_id="resource-allocation-agent",
    )
    return assignment


class RespondRequest(BaseModel):
    station_id: str
    accept: bool


class DecisionRequest(BaseModel):
    approved: bool
    operator_id: str
    notes: Optional[str] = None


@router.post("/allocations/{assignment_id}/decision", response_model=Assignment)
async def decide_allocation(assignment_id: str, payload: DecisionRequest):
    assignment = await assignment_repo.get(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Allocation proposal not found")

    assignment.decision = "approved" if payload.approved else "rejected"
    assignment.status = assignment.decision
    assignment.decided_by = payload.operator_id
    assignment.decided_at = datetime.now(timezone.utc)

    incident = await incident_repo.get(assignment.incident_id) if payload.approved else None

    if payload.approved:
        # Approving the allocation is the operator committing every
        # recommended station's responders/vehicles to this incident right
        # now, not just recording a decision — so their rosters need to
        # reflect that immediately, for every other incident's planning.
        await _dispatch_stations(assignment, assignment.assigned_station_ids)

        if incident is not None and incident.status in (IncidentStatus.awaiting_approval, IncidentStatus.notified):
            incident.status = IncidentStatus.dispatched
            incident.last_updated = datetime.now(timezone.utc)
            await incident_repo.replace(incident)

    await assignment_repo.replace(assignment)
    await monitoring_agent.log(
        "allocation_decision",
        f"Allocation {assignment_id} was {assignment.decision} by {payload.operator_id}.",
        incident_id=assignment.incident_id,
        payload={
            "approved": payload.approved,
            "notes": payload.notes,
            "resource_commitments": assignment.resource_commitments if payload.approved else {},
        },
        actor_type="human",
        actor_id=payload.operator_id,
    )

    if payload.approved and assignment.requires_additional_support:
        other_station_ids = [
            s.station_id for s in await station_repo.list() if s.station_id not in assignment.assigned_station_ids
        ]
        if other_station_ids:
            await monitoring_agent.log(
                "additional_help_requested",
                f"Allocation {assignment_id} for incident {assignment.incident_id} did not have enough station "
                f"capacity at planning time; alerting station(s) {', '.join(other_station_ids)} for help.",
                incident_id=assignment.incident_id,
                payload={"assignment_id": assignment_id, "alerted_station_ids": other_station_ids},
                actor_type="agent",
                actor_id="administrative-agent",
            )

    return assignment


@router.post("/allocations/{assignment_id}/notify")
async def simulate_notification(assignment_id: str):
    assignment = await assignment_repo.get(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Allocation proposal not found")
    if assignment.decision != "approved":
        raise HTTPException(status_code=409, detail="Human approval is required before notification")
    if assignment.status == "notified":
        raise HTTPException(status_code=409, detail="Notification was already simulated")

    incident = await incident_repo.get(assignment.incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.status not in (IncidentStatus.awaiting_approval, IncidentStatus.dispatched):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot notify stations when incident status is {incident.status.value}",
        )

    all_station_ids = [s.station_id for s in await station_repo.list()]
    await monitoring_agent.log(
        "simulated_notification",
        f"Simulated notification broadcast to all {len(all_station_ids)} registered station(s) for allocation "
        f"{assignment_id} (recommended: {', '.join(assignment.assigned_station_ids) or 'none available'}).",
        incident_id=assignment.incident_id,
        payload={
            "notified_station_ids": all_station_ids,
            "recommended_station_ids": assignment.assigned_station_ids,
            "simulate_911": assignment.escalate_to_911,
        },
        actor_type="system",
        actor_id="notification-simulator",
    )
    # Approval already advances a covered incident straight to `dispatched`
    # (stations' resources are committed at that point); don't regress that
    # back to `notified` here — this step is just the simulated broadcast.
    if incident.status == IncidentStatus.awaiting_approval:
        incident.status = IncidentStatus.notified
        incident.last_updated = datetime.now(timezone.utc)
        await incident_repo.replace(incident)
    assignment.status = "notified"
    await assignment_repo.replace(assignment)
    return {
        "status": "simulated",
        "assignment_id": assignment_id,
        "incident": incident,
        "message": "Station notification simulated.",
    }


@router.post("/assignments/{assignment_id}/respond", response_model=Assignment)
async def respond_to_assignment(assignment_id: str, payload: RespondRequest):
    """A station accepting or rejecting its proposed dispatch from the
    incident queue. Accepting means the station commits to dispatching its
    people and moves the incident out of awaiting_approval into dispatched.
    Rejecting closes the loop back to Agent 3, which re-plans against every
    other station."""
    assignment = await assignment_repo.get(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if payload.accept:
        if payload.station_id not in assignment.accepted_station_ids:
            assignment.accepted_station_ids.append(payload.station_id)
        if payload.station_id in assignment.rejected_station_ids:
            assignment.rejected_station_ids.remove(payload.station_id)

        await _dispatch_stations(assignment, [payload.station_id])
        await assignment_repo.replace(assignment)

        incident = await incident_repo.get(assignment.incident_id)
        if incident is not None and incident.status == IncidentStatus.awaiting_approval:
            incident.status = IncidentStatus.dispatched
            incident.last_updated = datetime.now(timezone.utc)
            await incident_repo.replace(incident)

        await monitoring_agent.log(
            "assignment_accepted",
            f"Station {payload.station_id} accepted assignment {assignment_id}; dispatching responders.",
            incident_id=assignment.incident_id,
            payload={"assignment_id": assignment_id, "committed_resources": assignment.resource_commitments.get(payload.station_id, {})},
        )

        # Multi-station incidents that still have an un-accepted recommended
        # station, or incidents Agent 3 already flagged as under-covered,
        # still need more hands — alert every other registered station.
        still_needs_help = assignment.requires_additional_support or (
            assignment.requires_multi_station
            and any(sid not in assignment.accepted_station_ids for sid in assignment.assigned_station_ids)
        )
        if still_needs_help:
            other_station_ids = [
                s.station_id for s in await station_repo.list() if s.station_id not in assignment.accepted_station_ids
            ]
            if other_station_ids:
                await monitoring_agent.log(
                    "additional_help_requested",
                    f"Incident {assignment.incident_id} still needs additional support after station "
                    f"{payload.station_id} dispatched; alerting station(s) {', '.join(other_station_ids)}.",
                    incident_id=assignment.incident_id,
                    payload={"assignment_id": assignment_id, "alerted_station_ids": other_station_ids},
                    actor_type="agent",
                    actor_id="administrative-agent",
                )

        return assignment

    if payload.station_id not in assignment.rejected_station_ids:
        assignment.rejected_station_ids.append(payload.station_id)
    await assignment_repo.replace(assignment)
    await monitoring_agent.log(
        "assignment_rejected",
        f"Station {payload.station_id} rejected assignment {assignment_id}; re-triggering Coordinator.",
        incident_id=assignment.incident_id,
    )

    if not assignment.accepted_station_ids:
        incident = await incident_repo.get(assignment.incident_id)
        if incident is not None:
            new_assignment = await coordinator_agent.run(incident)
            await monitoring_agent.log(
                "assignment_replanned",
                f"Coordinator re-planned incident {incident.incident_id} -> stations {new_assignment.assigned_station_ids}.",
                incident_id=incident.incident_id,
                payload={"assignment_id": new_assignment.assignment_id},
            )
            return new_assignment

    return assignment
