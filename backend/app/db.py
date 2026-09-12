from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket

from app.config import settings

_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


def get_database() -> AsyncIOMotorDatabase:
    if _database is None:
        raise RuntimeError("MongoDB has not been initialized")
    return _database


def get_gridfs_bucket() -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(get_database(), bucket_name="images")


async def ensure_indexes() -> None:
    global _client, _database
    # Uvicorn imports modules before starting its event loop. Create Motor here
    # so it binds to the same loop that serves requests.
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _database = _client[settings.mongodb_db_name]
    database = get_database()

    await database["incidents"].create_index("incident_id", unique=True)
    await database["incidents"].create_index("first_uploaded")
    await database["incidents"].create_index([("status", 1)])
    await database["detections"].create_index("detection_id", unique=True)
    await database["detections"].create_index("timestamp")
    await database["assessments"].create_index("assessment_id", unique=True)
    await database["assessments"].create_index("incident_id")
    await database["poses"].create_index("pose_id", unique=True)
    await database["stations"].create_index("station_id", unique=True)
    await database["assignments"].create_index("assignment_id", unique=True)
    await database["assignments"].create_index("incident_id")
    await database["logs"].create_index("log_id", unique=True)
    await database["logs"].create_index("incident_id")
    await database["logs"].create_index("timestamp")
    await database["images"].create_index("image_id", unique=True)


def close_database() -> None:
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None
