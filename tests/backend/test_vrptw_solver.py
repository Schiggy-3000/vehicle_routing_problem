from tests.backend.fixtures import MEMPHIS_DISTANCE_MATRIX, MEMPHIS_DURATION_MATRIX, validate_or_fail
from app.models.request_models import Location, SolveRequest, Vehicle
from app.solvers.vrptw_solver import VrptwSolver


def test_vrptw_respects_time_windows():
    """
    All locations have an open 24h window, so the solver should always find a solution.
    Arrival times should fall within each location's window.
    """
    locations = [
        Location(id="loc_0", label="Depot",             lat=35.0496, lng=-89.8581, time_window=(0, 86400)),
        Location(id="loc_1", label="Elvis Presley Blvd", lat=35.0465, lng=-90.0271, time_window=(0, 86400)),
        Location(id="loc_2", label="Union Avenue",       lat=35.1495, lng=-90.0490, time_window=(0, 86400)),
        Location(id="loc_3", label="Audubon Drive",      lat=35.1168, lng=-89.9549, time_window=(0, 86400)),
    ]
    vehicles = [Vehicle(id=0, max_distance=200_000), Vehicle(id=1, max_distance=200_000)]

    request = SolveRequest(
        problem_type="VRPTW",
        depot_index=0,
        locations=locations,
        vehicles=vehicles,
        distance_matrix=MEMPHIS_DISTANCE_MATRIX,
        duration_matrix=MEMPHIS_DURATION_MATRIX,
    )
    response = VrptwSolver(request).solve()

    assert response.status == "SUCCESS"
    validate_or_fail(request, response)

    for route in response.routes:
        for stop in route.stops:
            loc = next(l for l in locations if l.id == stop.location_id)
            if stop.arrival_time is not None:
                assert loc.time_window[0] <= stop.arrival_time <= loc.time_window[1], (
                    f"{stop.location_id} arrival {stop.arrival_time} outside "
                    f"window {loc.time_window}"
                )
