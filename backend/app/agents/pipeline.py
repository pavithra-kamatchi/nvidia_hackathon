from datetime import datetime

from app.agents.coordinator import coordinator_agent
from app.agents.monitoring import monitoring_agent
from app.agents.notification import notification_agent
from app.agents.perception import perception_agent
from app.agents.triage import triage_agent
from app.repositories.images import store_image
from app.schemas.common import Coordinate, IncidentStatus
from app.schemas.ingest import IngestResponse


async def run_pipeline(image_bytes: bytes, content_type: str, coordinate: Coordinate, timestamp: datetime) -> IngestResponse:
    """The hackathon simplification of Section 8's queue-based pipeline: one
    image upload runs straight through Agent 1 -> 2 -> 3 -> 4 -> 5,
    synchronously, in that order."""
    image_record = await store_image(image_bytes, content_type, coordinate, timestamp)
    await monitoring_agent.log("image_received", f"Image {image_record.image_id} received.", payload={"image_id": image_record.image_id})

    poses = await perception_agent.run(image_bytes, image_record.image_url, coordinate, timestamp)
    await monitoring_agent.log(
        "perception_complete",
        f"Perception Agent found {len(poses)} pose(s).",
        payload={"pose_ids": [p.pose_id for p in poses]},
    )

    detection, assessment, incident = await triage_agent.run(image_bytes, image_record.image_url, coordinate, timestamp, poses)
    await monitoring_agent.log(
        "triage_complete",
        f"Triage Agent assessed incident {incident.incident_id} as urgency={assessment.urgency.value}.",
        incident_id=incident.incident_id,
        payload={"detection_id": detection.detection_id, "assessment_id": assessment.assessment_id},
    )

    if incident.status == IncidentStatus.needs_review:
        await monitoring_agent.log(
            "incident_needs_review",
            f"Incident {incident.incident_id} urgency is uncertain; holding for operator review "
            "before it reaches the dispatch queue.",
            incident_id=incident.incident_id,
        )
        return IngestResponse(detection=detection, assessment=assessment, incident=incident, assignment=None)

    assignment = await coordinator_agent.run(incident)
    await monitoring_agent.log(
        "assignment_created",
        f"Coordinator proposed stations {assignment.assigned_station_ids} for incident {incident.incident_id}.",
        incident_id=incident.incident_id,
        payload={"assignment_id": assignment.assignment_id},
    )

    incident = await notification_agent.run(incident, assignment)

    return IngestResponse(detection=detection, assessment=assessment, incident=incident, assignment=assignment)
