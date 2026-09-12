from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from app.config import settings
from app.ml.detector import RawPoseDetection
from app.ml.reasoning import reasoner
from app.ml.vlm import vision_describer
from app.repositories.collections import assessment_repo, detection_repo, incident_repo, pose_repo
from app.schemas.common import Coordinate, IncidentStatus
from app.schemas.incident import Incident
from app.schemas.perception import Pose
from app.schemas.triage import Assessment, Detection
from app.utils.geo import haversine_distance_meters
from app.utils.ids import generate_id

_CLOSED_STATUSES = {IncidentStatus.resolved, IncidentStatus.false_positive}


class TriageAgent:
    """Agent 2. Interprets *why* a detection matters: produces the Detection
    (vision step), the Assessment (reasoning step), and resolves/creates the
    persistent Incident record the detection belongs to."""

    async def run(
        self,
        image_bytes: bytes,
        image_url: Optional[str],
        coordinate: Coordinate,
        timestamp: datetime,
        poses: List[Pose],
    ) -> Tuple[Detection, Assessment, Incident]:
        raw_poses = [RawPoseDetection(pose=p.pose, confidence=p.confidence) for p in poses]
        vision = vision_describer.describe(image_bytes, raw_poses)

        detection = Detection(
            detection_id=generate_id("det", timestamp),
            timestamp=timestamp,
            location=coordinate,
            human=vision.human,
            blood=vision.blood,
            number_of_people=vision.number_of_people,
            visible_hazards=vision.visible_hazards,
            observations=vision.observations,
            confidence=vision.confidence,
            image_url=image_url,
        )
        await detection_repo.insert(detection)

        preliminary = reasoner.assess(detection, raw_poses, prior_assessments=None)
        incident = await self._resolve_incident(coordinate, preliminary.incident_type, timestamp)

        prior_assessments = (
            await assessment_repo.list({"incident_id": incident.incident_id}, sort_field="timestamp")
            if incident is not None
            else None
        )
        reasoning = reasoner.assess(detection, raw_poses, prior_assessments=prior_assessments) if incident else preliminary

        if incident is None:
            incident = Incident(
                incident_id=generate_id("inc", timestamp),
                location=coordinate,
                incident_type=reasoning.incident_type,
                urgency=reasoning.urgency,
                status=IncidentStatus.new,
                number_of_people=detection.number_of_people,
                first_uploaded=timestamp,
                last_updated=timestamp,
                needs_human_verification=reasoning.needs_human_verification,
                image_url=image_url,
            )
        else:
            incident.urgency = reasoning.urgency
            incident.incident_type = reasoning.incident_type
            incident.number_of_people = detection.number_of_people
            incident.last_updated = timestamp
            incident.needs_human_verification = reasoning.needs_human_verification
            incident.image_url = image_url or incident.image_url

        reopenable_statuses = (IncidentStatus.new, IncidentStatus.notified, IncidentStatus.in_progress)
        if reasoning.needs_human_verification and incident.status in reopenable_statuses:
            incident.status = IncidentStatus.awaiting_approval

        await incident_repo.replace(incident)

        assessment = Assessment(
            assessment_id=generate_id("asmt", timestamp),
            incident_id=incident.incident_id,
            detection_id=detection.detection_id,
            timestamp=timestamp,
            urgency=reasoning.urgency,
            incident_type=reasoning.incident_type,
            observation_and_reasoning=reasoning.observation_and_reasoning,
            confidence=reasoning.confidence,
            needs_human_verification=reasoning.needs_human_verification,
        )
        await assessment_repo.insert(assessment)

        for pose in poses:
            pose.detection_id = detection.detection_id
            await pose_repo.replace(pose)

        return detection, assessment, incident

    async def _resolve_incident(self, coordinate: Coordinate, incident_type: str, timestamp: datetime) -> Optional[Incident]:
        """Dedup: fold into an existing open incident of the same type within
        both a spatial and temporal proximity window; otherwise, None (the
        caller creates a fresh Incident)."""
        candidates = await incident_repo.list({"incident_type": incident_type})
        window_start = timestamp - timedelta(minutes=settings.dedup_time_window_minutes)
        best: Optional[Incident] = None
        best_distance = None
        for candidate in candidates:
            if candidate.status in _CLOSED_STATUSES:
                continue
            if candidate.last_updated < window_start:
                continue
            distance = haversine_distance_meters(candidate.location, coordinate)
            if distance > settings.dedup_distance_meters:
                continue
            if best is None or distance < best_distance:
                best, best_distance = candidate, distance
        return best


triage_agent = TriageAgent()
