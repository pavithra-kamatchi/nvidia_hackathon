from datetime import datetime, timezone
from typing import Dict, List

from app.config import settings
from app.repositories.collections import assignment_repo, station_repo
from app.schemas.assignment import Assignment
from app.schemas.common import Urgency
from app.schemas.incident import Incident
from app.schemas.station import Station
from app.utils.geo import haversine_distance_meters
from app.utils.ids import generate_id

# incident_type -> responder types capable of handling it. Falls back to
# ["EMS"] for any incident_type not listed here.
_REQUIRED_RESPONDER_TYPES: Dict[str, List[str]] = {
    "injury": ["EMS", "paramedic"],
    "fire": ["fire"],
    "vehicle_incident": ["EMS", "fire"],
    "person_near_hazard": ["EMS"],
    "hazard_no_person": ["hazmat", "fire"],
}

_INACTIVE_STATION_STATUSES = {"offline", "unavailable"}


class CoordinatorAgent:
    """Agent 3. Global re-planner: looks at all active incidents and all
    station states together, not just the one incident that triggered it."""

    async def run(self, incident: Incident) -> Assignment:
        stations = await station_repo.list()
        required_types = _REQUIRED_RESPONDER_TYPES.get(incident.incident_type, ["EMS"])

        capable = [s for s in stations if self._can_help(s, required_types)]
        capable.sort(key=lambda s: haversine_distance_meters(s.location, incident.location))

        requires_multi_station = (
            incident.number_of_people >= settings.multi_station_people_threshold
            or incident.incident_type == "fire"
        )
        take = 2 if requires_multi_station else 1
        chosen = capable[:take]

        escalate_to_911 = incident.urgency == Urgency.high

        if chosen:
            rationale = (
                f"Selected {', '.join(s.name for s in chosen)} based on nearest available "
                f"station(s) with responder types {required_types} for incident_type="
                f"'{incident.incident_type}' (urgency={incident.urgency.value})."
            )
        else:
            rationale = (
                f"No station currently has available capacity for responder types {required_types}; "
                "flagging for manual dispatch / 911."
            )
            escalate_to_911 = escalate_to_911 or incident.urgency in (Urgency.high, Urgency.medium)

        now = datetime.now(timezone.utc)
        assignment = Assignment(
            assignment_id=generate_id("asg", now),
            incident_id=incident.incident_id,
            assigned_station_ids=[s.station_id for s in chosen],
            rationale=rationale,
            escalate_to_911=escalate_to_911,
            requires_multi_station=requires_multi_station,
            status="proposed",
            accepted_station_ids=[],
            rejected_station_ids=[],
            created_at=now,
        )
        await assignment_repo.insert(assignment)
        return assignment

    @staticmethod
    def _can_help(station: Station, required_types: List[str]) -> bool:
        if station.operational_status in _INACTIVE_STATION_STATUSES:
            return False
        if not any(t in station.responder_types for t in required_types):
            return False
        committed = len(station.current_deployments)
        if committed >= station.available_vehicles:
            return False
        return any(station.available_responders.get(t, 0) > 0 for t in required_types)


coordinator_agent = CoordinatorAgent()
