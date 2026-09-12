from app.repositories.collections import station_repo
from app.schemas.common import Coordinate
from app.schemas.station import Station

# Two simulated stations the app knows about out of the box, so Agent 3
# (coordinator) always has real capacity to reason about without requiring a
# manual /stations registration call first. Coordinates sit on opposite
# sides of Ithaca, NY so the nearest-station logic in CoordinatorAgent has
# something meaningful to choose between, and their combined/individual
# responder counts are sized so both single-station and
# needs-additional-support (multi-station) scenarios are reachable in demos.
_DEFAULT_STATIONS = [
    Station(
        station_id="stn-sim-001",
        name="Riverside Fire & Rescue Station 1",
        station_type="fire",
        location=Coordinate(latitude=42.4430, longitude=-76.5019),
        responder_types=["fire", "EMS", "paramedic"],
        available_responders={"fire": 6, "EMS": 4, "paramedic": 2},
        available_vehicles=3,
        available_equipment=["fire_truck", "ambulance", "rescue_ladder"],
        equipment_counts={"fire_truck": 2, "ambulance": 1, "rescue_ladder": 1},
        operational_status="available",
        current_deployments=[],
    ),
    Station(
        station_id="stn-sim-002",
        name="Eastside EMS & Hazmat Station 2",
        station_type="EMS",
        location=Coordinate(latitude=42.4534, longitude=-76.4735),
        responder_types=["EMS", "paramedic", "hazmat"],
        available_responders={"EMS": 5, "paramedic": 3, "hazmat": 2},
        available_vehicles=2,
        available_equipment=["ambulance", "hazmat_suit", "decon_kit"],
        equipment_counts={"ambulance": 2, "hazmat_suit": 4},
        operational_status="available",
        current_deployments=[],
    ),
]


async def seed_default_stations() -> None:
    """Idempotently ensures the simulated stations above exist. Safe to call
    on every startup: an already-registered station (matched by id) is left
    untouched so real dispatch state / roster edits are never clobbered."""
    for station in _DEFAULT_STATIONS:
        if await station_repo.get(station.station_id) is None:
            await station_repo.insert(station)
