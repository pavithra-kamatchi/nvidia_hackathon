from typing import Dict, List

from pydantic import BaseModel

from app.schemas.common import Coordinate


class StationCreate(BaseModel):
    name: str
    location: Coordinate
    responder_types: List[str]
    available_responders: Dict[str, int]
    available_vehicles: int
    available_equipment: List[str]


class Station(StationCreate):
    station_id: str
    operational_status: str
    current_deployments: List[str]
