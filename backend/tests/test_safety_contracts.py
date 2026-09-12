import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from pydantic import ValidationError

from app.agents.coordinator import CoordinatorAgent
from app.ml.local_explainer import explain_allocation
from app.schemas.assignment import Assignment
from app.schemas.common import Coordinate
from app.schemas.handoff import AgentHandoffRequest
from app.schemas.station import Station


class SafetyContractTests(unittest.IsolatedAsyncioTestCase):
    def test_assignment_always_defaults_to_human_approval(self):
        assignment = Assignment(
            assignment_id="asg-1",
            incident_id="inc-1",
            assigned_station_ids=[],
            recommended_resources={},
            priority=1,
            rationale="No available station.",
            escalate_to_911=True,
            requires_multi_station=False,
            requires_additional_support=True,
            status="proposed",
            accepted_station_ids=[],
            rejected_station_ids=[],
            created_at=datetime.now(timezone.utc),
        )
        self.assertTrue(assignment.needs_human_approval)

    def test_offline_station_is_not_eligible(self):
        station = Station(
            station_id="stn-1",
            name="Offline Fire",
            station_type="fire",
            location=Coordinate(latitude=37, longitude=-122),
            responder_types=["fire"],
            available_responders={"fire": 4},
            available_vehicles=2,
            available_equipment=[],
            operational_status="offline",
            current_deployments=[],
        )
        self.assertFalse(CoordinatorAgent._can_help(station, ["fire"], ["fire"]))

    def test_handoff_rejects_mismatched_locations(self):
        with self.assertRaises(ValidationError):
            AgentHandoffRequest.model_validate({
                "perception": {
                    "detection_id": "det-1",
                    "timestamp": datetime.now(timezone.utc),
                    "location": {"latitude": 37, "longitude": -122},
                    "human_detected": True,
                    "number_of_people": 1,
                    "injury_status": "unclear",
                    "visible_hazards": [],
                    "observations": "One person visible.",
                    "confidence": 0.8,
                },
                "triage": {
                    "urgency": "unclear",
                    "incident_type": "unclear",
                    "location": {"latitude": 38, "longitude": -122},
                    "observations": "Insufficient evidence.",
                    "reasoning": "Locations disagree.",
                    "confidence": 0.8,
                    "needs_human_verification": True,
                },
            })

    def test_handoff_rejects_people_when_human_false(self):
        with self.assertRaises(ValidationError):
            AgentHandoffRequest.model_validate({
                "perception": {
                    "detection_id": "det-1",
                    "timestamp": datetime.now(timezone.utc),
                    "location": {"latitude": 37, "longitude": -122},
                    "human_detected": False,
                    "number_of_people": 1,
                    "injury_status": "unclear",
                    "visible_hazards": [],
                    "observations": "No human detected.",
                    "confidence": 0.8,
                },
                "triage": {
                    "urgency": "unclear",
                    "incident_type": "unclear",
                    "location": {"latitude": 37, "longitude": -122},
                    "observations": "Insufficient evidence.",
                    "reasoning": "No person detected.",
                    "confidence": 0.8,
                    "needs_human_verification": True,
                },
            })

    async def test_local_explainer_rejects_remote_endpoint(self):
        with patch("app.ml.local_explainer.settings.nemotron_url", "https://example.com/v1/chat/completions"):
            with self.assertRaises(ValueError):
                await explain_allocation("fallback", {})


if __name__ == "__main__":
    unittest.main()
