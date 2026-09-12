from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agents.pipeline import run_pipeline
from app.config import settings
from app.schemas.common import Coordinate
from app.schemas.ingest import IngestResponse

router = APIRouter(tags=["ingest"])
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/ingest", response_model=IngestResponse)
async def ingest_image(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
):
    """Entry point: drone/UI image upload. Runs the full synchronous
    Perception -> Triage -> Coordinator -> Notification -> Monitoring chain
    and returns the resulting IngestResponse."""
    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WebP images are supported")
    image_bytes = await file.read(settings.max_upload_bytes + 1)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    if len(image_bytes) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Uploaded image exceeds the configured size limit")
    coordinate = Coordinate(latitude=latitude, longitude=longitude)
    timestamp = datetime.now(timezone.utc)
    return await run_pipeline(image_bytes, content_type, coordinate, timestamp)
