from app.db import (
    assessments_collection,
    assignments_collection,
    detections_collection,
    incidents_collection,
    logs_collection,
    poses_collection,
    stations_collection,
)
from app.repositories.base import MongoRepository
from app.schemas.assignment import Assignment
from app.schemas.incident import Incident
from app.schemas.log import LogEntry
from app.schemas.perception import Pose
from app.schemas.station import Station
from app.schemas.triage import Assessment, Detection

pose_repo = MongoRepository(poses_collection, Pose, "pose_id")
detection_repo = MongoRepository(detections_collection, Detection, "detection_id")
assessment_repo = MongoRepository(assessments_collection, Assessment, "assessment_id")
incident_repo = MongoRepository(incidents_collection, Incident, "incident_id")
station_repo = MongoRepository(stations_collection, Station, "station_id")
assignment_repo = MongoRepository(assignments_collection, Assignment, "assignment_id")
log_repo = MongoRepository(logs_collection, LogEntry, "log_id")
