"""
Tests for the optimization objective selector and max driving time constraint.
Covers both distance/time objective switching and time dimension enforcement.
"""
from app.models.request_models import Vehicle
from app.solvers.tsp_solver import TspSolver
from app.solvers.vrp_solver import VrpSolver
from app.solvers.cvrp_solver import CvrpSolver
from app.solvers.vrptw_solver import VrptwSolver
from tests.fixtures import (
    MEMPHIS_DISTANCE_MATRIX,
    MEMPHIS_DURATION_MATRIX,
    make_request,
    validate_or_fail,
)


# ── Optimization objective switching ─────────────────────────────────


def test_vrp_minimize_distance_returns_success():
    request = make_request("VRP", optimization_objective="distance")
    response = VrpSolver(request).solve()
    assert response.status == "SUCCESS"
    validate_or_fail(request, response)


def test_vrp_minimize_time_returns_success():
    request = make_request("VRP", optimization_objective="time")
    response = VrpSolver(request).solve()
    assert response.status == "SUCCESS"
    validate_or_fail(request, response)


def test_vrp_objective_differs_between_distance_and_time():
    """
    Minimizing distance vs time should yield different objective values,
    since distance_matrix and duration_matrix have different scales.
    """
    req_dist = make_request("VRP", optimization_objective="distance")
    req_time = make_request("VRP", optimization_objective="time")

    resp_dist = VrpSolver(req_dist).solve()
    resp_time = VrpSolver(req_time).solve()

    assert resp_dist.status == "SUCCESS"
    assert resp_time.status == "SUCCESS"
    validate_or_fail(req_dist, resp_dist)
    validate_or_fail(req_time, resp_time)
    # Objective values must differ because they measure different things
    assert resp_dist.objective_value != resp_time.objective_value


def test_tsp_minimize_time_returns_success():
    request = make_request("TSP", optimization_objective="time")
    response = TspSolver(request).solve()
    assert response.status == "SUCCESS"
    assert len(response.routes) == 1
    validate_or_fail(request, response)


def test_cvrp_minimize_time_returns_success():
    from app.models.request_models import Location
    from tests.fixtures import MEMPHIS_LOCATIONS

    locs = [
        MEMPHIS_LOCATIONS[0],
        MEMPHIS_LOCATIONS[1].model_copy(update={"demand": 3}),
        MEMPHIS_LOCATIONS[2].model_copy(update={"demand": 4}),
        MEMPHIS_LOCATIONS[3].model_copy(update={"demand": 2}),
    ]
    vehicles = [Vehicle(id=0, capacity=10, max_distance=100_000),
                Vehicle(id=1, capacity=10, max_distance=100_000)]

    request = make_request("CVRP", locations=locs, vehicles=vehicles,
                           optimization_objective="time")
    response = CvrpSolver(request).solve()
    assert response.status == "SUCCESS"
    validate_or_fail(request, response)


# ── Duration in response ─────────────────────────────────────────────


def test_response_includes_total_duration():
    """Every route should report total_duration_s alongside total_distance_m."""
    request = make_request("VRP")
    response = VrpSolver(request).solve()
    validate_or_fail(request, response)

    for route in response.routes:
        assert route.total_duration_s is not None
        assert route.total_duration_s > 0
        assert route.total_distance_m > 0


def test_duration_uses_duration_matrix():
    """
    Verify total_duration_s is computed from the duration matrix, not the
    distance matrix, by checking the value is in the right order of magnitude.
    Duration matrix values are in seconds (~600–2500), distance in meters (~8000–34000).
    """
    request = make_request("VRP")
    response = VrpSolver(request).solve()
    validate_or_fail(request, response)

    for route in response.routes:
        # Duration should be much smaller than distance (seconds vs meters)
        assert route.total_duration_s < route.total_distance_m


# ── Max driving time constraint ──────────────────────────────────────


def test_vrp_respects_max_time():
    """Routes should not exceed the vehicle's max_time."""
    request = make_request("VRP")
    response = VrpSolver(request).solve()
    validate_or_fail(request, response)

    for route in response.routes:
        # With default max_time (57600s = 16h), routes should be well within limits
        assert route.total_duration_s <= 57600


def test_vrp_tight_max_time_drops_visits_or_no_solution():
    """
    With a very tight max_time, the solver should either drop visits or
    return no solution rather than violating the constraint.
    """
    tight_vehicles = [
        Vehicle(id=0, max_distance=100_000, max_time=500),
        Vehicle(id=1, max_distance=100_000, max_time=500),
    ]
    request = make_request("VRP", vehicles=tight_vehicles)
    response = VrpSolver(request).solve()
    validate_or_fail(request, response)

    if response.status == "SUCCESS":
        for route in response.routes:
            assert route.total_duration_s <= 500
    else:
        assert response.status == "NO_SOLUTION"


def test_tsp_max_time_from_vehicle_model():
    """TSP solver sets max_time=360_000; verify it doesn't block normal solutions."""
    request = make_request("TSP")
    response = TspSolver(request).solve()
    assert response.status == "SUCCESS"
    validate_or_fail(request, response)
    assert response.routes[0].total_duration_s <= 360_000


# ── Duration matrix fallback ─────────────────────────────────────────


def test_fallback_to_distance_matrix_when_no_duration():
    """When duration_matrix is empty, solver should fall back to distance_matrix."""
    # Need large max_time since distance values (meters) become "seconds" in fallback
    big_vehicles = [
        Vehicle(id=0, max_distance=100_000, max_time=500_000),
        Vehicle(id=1, max_distance=100_000, max_time=500_000),
    ]
    request = make_request("VRP", duration_matrix=[], vehicles=big_vehicles)
    response = VrpSolver(request).solve()

    assert response.status == "SUCCESS"
    validate_or_fail(request, response)
    for route in response.routes:
        # With fallback, duration equals distance (same matrix used for both)
        assert route.total_duration_s == route.total_distance_m
