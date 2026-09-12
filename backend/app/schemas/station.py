from typing import Annotated, Dict, List

from pydantic import BaseModel, Field

from app.schemas.common import Coordinate

NonNegativeInt = Annotated[int, Field(ge=0)]


class StationCreate(BaseModel):
    name: str
    station_type: str = "other"
    location: Coordinate
    responder_types: List[str]
    available_responders: Dict[str, NonNegativeInt]
    available_vehicles: NonNegativeInt
    available_equipment: List[str]
    equipment_counts: Dict[str, NonNegativeInt] = Field(default_factory=dict)


class Station(StationCreate):
    station_id: str
    operational_status: str
    current_deployments: List[str]
