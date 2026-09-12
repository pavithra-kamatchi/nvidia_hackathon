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


class RespondRequest(BaseModel):
    station_id: str
    accept: bool


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
