from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket

from app.config import settings

_client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongodb_uri)
database = _client[settings.mongodb_db_name]
gridfs_bucket = AsyncIOMotorGridFSBucket(database, bucket_name="images")

# Every Pydantic model in the system gets its own collection, keyed by its own
# `<x>_id` field (not Mongo's `_id`), so documents round-trip cleanly to/from
# the Pydantic schemas without translation. IDs are timestamp-prefixed (see
# app/utils/ids.py) so a record's origin-in-time is visible from its id alone.
poses_collection = database["poses"]
images_collection = database["images"]
detections_collection = database["detections"]
assessments_collection = database["assessments"]
incidents_collection = database["incidents"]
stations_collection = database["stations"]
assignments_collection = database["assignments"]
logs_collection = database["logs"]
reports_collection = database["reports"]


async def ensure_indexes() -> None:
    await incidents_collection.create_index("incident_id", unique=True)
    await incidents_collection.create_index("first_uploaded")
    await incidents_collection.create_index([("status", 1)])
    await detections_collection.create_index("detection_id", unique=True)
    await detections_collection.create_index("timestamp")
    await assessments_collection.create_index("assessment_id", unique=True)
    await assessments_collection.create_index("incident_id")
    await poses_collection.create_index("pose_id", unique=True)
    await stations_collection.create_index("station_id", unique=True)
    await assignments_collection.create_index("assignment_id", unique=True)
    await assignments_collection.create_index("incident_id")
    await logs_collection.create_index("log_id", unique=True)
    await logs_collection.create_index("incident_id")
    await logs_collection.create_index("timestamp")
    await images_collection.create_index("image_id", unique=True)
