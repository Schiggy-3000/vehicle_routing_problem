"""
Layer 1: Independent solution validator.

Re-checks every constraint using only the request and response data,
without OR-Tools. Catches bugs in both constraint registration and
solution extraction.
"""
from typing import Dict, List

from app.models.request_models import SolveRequest
from app.models.response_models import SolveResponse


def validate_solution(request: SolveRequest, response: SolveResponse) -> List[str]:
    """Returns a list of violation messages. Empty list = valid solution."""
    if response.status != "SUCCESS":
        return []

    violations: List[str] = []

    # Build lookup: location_id → index in request.locations
    loc_id_to_idx: Dict[str, int] = {
        loc.id: i for i, loc in enumerate(request.locations)
    }
    depot_id = request.locations[request.depot_index].id

    # ── Universal checks ─────────────────────────────────────────────

    # Check 1: All locations accounted for
    _check_all_locations_accounted(request, response, depot_id, loc_id_to_idx, violations)

    # Check 2: Routes start and end at depot
    _check_depot_endpoints(response, depot_id, violations)

    # Check 3 & 4: Distance and duration recomputation
    if request.distance_matrix:
        _check_distance_recomputation(request, response, loc_id_to_idx, violations)
    if request.duration_matrix:
        _check_duration_recomputation(request, response, loc_id_to_idx, violations)

    # Check 5 & 6: Max distance and max time
    _check_vehicle_limits(request, response, loc_id_to_idx, violations)

    # ── Problem-type-specific checks ─────────────────────────────────

    if request.problem_type == "TSP":
        _check_tsp_single_vehicle(response, violations)

    if request.problem_type == "CVRP":
        _check_capacity(request, response, loc_id_to_idx, violations)

    if request.problem_type == "VRPTW":
        _check_time_windows(request, response, loc_id_to_idx, violations)
        if request.duration_matrix:
            _check_arrival_time_consistency(request, response, loc_id_to_idx, violations)

    if request.problem_type == "PDP":
        _check_pickup_delivery(request, response, violations)

    return violations


# ── Check implementations ────────────────────────────────────────────


def _check_all_locations_accounted(
    request: SolveRequest,
    response: SolveResponse,
    depot_id: str,
    loc_id_to_idx: Dict[str, int],
    violations: List[str],
) -> None:
    non_depot_ids = {loc.id for loc in request.locations if loc.id != depot_id}

    routed_ids = set()
    for route in response.routes:
        for stop in route.stops:
            if stop.location_id != depot_id:
                if stop.location_id in routed_ids:
                    violations.append(
                        f"Duplicate: {stop.location_id} appears in multiple routes"
                    )
                routed_ids.add(stop.location_id)

    dropped_ids = set(response.dropped_visits)

    missing = non_depot_ids - routed_ids - dropped_ids
    if missing:
        violations.append(
            f"Missing locations (not routed and not dropped): {sorted(missing)}"
        )

    overlap = routed_ids & dropped_ids
    if overlap:
        violations.append(
            f"Locations both routed and dropped: {sorted(overlap)}"
        )


def _check_depot_endpoints(
    response: SolveResponse, depot_id: str, violations: List[str]
) -> None:
    for i, route in enumerate(response.routes):
        if not route.stops:
            violations.append(f"Route {i}: empty stops list")
            continue
        if route.stops[0].location_id != depot_id:
            violations.append(
                f"Route {i}: starts at {route.stops[0].location_id}, expected depot {depot_id}"
            )
        if route.stops[-1].location_id != depot_id:
            violations.append(
                f"Route {i}: ends at {route.stops[-1].location_id}, expected depot {depot_id}"
            )


def _check_distance_recomputation(
    request: SolveRequest,
    response: SolveResponse,
    loc_id_to_idx: Dict[str, int],
    violations: List[str],
) -> None:
    matrix = request.distance_matrix
    for i, route in enumerate(response.routes):
        recomputed = 0
        for j in range(len(route.stops) - 1):
            from_idx = loc_id_to_idx.get(route.stops[j].location_id)
            to_idx = loc_id_to_idx.get(route.stops[j + 1].location_id)
            if from_idx is None or to_idx is None:
                violations.append(
                    f"Route {i}: unknown location_id in stop sequence"
                )
                return
            recomputed += matrix[from_idx][to_idx]
        if recomputed != route.total_distance_m:
            violations.append(
                f"Route {i}: total_distance_m={route.total_distance_m} "
                f"but recomputed={recomputed} (delta={recomputed - route.total_distance_m})"
            )


def _check_duration_recomputation(
    request: SolveRequest,
    response: SolveResponse,
    loc_id_to_idx: Dict[str, int],
    violations: List[str],
) -> None:
    matrix = request.duration_matrix
    for i, route in enumerate(response.routes):
        if route.total_duration_s is None:
            continue
        recomputed = 0
        for j in range(len(route.stops) - 1):
            from_idx = loc_id_to_idx.get(route.stops[j].location_id)
            to_idx = loc_id_to_idx.get(route.stops[j + 1].location_id)
            if from_idx is None or to_idx is None:
                return
            recomputed += matrix[from_idx][to_idx]
        if recomputed != route.total_duration_s:
            violations.append(
                f"Route {i}: total_duration_s={route.total_duration_s} "
                f"but recomputed={recomputed} (delta={recomputed - route.total_duration_s})"
            )


