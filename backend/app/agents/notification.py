from app.agents.monitoring import monitoring_agent
from app.repositories.collections import incident_repo
from app.schemas.assignment import Assignment
from app.schemas.common import IncidentStatus
from app.schemas.incident import Incident


class NotificationAgent:
    """Agent 4. Posts a proposal to the dashboard without contacting anyone.

    Every proposed allocation requires a human decision. External station and
    911 actions are simulations handled by the explicit notification route.
    """

    async def run(self, incident: Incident, assignment: Assignment) -> Incident:
        await monitoring_agent.log(
            event_type="dashboard_alert",
            summary=f"Incident {incident.incident_id} ({incident.urgency.value}/{incident.incident_type}) posted to dashboard.",
            incident_id=incident.incident_id,
            payload={"assignment_id": assignment.assignment_id, "assigned_station_ids": assignment.assigned_station_ids},
        )

        incident.status = IncidentStatus.awaiting_approval
        incident.needs_human_verification = True
        await incident_repo.replace(incident)
        await monitoring_agent.log(
            event_type="allocation_awaiting_human_approval",
            summary=f"Allocation {assignment.assignment_id} is awaiting human approval; no notification was sent.",
            incident_id=incident.incident_id,
            payload={"assignment_id": assignment.assignment_id},
            actor_type="agent",
            actor_id="administrative-agent",
        )

        return incident


notification_agent = NotificationAgent()
