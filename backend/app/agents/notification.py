from app.agents.monitoring import monitoring_agent
from app.repositories.collections import incident_repo
from app.schemas.assignment import Assignment
from app.schemas.common import IncidentStatus
from app.schemas.incident import Incident


class NotificationAgent:
    """Agent 4. Turns a plan into dashboard-facing facts. Per project rule:
    every incident is posted to the dashboard regardless of urgency; a
    needs_human_verification incident stays gated at awaiting_approval until
    a human reviews it (see routers/incidents.py `/review`)."""

    async def run(self, incident: Incident, assignment: Assignment) -> Incident:
        await monitoring_agent.log(
            event_type="dashboard_alert",
            summary=f"Incident {incident.incident_id} ({incident.urgency.value}/{incident.incident_type}) posted to dashboard.",
            incident_id=incident.incident_id,
            payload={"assignment_id": assignment.assignment_id, "assigned_station_ids": assignment.assigned_station_ids},
        )

        if assignment.escalate_to_911:
            await monitoring_agent.log(
                event_type="escalate_911",
                summary=f"Incident {incident.incident_id} flagged high urgency — 911 escalation triggered.",
                incident_id=incident.incident_id,
                payload={"assignment_id": assignment.assignment_id},
            )

        if incident.status != IncidentStatus.awaiting_approval:
            incident.status = IncidentStatus.notified
            await incident_repo.replace(incident)
            await monitoring_agent.log(
                event_type="stations_notified",
                summary=f"Station(s) {assignment.assigned_station_ids} notified for incident {incident.incident_id}.",
                incident_id=incident.incident_id,
                payload={"station_ids": assignment.assigned_station_ids},
            )

        return incident


notification_agent = NotificationAgent()
