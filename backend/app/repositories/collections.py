from app.repositories.base import MongoRepository
from app.schemas.assignment import Assignment
from app.schemas.incident import Incident
from app.schemas.log import LogEntry
from app.schemas.perception import Pose
from app.schemas.station import Station
from app.schemas.triage import Assessment, Detection

pose_repo = MongoRepository("poses", Pose, "pose_id")
detection_repo = MongoRepository("detections", Detection, "detection_id")
assessment_repo = MongoRepository("assessments", Assessment, "assessment_id")
incident_repo = MongoRepository("incidents", Incident, "incident_id")
station_repo = MongoRepository("stations", Station, "station_id")
assignment_repo = MongoRepository("assignments", Assignment, "assignment_id")
log_repo = MongoRepository("logs", LogEntry, "log_id")
