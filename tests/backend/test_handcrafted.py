"""
Layer 3: Hand-crafted instance tests.
Small, deterministic instances where the correct answer is manually verifiable.
"""
from tests.backend.fixtures import load_instance, instance_to_request, validate_or_fail
from app.services.solver_service import solve


def test_tsp_triangle():
    """3 cities in a triangle — both tours cost 45."""
    data = load_instance("handcrafted/tsp_triangle")
    request = instance_to_request(data)
    response = solve(request)

    assert response.status == "SUCCESS"
    validate_or_fail(request, response)
    assert response.objective_value == 45
    assert len(response.routes) == 1

    # All 3 locations visited
    visited = {s.location_id for s in response.routes[0].stops}
    assert visited == {"loc_0", "loc_1", "loc_2"}


def test_cvrp_forced_split():
    """3 customers with demand 6 each, capacity 10 — forces 3 vehicles."""
    data = load_instance("handcrafted/cvrp_forced_split")
    request = instance_to_request(data)
    response = solve(request)

    assert response.status == "SUCCESS"
    validate_or_fail(request, response)
    assert len(response.routes) == 3

    # Each route serves exactly 1 non-depot customer
    for route in response.routes:
        non_depot = [s for s in route.stops if s.location_id != "loc_0"]
        assert len(non_depot) == 1, f"Route {route.vehicle_id} serves {len(non_depot)} customers"


def test_vrptw_forced_order():
    """Non-overlapping time windows [0,10], [20,30], [40,50] force order 1→2→3."""
    data = load_instance("handcrafted/vrptw_forced_order")
    request = instance_to_request(data)
    response = solve(request)

    assert response.status == "SUCCESS"
    validate_or_fail(request, response)
    assert len(response.routes) == 1

    stop_ids = [s.location_id for s in response.routes[0].stops]
    # Must be depot → loc_1 → loc_2 → loc_3 → depot
    assert stop_ids == ["loc_0", "loc_1", "loc_2", "loc_3", "loc_0"]


def test_pdp_precedence():
    """2 pickup-delivery pairs — pickup must precede delivery on same vehicle."""
    data = load_instance("handcrafted/pdp_precedence")
    request = instance_to_request(data)
    response = solve(request)

    assert response.status == "SUCCESS"
    validate_or_fail(request, response)

    # Verify each pair: pickup before delivery, same route
    for pair in data["pickup_delivery_pairs"]:
        pickup_id = pair["pickup_id"]
        delivery_id = pair["delivery_id"]
        found = False
        for route in response.routes:
            ids = [s.location_id for s in route.stops]
            if pickup_id in ids and delivery_id in ids:
                assert ids.index(pickup_id) < ids.index(delivery_id), (
                    f"Pickup {pickup_id} must precede delivery {delivery_id}"
                )
                found = True
        assert found, f"Pair {pickup_id}→{delivery_id} not found in any route"


def test_vrp_max_dist_split():
    """2 clusters far apart — max_distance forces 2 vehicles."""
    data = load_instance("handcrafted/vrp_max_dist_split")
    request = instance_to_request(data)
    response = solve(request)

    assert response.status == "SUCCESS"
    validate_or_fail(request, response)
    assert len(response.routes) == 2
    assert len(response.dropped_visits) == 0

    # Each route should serve exactly 2 customers (one cluster each)
    for route in response.routes:
        non_depot = [s for s in route.stops if s.location_id != "loc_0"]
        assert len(non_depot) == 2, f"Route {route.vehicle_id} serves {len(non_depot)} customers"
