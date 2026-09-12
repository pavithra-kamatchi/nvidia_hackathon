from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.repositories.images import image_repo, load_image_bytes

router = APIRouter(tags=["images"])


@router.get("/images/{image_id}")
async def get_image(image_id: str):
    record = await image_repo.get(image_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Image not found")
    data, content_type = await load_image_bytes(record.gridfs_file_id)
    return Response(content=data, media_type=content_type)
