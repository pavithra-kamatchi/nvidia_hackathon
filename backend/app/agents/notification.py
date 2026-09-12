from app.agents.monitoring import monitoring_agent
from app.repositories.collections import incident_repo, station_repo
from app.schemas.assignment import Assignment
from app.schemas.common import IncidentStatus
from app.schemas.incident import Incident


class NotificationAgent:
    """Agent 4. Posts a proposal to the dashboard without contacting anyone.

    The alert is broadcast to every registered station so all of them are
    aware of the incident; the Coordinator's assigned_station_ids remain the
    recommended nearest-station(s)-with-capacity proposal, not the only
    stations that get notified. Puts the incident into the dispatch queue
    (awaiting_approval): stations see it there and accept/reject via
    /assignments/{id}/respond, stating whether they will dispatch their
    people. External station and 911 calls are simulations handled by the
    explicit notification route.
    """

    async def run(self, incident: Incident, assignment: Assignment) -> Incident:
        all_station_ids = [s.station_id for s in await station_repo.list()]
        await monitoring_agent.log(
            event_type="dashboard_alert",
            summary=(
                f"Incident {incident.incident_id} ({incident.urgency.value}/{incident.incident_type}) "
                f"broadcast to all {len(all_station_ids)} registered station(s); recommended: "
                f"{', '.join(assignment.assigned_station_ids) or 'none available'}."
            ),
            incident_id=incident.incident_id,
            payload={
                "assignment_id": assignment.assignment_id,
                "notified_station_ids": all_station_ids,
                "recommended_station_ids": assignment.assigned_station_ids,
            },
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
