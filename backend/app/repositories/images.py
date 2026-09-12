from datetime import datetime
from typing import Tuple

from bson import ObjectId

from app.db import gridfs_bucket, images_collection
from app.repositories.base import MongoRepository
from app.schemas.common import Coordinate
from app.schemas.image import ImageRecord
from app.utils.ids import generate_id

image_repo = MongoRepository(images_collection, ImageRecord, "image_id")


async def store_image(image_bytes: bytes, content_type: str, coordinate: Coordinate, timestamp: datetime) -> ImageRecord:
    gridfs_id = await gridfs_bucket.upload_from_stream(
        f"{timestamp.isoformat()}.bin", image_bytes, metadata={"content_type": content_type}
    )
    image_id = generate_id("img", timestamp)
    record = ImageRecord(
        image_id=image_id,
        timestamp=timestamp,
        coordinate=coordinate,
        content_type=content_type,
        gridfs_file_id=str(gridfs_id),
        image_url=f"/images/{image_id}",
    )
    await image_repo.insert(record)
    return record


async def load_image_bytes(gridfs_file_id: str) -> Tuple[bytes, str]:
    grid_out = await gridfs_bucket.open_download_stream(ObjectId(gridfs_file_id))
    data = await grid_out.read()
    content_type = (grid_out.metadata or {}).get("content_type", "application/octet-stream")
    return data, content_type
