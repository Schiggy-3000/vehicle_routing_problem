"""
Layer 2: Benchmark instance tests.
Solves published VRP benchmark instances, validates constraints, and checks
that objective values are within a reasonable range of best-known solutions.
"""
import pytest
from tests.backend.fixtures import load_instance, instance_to_request, validate_or_fail
from app.services.solver_service import solve


BENCHMARK_INSTANCES = [
    "TSPLIB/burma14",
    "TSPLIB/ulysses16",
    "TSPLIB/ulysses22",
    "TSPLIB/gr96",
]


@pytest.mark.parametrize("instance_path", BENCHMARK_INSTANCES)
def test_benchmark_feasibility(instance_path):
    """Solve a benchmark instance and validate all constraints."""
    data = load_instance(instance_path)
    request = instance_to_request(data)
    response = solve(request)

    assert response.status == "SUCCESS", (
        f"{data['name']}: expected SUCCESS, got {response.status}"
    )
    validate_or_fail(request, response)


@pytest.mark.parametrize("instance_path", BENCHMARK_INSTANCES)
def test_benchmark_quality(instance_path):
    """Check solver objective is within threshold of best-known."""
    data = load_instance(instance_path)
    expected = data.get("expected", {})
    best_known = expected.get("best_known_objective")
    threshold = expected.get("quality_threshold")

    if best_known is None or threshold is None:
        pytest.skip(f"No best-known objective or threshold for {data['name']}")

    request = instance_to_request(data)
    response = solve(request)

    assert response.status == "SUCCESS"

    # Compare total route distance (not objective_value, which includes span penalties)
    total_distance = sum(r.total_distance_m for r in response.routes)
    ratio = total_distance / best_known
    assert ratio <= threshold, (
        f"{data['name']}: total distance {total_distance} is {ratio:.1f}x "
        f"best-known {best_known} (threshold: {threshold}x)"
    )
