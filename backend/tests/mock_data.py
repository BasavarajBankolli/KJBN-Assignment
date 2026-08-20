"""Shared mock data for tests - realistic trucks modeled on the live DataSF payload.

All tests use this data; nothing depends on the live DataSF service.
"""

from app.schemas.food_truck import FoodTruck

#: Matches the default DataSF base URL configured in app settings.
DATASF_TEST_URL = "https://data.sfgov.org/resource/rqzj-sfat.json"

#: Search center used by tests (SF City Hall).
CENTER_LAT = 37.7793
CENTER_LNG = -122.4193

TRUCK_A = FoodTruck(
    id="1",
    applicant="Golden Grill",
    facility_type="Truck",
    location_description="CIVIC CENTER PLAZA: LARKIN ST to POLK ST",
    address="100 LARKIN ST",
    food_items="burgers: fries: milkshakes",
    latitude=37.7793,
    longitude=-122.4193,
    status="APPROVED",
)

TRUCK_B = FoodTruck(
    id="2",
    applicant="Taqueria La Mexicana",
    facility_type="Truck",
    location_description="MISSION ST: 21ST ST to 22ND ST",
    address="2200 MISSION ST",
    food_items="tacos: burritos: quesadillas",
    latitude=37.7683,
    longitude=-122.4193,
    status="APPROVED",
)

TRUCK_C = FoodTruck(
    id="3",
    applicant="Cafe Luna",
    facility_type="Push Cart",
    location_description="DOLORES ST: 18TH ST to 19TH ST",
    address="300 DOLORES ST",
    food_items="coffee: pastries: sandwiches",
    latitude=37.7615,
    longitude=-122.4265,
    status="APPROVED",
)

TRUCK_NO_COORDS = FoodTruck(
    id="4",
    applicant="Ghost Kitchen",
    facility_type="Truck",
    address="UNKNOWN LOCATION",
    food_items="mystery meals",
    latitude=None,
    longitude=None,
    status="APPROVED",
)

ALL_TRUCKS = [TRUCK_A, TRUCK_B, TRUCK_C, TRUCK_NO_COORDS]


def raw_record(truck: FoodTruck) -> dict:
    """Serialize an internal truck into a raw DataSF-style JSON record."""
    return {
        "objectid": truck.id,
        "applicant": truck.applicant,
        "facilitytype": truck.facility_type,
        "locationdescription": truck.location_description,
        "address": truck.address,
        "permit": "MFF-TEST-001",
        "status": truck.status,
        "fooditems": truck.food_items,
        "latitude": str(truck.latitude) if truck.latitude is not None else None,
        "longitude": str(truck.longitude) if truck.longitude is not None else None,
        "schedule": "http://bsm.sfdpw.org/report.pdf",
        "location": {
            "latitude": str(truck.latitude) if truck.latitude is not None else None,
            "longitude": str(truck.longitude) if truck.longitude is not None else None,
        },
        ":@computed_region_yftq_j783": "14",
    }