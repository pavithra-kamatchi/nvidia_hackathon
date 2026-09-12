import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.routers.assignments import simulate_notification
from app.routers.incidents import ReviewRequest, review_incident
from app.schemas.assignment import Assignment
from app.schemas.common import Coordinate, IncidentStatus, Urgency
from app.schemas.incident import Incident


def _incident() -> Incident:
    now = datetime.now(timezone.utc)
    return Incident(
        incident_id="inc-test",
        location=Coordinate(latitude=42.44, longitude=-76.48),
        incident_type="fire",
        urgency=Urgency.high,
        status=IncidentStatus.awaiting_approval,
        number_of_people=1,
        first_uploaded=now,
        last_updated=now,
        needs_human_verification=True,
    )


class HumanApprovalFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_observation_review_does_not_notify(self):
        incident = _incident()
        with (
            patch("app.routers.incidents.incident_repo.get", AsyncMock(return_value=incident)),
            patch("app.routers.incidents.incident_repo.replace", AsyncMock()),
            patch("app.routers.incidents.monitoring_agent.log", AsyncMock()),
        ):
            result = await review_incident(
                incident.incident_id,
                ReviewRequest(approved=True, operator_id="operator-test"),
            )
        self.assertEqual(result.status, IncidentStatus.awaiting_approval)
        self.assertFalse(result.needs_human_verification)

    async def test_approved_allocation_notification_is_simulated_and_recorded(self):
        incident = _incident()
        now = datetime.now(timezone.utc)
        assignment = Assignment(
            assignment_id="asg-test",
            incident_id=incident.incident_id,
            assigned_station_ids=["station-test"],
            recommended_resources={"fire": 1},
            priority=1,
            rationale="Test allocation.",
            escalate_to_911=True,
            requires_multi_station=False,
            requires_additional_support=False,
            status="approved",
            accepted_station_ids=[],
            rejected_station_ids=[],
            created_at=now,
            decision="approved",
            decided_by="operator-test",
            decided_at=now,
        )
        with (
            patch("app.routers.assignments.assignment_repo.get", AsyncMock(return_value=assignment)),
            patch("app.routers.assignments.assignment_repo.replace", AsyncMock()) as replace_assignment,
            patch("app.routers.assignments.incident_repo.get", AsyncMock(return_value=incident)),
            patch("app.routers.assignments.incident_repo.replace", AsyncMock()) as replace_incident,
            patch("app.routers.assignments.monitoring_agent.log", AsyncMock()),
        ):
            result = await simulate_notification(assignment.assignment_id)
        self.assertEqual(result["status"], "simulated")
        self.assertEqual(incident.status, IncidentStatus.notified)
        self.assertEqual(assignment.status, "notified")
        replace_incident.assert_awaited_once()
        replace_assignment.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