def _check_vehicle_limits(
    request: SolveRequest,
    response: SolveResponse,
    loc_id_to_idx: Dict[str, int],
    violations: List[str],
) -> None:
    for i, route in enumerate(response.routes):
        vehicle = request.vehicles[route.vehicle_id]

        # Recompute distance from matrix if available
        if request.distance_matrix:
            dist = 0
            for j in range(len(route.stops) - 1):
                fi = loc_id_to_idx.get(route.stops[j].location_id)
                ti = loc_id_to_idx.get(route.stops[j + 1].location_id)
                if fi is not None and ti is not None:
                    dist += request.distance_matrix[fi][ti]
            if dist > vehicle.max_distance:
                violations.append(
                    f"Route {i}: distance {dist} exceeds vehicle max_distance {vehicle.max_distance}"
                )

        # Recompute duration from matrix if available
        if request.duration_matrix:
            dur = 0
            for j in range(len(route.stops) - 1):
                fi = loc_id_to_idx.get(route.stops[j].location_id)
                ti = loc_id_to_idx.get(route.stops[j + 1].location_id)
                if fi is not None and ti is not None:
                    dur += request.duration_matrix[fi][ti]
            if dur > vehicle.max_time:
                violations.append(
                    f"Route {i}: duration {dur} exceeds vehicle max_time {vehicle.max_time}"
                )


def _check_tsp_single_vehicle(
    response: SolveResponse, violations: List[str]
) -> None:
    if len(response.routes) != 1:
        violations.append(
            f"TSP: expected 1 route, got {len(response.routes)}"
        )


def _check_capacity(
    request: SolveRequest,
    response: SolveResponse,
    loc_id_to_idx: Dict[str, int],
    violations: List[str],
) -> None:
    depot_id = request.locations[request.depot_index].id
    for i, route in enumerate(response.routes):
        vehicle = request.vehicles[route.vehicle_id]
        if vehicle.capacity == 0:
            continue  # unlimited
        load = 0
        for stop in route.stops:
            if stop.location_id == depot_id:
                continue
            idx = loc_id_to_idx.get(stop.location_id)
            if idx is not None:
                load += request.locations[idx].demand
        if load > vehicle.capacity:
            violations.append(
                f"Route {i}: load {load} exceeds vehicle capacity {vehicle.capacity}"
            )


def _check_time_windows(
    request: SolveRequest,
    response: SolveResponse,
    loc_id_to_idx: Dict[str, int],
    violations: List[str],
) -> None:
    for i, route in enumerate(response.routes):
        for stop in route.stops:
            if stop.arrival_time is None:
                continue
            idx = loc_id_to_idx.get(stop.location_id)
            if idx is None:
                continue
            tw = request.locations[idx].time_window
            if stop.arrival_time < tw[0] or stop.arrival_time > tw[1]:
                violations.append(
                    f"Route {i}: {stop.location_id} arrival_time={stop.arrival_time} "
                    f"outside time_window [{tw[0]}, {tw[1]}]"
                )


def _check_arrival_time_consistency(
    request: SolveRequest,
    response: SolveResponse,
    loc_id_to_idx: Dict[str, int],
    violations: List[str],
) -> None:
    matrix = request.duration_matrix
    for i, route in enumerate(response.routes):
        for j in range(len(route.stops) - 1):
            curr = route.stops[j]
            nxt = route.stops[j + 1]
            if curr.arrival_time is None or nxt.arrival_time is None:
                continue
            fi = loc_id_to_idx.get(curr.location_id)
            ti = loc_id_to_idx.get(nxt.location_id)
            if fi is None or ti is None:
                continue
            travel = matrix[fi][ti]
            if curr.arrival_time + travel > nxt.arrival_time:
                violations.append(
                    f"Route {i}: arrival at {curr.location_id}={curr.arrival_time} "
                    f"+ travel {travel} = {curr.arrival_time + travel} "
                    f"> arrival at {nxt.location_id}={nxt.arrival_time} (time travel)"
                )


def _check_pickup_delivery(
    request: SolveRequest,
    response: SolveResponse,
    violations: List[str],
) -> None:
    for pair in request.pickup_delivery_pairs:
        pickup_route = None
        pickup_pos = None
        delivery_route = None
        delivery_pos = None

        for i, route in enumerate(response.routes):
            stop_ids = [s.location_id for s in route.stops]
            if pair.pickup_id in stop_ids:
                pickup_route = i
                pickup_pos = stop_ids.index(pair.pickup_id)
            if pair.delivery_id in stop_ids:
                delivery_route = i
                delivery_pos = stop_ids.index(pair.delivery_id)

        if pickup_route is None:
            if pair.pickup_id not in response.dropped_visits:
                violations.append(f"PDP: pickup {pair.pickup_id} not found in any route or dropped_visits")
            continue
        if delivery_route is None:
            if pair.delivery_id not in response.dropped_visits:
                violations.append(f"PDP: delivery {pair.delivery_id} not found in any route or dropped_visits")
            continue

        if pickup_route != delivery_route:
            violations.append(
                f"PDP: {pair.pickup_id}→{pair.delivery_id} on different vehicles "
                f"(route {pickup_route} vs {delivery_route})"
            )
        elif pickup_pos >= delivery_pos:
            violations.append(
                f"PDP: {pair.pickup_id} (pos {pickup_pos}) not before "
                f"{pair.delivery_id} (pos {delivery_pos}) in route {pickup_route}"
            )
