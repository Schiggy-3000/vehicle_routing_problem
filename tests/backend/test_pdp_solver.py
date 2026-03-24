from tests.backend.fixtures import MEMPHIS_LOCATIONS, MEMPHIS_DISTANCE_MATRIX, MEMPHIS_DURATION_MATRIX, validate_or_fail
from app.models.request_models import Location, PickupDeliveryPair, SolveRequest, Vehicle
from app.solvers.pdp_solver import PdpSolver


def test_pdp_pickup_before_delivery():
    """
    Pair: pickup=loc_1, delivery=loc_2.
    Verify pickup appears before delivery in every route that serves them.
    """
    vehicles = [Vehicle(id=0, max_distance=200_000), Vehicle(id=1, max_distance=200_000)]
    pairs = [PickupDeliveryPair(pickup_id="loc_1", delivery_id="loc_2")]

    request = SolveRequest(
        problem_type="PDP",
        depot_index=0,
        locations=MEMPHIS_LOCATIONS,
        vehicles=vehicles,
        pickup_delivery_pairs=pairs,
        distance_matrix=MEMPHIS_DISTANCE_MATRIX,
        duration_matrix=MEMPHIS_DURATION_MATRIX,
    )
    response = PdpSolver(request).solve()

    assert response.status == "SUCCESS"
    validate_or_fail(request, response)

    for route in response.routes:
        ids = [s.location_id for s in route.stops]
        if "loc_1" in ids and "loc_2" in ids:
            assert ids.index("loc_1") < ids.index("loc_2"), (
                "Pickup must appear before delivery in the route"
            )
