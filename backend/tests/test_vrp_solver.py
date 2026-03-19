from tests.fixtures import make_request
from app.solvers.vrp_solver import VrpSolver


def test_vrp_finds_solution():
    request = make_request("VRP")
    response = VrpSolver(request).solve()

    assert response.status == "SUCCESS"
    assert response.objective_value is not None and response.objective_value > 0

    # All non-depot locations must appear across all routes
    all_visited = {
        stop.location_id
        for route in response.routes
        for stop in route.stops
    }
    assert {"loc_1", "loc_2", "loc_3"}.issubset(all_visited)

    # Each route starts and ends at the depot
    for route in response.routes:
        assert route.stops[0].location_id == "loc_0"
        assert route.stops[-1].location_id == "loc_0"
        assert route.total_distance_m > 0


def test_vrp_objective_matches_notebook():
    """
    The notebook reports Objective: 6406522 for 2 vehicles on the Memphis data.
    Verify our port produces the same value.
    """
    request = make_request("VRP")
    response = VrpSolver(request).solve()
    assert response.objective_value == 6_406_522
