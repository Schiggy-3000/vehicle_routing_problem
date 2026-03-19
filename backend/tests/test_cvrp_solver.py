from tests.fixtures import MEMPHIS_LOCATIONS, make_request
from app.models.request_models import Location, Vehicle
from app.solvers.cvrp_solver import CvrpSolver


def test_cvrp_respects_capacity():
    # Assign demands: loc_1=5, loc_2=5, loc_3=5 (total=15), 2 vehicles each cap=10
    locations = [
        loc.model_copy(update={"demand": 5 if loc.id != "loc_0" else 0})
        for loc in MEMPHIS_LOCATIONS
    ]
    vehicles = [
        Vehicle(id=0, capacity=10, max_distance=100_000),
        Vehicle(id=1, capacity=10, max_distance=100_000),
    ]
    request = make_request("CVRP", locations=locations, vehicles=vehicles)
    response = CvrpSolver(request).solve()

    assert response.status == "SUCCESS"

    # No vehicle should exceed capacity 10
    for route in response.routes:
        load = sum(
            next(loc.demand for loc in locations if loc.id == stop.location_id)
            for stop in route.stops
            if stop.location_id != "loc_0"
        )
        assert load <= 10, f"Vehicle {route.vehicle_id} exceeded capacity: {load}"
