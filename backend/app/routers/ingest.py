from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, UploadFile

from app.agents.pipeline import run_pipeline
from app.schemas.common import Coordinate
from app.schemas.ingest import IngestResponse

router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_image(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
):
    """Entry point: drone/UI image upload. Runs the full synchronous
    Perception -> Triage -> Coordinator -> Notification -> Monitoring chain
    and returns the resulting IngestResponse."""
    image_bytes = await file.read()
    coordinate = Coordinate(latitude=latitude, longitude=longitude)
    timestamp = datetime.now(timezone.utc)
    return await run_pipeline(image_bytes, file.content_type or "application/octet-stream", coordinate, timestamp)
