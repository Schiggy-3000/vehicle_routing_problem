"""
Memphis, TN test fixtures derived from 01_create_distance_matrix.ipynb and
02_solver.ipynb. Use these in all solver tests so results are verifiable
against the known notebook output.

Locations:
  0  3610 Hacks Cross Rd        (depot)
  1  1921 Elvis Presley Blvd
  2  149 Union Avenue
  3  1034 Audubon Drive

Distance matrix values are in meters (driving distance).
Duration matrix values are in seconds (estimated from distance @ 50 km/h).
"""
import json
from pathlib import Path

from app.models.request_models import Location, PickupDeliveryPair, SolveRequest, Vehicle
from app.models.response_models import SolveResponse
from tests.backend.solution_validator import validate_solution

# Root of the sample_datasets directory
INSTANCES_DIR = Path(__file__).resolve().parent.parent.parent / "sample_datasets"


def validate_or_fail(request: SolveRequest, response: SolveResponse) -> None:
    """Run the solution validator. Fails the test if any violations found."""
    violations = validate_solution(request, response)
    assert violations == [], "Solution violations:\n" + "\n".join(violations)


def load_instance(relative_path: str) -> dict:
    """Load a JSON test instance file relative to sample_datasets/."""
    path = INSTANCES_DIR / f"{relative_path}.json"
    with open(path) as f:
        return json.load(f)


def instance_to_request(data: dict) -> SolveRequest:
    """Convert a JSON instance dict to a SolveRequest."""
    return SolveRequest(
        problem_type=data["problem_type"],
        depot_index=0,
        locations=[Location(**loc) for loc in data["locations"]],
        vehicles=[Vehicle(**v) for v in data["vehicles"]],
        pickup_delivery_pairs=[
            PickupDeliveryPair(**p) for p in data.get("pickup_delivery_pairs", [])
        ],
        optimization_objective=data.get("optimization_objective", "distance"),
        distance_matrix=data.get("distance_matrix", []),
        duration_matrix=data.get("duration_matrix", []),
    )

# 4×4 driving distance matrix from the notebook (meters)
MEMPHIS_DISTANCE_MATRIX = [
    [0,     25288, 33362, 14933],
    [26314, 0,     8795,  11802],
    [34057, 8968,  0,     14082],
    [15511, 12071, 13930, 0    ],
]

# Approximate durations in seconds (distance / 50 km/h → seconds)
MEMPHIS_DURATION_MATRIX = [
    [0,    1823, 2403, 1076],
    [1896, 0,    634,  851 ],
    [2452, 646,  0,    1015],
    [1118, 870,  1004, 0   ],
]

MEMPHIS_LOCATIONS = [
    Location(id="loc_0", label="Hacks Cross Rd (Depot)", address="3610 Hacks Cross Rd, Memphis, TN", lat=35.0496, lng=-89.8581),
    Location(id="loc_1", label="Elvis Presley Blvd",     address="1921 Elvis Presley Blvd, Memphis, TN", lat=35.0465, lng=-90.0271),
    Location(id="loc_2", label="Union Avenue",           address="149 Union Avenue, Memphis, TN", lat=35.1495, lng=-90.0490),
    Location(id="loc_3", label="Audubon Drive",          address="1034 Audubon Drive, Memphis, TN", lat=35.1168, lng=-89.9549),
]

TWO_VEHICLES = [
    Vehicle(id=0, max_distance=100_000),
    Vehicle(id=1, max_distance=100_000),
]


def make_request(problem_type: str, **kwargs) -> SolveRequest:
    """Helper to build a minimal SolveRequest for the Memphis fixture."""
    defaults = dict(
        problem_type=problem_type,
        depot_index=0,
        locations=MEMPHIS_LOCATIONS,
        vehicles=TWO_VEHICLES,
        distance_matrix=MEMPHIS_DISTANCE_MATRIX,
        duration_matrix=MEMPHIS_DURATION_MATRIX,
    )
    defaults.update(kwargs)
    return SolveRequest(**defaults)
