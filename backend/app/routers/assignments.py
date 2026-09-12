from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.coordinator import coordinator_agent
from app.agents.monitoring import monitoring_agent
from app.repositories.collections import assignment_repo, incident_repo
from app.schemas.assignment import Assignment

router = APIRouter(tags=["assignments"])


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
    notes: str | None = None


@router.post("/allocations/{assignment_id}/decision", response_model=Assignment)
async def decide_allocation(assignment_id: str, payload: DecisionRequest):
    assignment = await assignment_repo.get(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Allocation proposal not found")

    assignment.decision = "approved" if payload.approved else "rejected"
    assignment.status = assignment.decision
    assignment.decided_by = payload.operator_id
    assignment.decided_at = datetime.now(timezone.utc)
    await assignment_repo.replace(assignment)
    await monitoring_agent.log(
        "allocation_decision",
        f"Allocation {assignment_id} was {assignment.decision} by {payload.operator_id}.",
        incident_id=assignment.incident_id,
        payload={"approved": payload.approved, "notes": payload.notes},
        actor_type="human",
        actor_id=payload.operator_id,
    )
    return assignment


@router.post("/allocations/{assignment_id}/notify")
async def simulate_notification(assignment_id: str):
    assignment = await assignment_repo.get(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Allocation proposal not found")
    if assignment.decision != "approved":
        raise HTTPException(status_code=409, detail="Human approval is required before notification")

    await monitoring_agent.log(
        "simulated_notification",
        f"Simulated station/911 notification for allocation {assignment_id}; no real call or message was made.",
        incident_id=assignment.incident_id,
        payload={
            "station_ids": assignment.assigned_station_ids,
            "simulate_911": assignment.escalate_to_911,
        },
        actor_type="system",
        actor_id="notification-simulator",
    )
    return {
        "status": "simulated",
        "assignment_id": assignment_id,
        "message": "No real station notification or 911 call was made.",
    }


@router.post("/assignments/{assignment_id}/respond", response_model=Assignment)
async def respond_to_assignment(assignment_id: str, payload: RespondRequest):
    """Agent 4's feasibility check made concrete: a station rejecting closes
    the loop back to Agent 3, which re-plans against every other station."""
    assignment = await assignment_repo.get(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if payload.accept:
        if payload.station_id not in assignment.accepted_station_ids:
            assignment.accepted_station_ids.append(payload.station_id)
        if payload.station_id in assignment.rejected_station_ids:
            assignment.rejected_station_ids.remove(payload.station_id)
        await assignment_repo.replace(assignment)
        await monitoring_agent.log(
            "assignment_accepted",
            f"Station {payload.station_id} accepted assignment {assignment_id}.",
            incident_id=assignment.incident_id,
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
