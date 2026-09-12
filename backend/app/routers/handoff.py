from datetime import datetime, timezone

from fastapi import APIRouter

from app.agents.coordinator import coordinator_agent
from app.agents.monitoring import monitoring_agent
from app.agents.notification import notification_agent
from app.config import settings
from app.repositories.collections import assessment_repo, detection_repo, incident_repo
from app.schemas.common import IncidentStatus, Urgency
from app.schemas.handoff import AgentHandoffRequest, AgentHandoffResponse
from app.schemas.incident import Incident
from app.schemas.triage import Assessment, Detection
from app.utils.ids import generate_id

router = APIRouter(tags=["agent-handoff"])


def _hazards_as_text(value: str | list[str]) -> str:
    if isinstance(value, str):
        return value.strip() or "none visible"
    return ", ".join(value) if value else "none visible"


@router.post("/agent-handoff", response_model=AgentHandoffResponse)
async def agent_handoff(payload: AgentHandoffRequest):
    """Persist validated Perception/Triage outputs and propose resources.

    This endpoint never dispatches resources or sends real notifications.
    """
    perception, triage = payload.perception, payload.triage
    warnings: list[str] = []
    hazards = _hazards_as_text(perception.visible_hazards)
    needs_human = (
        perception.confidence < settings.confidence_threshold
        or triage.confidence < settings.confidence_threshold
        or triage.needs_human_verification
    )
    conflict = (
        triage.urgency == Urgency.low
        and (perception.injury_status.lower() == "injured" or hazards.lower() != "none visible")
    )
    if conflict:
        needs_human = True
        warnings.append("Low urgency conflicts with visible injury/hazard evidence; human review required.")
    if perception.confidence < settings.confidence_threshold or triage.confidence < settings.confidence_threshold:
        warnings.append("Confidence below 0.70; human review required.")

    detection = Detection(
        detection_id=perception.detection_id,
        timestamp=perception.timestamp,
        location=perception.location,
        human=perception.human_detected,
        blood=False,
        number_of_people=perception.number_of_people,
        visible_hazards=hazards,
        observations=perception.observations,
        confidence=perception.confidence,
    )
    await detection_repo.insert(detection)

    now = datetime.now(timezone.utc)
    incident = Incident(
        incident_id=generate_id("inc", now),
        location=triage.location,
        incident_type=triage.incident_type,
        urgency=triage.urgency,
        status=IncidentStatus.awaiting_approval,
        number_of_people=perception.number_of_people,
        first_uploaded=perception.timestamp,
        last_updated=now,
        needs_human_verification=True,
    )
    await incident_repo.insert(incident)

    assessment = Assessment(
        assessment_id=generate_id("asmt", now),
        incident_id=incident.incident_id,
        detection_id=detection.detection_id,
        timestamp=now,
        urgency=triage.urgency,
        incident_type=triage.incident_type,
        observation_and_reasoning=f"{triage.observations} {triage.reasoning}".strip(),
        confidence=triage.confidence,
        needs_human_verification=needs_human,
    )
    await assessment_repo.insert(assessment)
    await monitoring_agent.log(
        "agent_handoff",
        f"Validated Perception/Triage handoff for incident {incident.incident_id}.",
        incident_id=incident.incident_id,
        payload={"detection_id": detection.detection_id, "warnings": warnings},
        actor_type="agent",
        actor_id="perception-triage-handoff",
    )

    assignment = await coordinator_agent.run(incident)
    incident = await notification_agent.run(incident, assignment)
    return AgentHandoffResponse(
        detection=detection,
        assessment=assessment,
        incident=incident,
        assignment=assignment,
        warnings=warnings,
    )
