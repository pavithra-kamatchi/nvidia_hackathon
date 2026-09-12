from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.config import settings
from app.ml.local_explainer import explain_allocation
from app.repositories.collections import assignment_repo, incident_repo, station_repo
from app.schemas.assignment import Assignment
from app.schemas.common import IncidentStatus, Urgency
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

# Urgency types severe enough that we recommend looping in 911 even when a
# local station can respond, per the design doc's "incident_type in {fire,
# injury, ...}" example.
_ALWAYS_ESCALATE_INCIDENT_TYPES = {"injury", "fire", "vehicle_incident"}

_INACTIVE_STATION_STATUSES = {"offline", "unavailable"}
_CLOSED_INCIDENT_STATUSES = {IncidentStatus.resolved, IncidentStatus.false_positive}

_URGENCY_PRIORITY: Dict[Urgency, int] = {
    Urgency.high: 1,
    Urgency.medium: 2,
    Urgency.low: 3,
    Urgency.unclear: 2,
}


class CoordinatorAgent:
    """Agent 3. Global re-planner: every call re-ranks and re-allocates
    across *all* currently active incidents and *all* stations together, not
    just the one incident that triggered the run. Higher-urgency (then
    older) incidents claim capacity first, so a newly-arrived low-urgency
    incident can't preempt an already in-progress high one."""

    async def run(self, incident: Incident) -> Assignment:
        stations = await station_repo.list()
        active_incidents = await self._active_incidents()
        by_id = {i.incident_id: i for i in active_incidents}
        by_id[incident.incident_id] = incident  # use the caller's freshest copy

        ordered = sorted(by_id.values(), key=self._rank_key)
        station_by_id = {s.station_id: s for s in stations}

        reserved: Dict[str, int] = {}
        triggering_assignment: Optional[Assignment] = None

        for candidate in ordered:
            assignment = await self._plan_one(candidate, stations, reserved)

            for station_id in assignment.assigned_station_ids:
                station = station_by_id[station_id]
                # Already-persisted commitments stay reflected in that
                # station's own current_deployments for every other
                # incident's eligibility check; only a not-yet-persisted
                # proposal needs an in-pass reservation, otherwise we'd
                # double-count the same slot.
                if candidate.incident_id not in station.current_deployments:
                    reserved[station_id] = reserved.get(station_id, 0) + 1

            if candidate.incident_id == incident.incident_id:
                triggering_assignment = assignment
            elif await self._plan_changed(candidate.incident_id, assignment):
                await assignment_repo.insert(assignment)

        assert triggering_assignment is not None
        await assignment_repo.insert(triggering_assignment)
        return triggering_assignment

    async def _active_incidents(self) -> List[Incident]:
        incidents = await incident_repo.list({})
        return [i for i in incidents if i.status not in _CLOSED_INCIDENT_STATUSES]

    @staticmethod
    def _rank_key(incident: Incident):
        return (_URGENCY_PRIORITY[incident.urgency], incident.first_uploaded)

    @staticmethod
    async def _plan_changed(incident_id: str, assignment: Assignment) -> bool:
        previous = await assignment_repo.list({"incident_id": incident_id}, sort_field="created_at")
        if not previous:
            return True
        last = previous[0]
        return (
            sorted(last.assigned_station_ids) != sorted(assignment.assigned_station_ids)
            or last.escalate_to_911 != assignment.escalate_to_911
        )

    async def _plan_one(self, incident: Incident, stations: List[Station], reserved: Dict[str, int]) -> Assignment:
        required_types = _REQUIRED_RESPONDER_TYPES.get(incident.incident_type, ["EMS"])

        capable = [s for s in stations if self._can_help(s, required_types, incident.incident_id, reserved)]
        capable.sort(key=lambda s: haversine_distance_meters(s.location, incident.location))

        requires_multi_station = (
            incident.number_of_people >= settings.multi_station_people_threshold
            or incident.incident_type == "fire"
        )
        take = 2 if requires_multi_station else 1
        chosen = capable[:take]

        recommended_resources: Dict[str, int] = {}
        for responder_type in required_types:
            available = sum(s.available_responders.get(responder_type, 0) for s in chosen)
            if available:
                recommended_resources[responder_type] = min(available, max(1, incident.number_of_people))

        no_coverage = not chosen
        escalate_to_911 = incident.urgency == Urgency.high and (
            no_coverage or incident.incident_type in _ALWAYS_ESCALATE_INCIDENT_TYPES
        )

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

        rationale = await explain_allocation(
            rationale,
            {
                "incident_id": incident.incident_id,
                "incident_type": incident.incident_type,
                "urgency": incident.urgency.value,
                "number_of_people": incident.number_of_people,
                "selected_station_ids": [s.station_id for s in chosen],
                "recommended_resources": recommended_resources,
                "requires_additional_support": len(chosen) < take,
                "straight_line_distance_only": True,
            },
        )

        now = datetime.now(timezone.utc)
        assignment = Assignment(
            assignment_id=generate_id("asg", now),
            incident_id=incident.incident_id,
            assigned_station_ids=[s.station_id for s in chosen],
            recommended_resources=recommended_resources,
            priority=_URGENCY_PRIORITY[incident.urgency],
            rationale=rationale,
            escalate_to_911=escalate_to_911,
            requires_multi_station=requires_multi_station,
            requires_additional_support=len(chosen) < take,
            needs_human_approval=True,
            status="proposed",
            accepted_station_ids=[],
            rejected_station_ids=[],
            created_at=now,
        )
        return assignment

    @staticmethod
    def _can_help(station: Station, required_types: List[str], incident_id: str, reserved: Dict[str, int]) -> bool:
        if station.operational_status in _INACTIVE_STATION_STATUSES:
            return False
        if not any(t in station.responder_types for t in required_types):
            return False

        # Don't count this incident's own existing commitment to this
        # station against itself, so an already-settled incident's plan
        # stays stable when it's re-evaluated in a later replan pass.
        committed = len([d for d in station.current_deployments if d != incident_id])
        committed += reserved.get(station.station_id, 0)
        if committed >= station.available_vehicles:
            return False

        return sum(station.available_responders.get(t, 0) for t in required_types) > 0


coordinator_agent = CoordinatorAgent()
