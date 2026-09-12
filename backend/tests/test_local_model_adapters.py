import io
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.config import settings
from app.ml.detector import RawPoseDetection
from app.ml.reasoning import LocalNemotronReasoner
from app.ml.vlm import LocalNemotronVisionDescriber
from app.schemas.common import Coordinate, PoseLabel, Urgency
from app.schemas.triage import Detection


def _response(content: str) -> io.BytesIO:
    return io.BytesIO(
        json.dumps({"choices": [{"message": {"content": content}}]}).encode()
    )


class LocalModelAdapterTests(unittest.TestCase):
    def setUp(self):
        self.original_url = settings.nemotron_url
        settings.nemotron_url = "http://127.0.0.1:8000/v1/chat/completions"
        self.poses = [RawPoseDetection(PoseLabel.upright, 0.91)]

    def tearDown(self):
        settings.nemotron_url = self.original_url

    def test_vlm_sends_image_and_parses_structured_result(self):
        content = json.dumps(
            {
                "human": True,
                "number_of_people": 1,
                "visible_blood": False,
                "visible_hazards": "debris",
                "observations": "One person is standing near debris.",
                "confidence": 0.88,
            }
        )
        with patch("urllib.request.urlopen", return_value=_response(content)) as call:
            result = LocalNemotronVisionDescriber().describe(b"\xff\xd8image", self.poses)
        request_body = json.loads(call.call_args.args[0].data)
        image_url = request_body["messages"][0]["content"][1]["image_url"]["url"]
        self.assertTrue(image_url.startswith("data:image/jpeg;base64,"))
        self.assertEqual(result.number_of_people, 1)
        self.assertEqual(result.visible_hazards, "debris")

    def test_vlm_failure_never_invents_hazards_or_blood(self):
        with patch("urllib.request.urlopen", side_effect=OSError("model stopped")):
            result = LocalNemotronVisionDescriber().describe(b"image", self.poses)
        self.assertEqual(result.visible_hazards, "unclear")
        self.assertFalse(result.blood)
        self.assertLess(result.confidence, settings.confidence_threshold)

    def test_vlm_rejects_remote_model_endpoint(self):
        settings.nemotron_url = "https://remote.example/v1/chat/completions"
        with self.assertRaises(ValueError):
            LocalNemotronVisionDescriber().describe(b"image", self.poses)

    def test_reasoner_forces_review_for_high_urgency(self):
        content = json.dumps(
            {
                "urgency": "high",
                "incident_type": "fire",
                "reasoning": "Smoke is visible near a person.",
                "confidence": 0.92,
                "needs_human_verification": False,
            }
        )
        detection = Detection(
            detection_id="det-test",
            timestamp=datetime.now(timezone.utc),
            location=Coordinate(latitude=40.0, longitude=-74.0),
            human=True,
            blood=False,
            number_of_people=1,
            visible_hazards="smoke",
            observations="One person and smoke are visible.",
            confidence=0.9,
        )
        with patch("urllib.request.urlopen", return_value=_response(content)):
            result = LocalNemotronReasoner().assess(detection, self.poses)
        self.assertEqual(result.urgency, Urgency.high)
        self.assertTrue(result.needs_human_verification)

    def test_reasoner_corrects_low_urgency_when_hazard_is_visible(self):
        content = json.dumps(
            {
                "urgency": "low",
                "incident_type": "person_detected",
                "reasoning": "A person is visible.",
                "confidence": 0.91,
                "needs_human_verification": False,
            }
        )
        detection = Detection(
            detection_id="det-hazard-conflict",
            timestamp=datetime.now(timezone.utc),
            location=Coordinate(latitude=40.0, longitude=-74.0),
            human=True,
            blood=False,
            number_of_people=1,
            visible_hazards="smoke and fire",
            observations="One person is visible near smoke and fire.",
            confidence=0.9,
        )
        with patch("urllib.request.urlopen", return_value=_response(content)):
            result = LocalNemotronReasoner().assess(detection, self.poses)
        self.assertEqual(result.urgency, Urgency.medium)
        self.assertEqual(result.incident_type, "person_near_hazard")
        self.assertTrue(result.needs_human_verification)

    def test_reasoner_uses_deterministic_fallback(self):
        detection = Detection(
            detection_id="det-fallback",
            timestamp=datetime.now(timezone.utc),
            location=Coordinate(latitude=40.0, longitude=-74.0),
            human=True,
            blood=False,
            number_of_people=1,
            visible_hazards="none visible",
            observations="One person is visible.",
            confidence=0.9,
        )
        with patch("urllib.request.urlopen", side_effect=OSError("model stopped")):
            result = LocalNemotronReasoner().assess(detection, self.poses)
        self.assertEqual(result.urgency, Urgency.low)
        self.assertEqual(result.incident_type, "person_detected")


if __name__ == "__main__":
    unittest.main()
