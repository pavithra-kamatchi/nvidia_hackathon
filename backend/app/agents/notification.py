from app.agents.monitoring import monitoring_agent
from app.repositories.collections import incident_repo
from app.schemas.assignment import Assignment
from app.schemas.common import IncidentStatus
from app.schemas.incident import Incident


class NotificationAgent:
    """Agent 4. Posts a proposal to the dashboard without contacting anyone.

    Puts the incident into the dispatch queue (awaiting_approval): stations
    see it there and accept/reject via /assignments/{id}/respond, stating
    whether they will dispatch their people. External station and 911 calls
    are simulations handled by the explicit notification route.
    """

    async def run(self, incident: Incident, assignment: Assignment) -> Incident:
        await monitoring_agent.log(
            event_type="dashboard_alert",
            summary=f"Incident {incident.incident_id} ({incident.urgency.value}/{incident.incident_type}) posted to dashboard.",
            incident_id=incident.incident_id,
            payload={"assignment_id": assignment.assignment_id, "assigned_station_ids": assignment.assigned_station_ids},
        )

        incident.status = IncidentStatus.awaiting_approval
        await incident_repo.replace(incident)
        await monitoring_agent.log(
            event_type="allocation_awaiting_station_response",
            summary=f"Allocation {assignment.assignment_id} is in the dispatch queue awaiting station acceptance.",
            incident_id=incident.incident_id,
            payload={"assignment_id": assignment.assignment_id},
            actor_type="agent",
            actor_id="administrative-agent",
        )

        return incident


notification_agent = NotificationAgent()
