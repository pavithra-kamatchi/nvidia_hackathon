import unittest

from pydantic import ValidationError

from app.schemas.common import Coordinate
from app.schemas.station import StationCreate


class InputValidationTests(unittest.TestCase):
    def test_coordinate_ranges_are_enforced(self):
        with self.assertRaises(ValidationError):
            Coordinate(latitude=91, longitude=0)
        with self.assertRaises(ValidationError):
            Coordinate(latitude=0, longitude=-181)

    def test_station_resources_cannot_be_negative(self):
        with self.assertRaises(ValidationError):
            StationCreate(
                name="Invalid station",
                station_type="fire",
                location=Coordinate(latitude=42.44, longitude=-76.48),
                responder_types=["fire"],
                available_responders={"fire": -1},
                available_vehicles=1,
                available_equipment=[],
            )


if __name__ == "__main__":
    unittest.main()
