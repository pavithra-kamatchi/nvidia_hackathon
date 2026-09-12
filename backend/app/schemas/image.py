from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import Coordinate


class ImageRecord(BaseModel):
    """Metadata for a raw uploaded frame. The bytes themselves live in
    GridFS (see app/repositories/images.py); this record is what `images`
    in the shared IncidentState maps to."""

    image_id: str
    timestamp: datetime
    coordinate: Coordinate
    content_type: str
    gridfs_file_id: str
    image_url: str
