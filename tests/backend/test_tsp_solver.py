from tests.backend.fixtures import make_request, validate_or_fail
from app.solvers.tsp_solver import TspSolver


def test_tsp_finds_solution():
    request = make_request("TSP")
    response = TspSolver(request).solve()

    assert response.status == "SUCCESS"
    validate_or_fail(request, response)
    assert response.objective_value is not None and response.objective_value > 0
    assert len(response.routes) == 1, "TSP must use exactly 1 vehicle"

    route = response.routes[0]
    # All 4 locations should appear (depot appears at start and end)
    visited_ids = {s.location_id for s in route.stops}
    assert visited_ids == {"loc_0", "loc_1", "loc_2", "loc_3"}
    # Route starts and ends at depot
    assert route.stops[0].location_id == "loc_0"
    assert route.stops[-1].location_id == "loc_0"
