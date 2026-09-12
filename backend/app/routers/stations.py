from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.repositories.collections import station_repo
from app.schemas.station import Station, StationCreate
from app.utils.ids import generate_id

router = APIRouter(tags=["stations"])


@router.post("/stations", response_model=Station)
async def register_station(payload: StationCreate):
    now = datetime.now(timezone.utc)
    station = Station(
        **payload.model_dump(),
        station_id=generate_id("stn", now),
        operational_status="available",
        current_deployments=[],
    )
    await station_repo.insert(station)
    return station


@router.get("/stations", response_model=List[Station])
async def list_stations():
    return await station_repo.list()


@router.get("/stations/{station_id}", response_model=Station)
async def get_station(station_id: str):
    station = await station_repo.get(station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


class StationUpdate(BaseModel):
    available_responders: Optional[dict] = None
    available_vehicles: Optional[int] = None
    available_equipment: Optional[List[str]] = None
    operational_status: Optional[str] = None


@router.patch("/stations/{station_id}", response_model=Station)
async def update_station(station_id: str, payload: StationUpdate):
    """Backs both the daily roster update and operational-status changes
    from the station UI — a plain state write Agent 3 picks up on its next
    trigger, no special path needed."""
    station = await station_repo.get(station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(station, field, value)

    await station_repo.replace(station)
    return station
