from __future__ import annotations

import time
from abc import ABC, abstractmethod

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.models.request_models import SolveRequest
from app.models.response_models import RouteStop, SolveResponse, VehicleRoute


class BaseSolver(ABC):
    """
    Encapsulates the OR-Tools boilerplate from 02_solver.ipynb.
    Subclasses override _add_constraints() to extend for each problem type.
    """

    def __init__(self, request: SolveRequest):
        self.request = request
        self.matrix = request.distance_matrix
        self.duration_matrix = request.duration_matrix or request.distance_matrix
        self.objective = request.optimization_objective
        self.num_locations = len(request.locations)
        self.num_vehicles = len(request.vehicles)
        self.depot = request.depot_index

        self._validate(request)

        self.manager: pywrapcp.RoutingIndexManager | None = None
        self.routing: pywrapcp.RoutingModel | None = None
        self.transit_callback_index: int | None = None
        self.distance_callback_index: int | None = None
        self.duration_callback_index: int | None = None

    def _validate(self, request: SolveRequest) -> None:
        if self.depot < 0 or self.depot >= self.num_locations:
            raise ValueError(
                f"depot_index {self.depot} out of range for "
                f"{self.num_locations} locations"
            )
        if request.distance_matrix:
            n = self.num_locations
            if len(request.distance_matrix) != n:
                raise ValueError(
                    f"distance_matrix has {len(request.distance_matrix)} rows "
                    f"but there are {n} locations"
                )
            for i, row in enumerate(request.distance_matrix):
                if len(row) != n:
                    raise ValueError(
                        f"distance_matrix row {i} has {len(row)} columns, "
                        f"expected {n}"
                    )

    # ------------------------------------------------------------------
    # Setup helpers (mirror the notebook's step-by-step pattern)
    # ------------------------------------------------------------------

    def _create_manager_and_model(self) -> None:
        self.manager = pywrapcp.RoutingIndexManager(
            self.num_locations, self.num_vehicles, self.depot
        )
        self.routing = pywrapcp.RoutingModel(self.manager)

    def _register_distance_callback(self) -> None:
        dist_matrix = self.matrix

        def distance_cb(from_index: int, to_index: int) -> int:
            return dist_matrix[self.manager.IndexToNode(from_index)][self.manager.IndexToNode(to_index)]

        self.distance_callback_index = self.routing.RegisterTransitCallback(distance_cb)
        self.transit_callback_index = self.distance_callback_index  # used by _add_distance_dimension

        dur_matrix = self.duration_matrix

        def duration_cb(from_index: int, to_index: int) -> int:
            return dur_matrix[self.manager.IndexToNode(from_index)][self.manager.IndexToNode(to_index)]

        self.duration_callback_index = self.routing.RegisterTransitCallback(duration_cb)

        # Arc cost = the optimization objective
        arc_cost_index = self.duration_callback_index if self.objective == "time" else self.distance_callback_index
        self.routing.SetArcCostEvaluatorOfAllVehicles(arc_cost_index)

    def _add_distance_dimension(self, span_cost_coefficient: int = 100):
        """Add a Distance dimension with a global span cost. Returns the dimension."""
        max_distance = max(v.max_distance for v in self.request.vehicles)
        self.routing.AddDimension(
            self.transit_callback_index,
            0,
            max_distance,
            True,
            "Distance",
        )
        dimension = self.routing.GetDimensionOrDie("Distance")
        dimension.SetGlobalSpanCostCoefficient(span_cost_coefficient)
        return dimension

    def _add_time_dimension(self, span_cost_coefficient: int = 0):
        """Add a Time dimension using the duration callback. Returns the dimension."""
        max_time = max(v.max_time for v in self.request.vehicles)
        self.routing.AddDimension(
            self.duration_callback_index,
            0,         # no slack (VRPTW overrides this)
            max_time,
            True,      # start_cumul_to_zero
            "Time",
        )
        dimension = self.routing.GetDimensionOrDie("Time")
        dimension.SetGlobalSpanCostCoefficient(span_cost_coefficient)
        return dimension

    def _get_search_parameters(self) -> pywrapcp.DefaultRoutingSearchParameters:
        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        params.time_limit.seconds = 30  # guard against Cloud Run timeouts
        return params

    # ------------------------------------------------------------------
    # Extension point for problem-specific constraints
    # ------------------------------------------------------------------

    @abstractmethod
    def _add_constraints(self) -> None:
        """Add dimensions and constraints specific to the problem type."""

    # ------------------------------------------------------------------
    # Solution extraction (mirrors print_solution() from the notebook)
    # ------------------------------------------------------------------

    def _extract_solution(self, solution: pywrapcp.Assignment) -> SolveResponse:
        routes: list[VehicleRoute] = []
        dropped_visits: list[str] = []

        # Collect dropped nodes (penalty-based dropping, CVRP/VRPTW with slack)
        for node in range(self.routing.Size()):
            if self.routing.IsStart(node) or self.routing.IsEnd(node):
                continue
            if solution.Value(self.routing.NextVar(node)) == node:
                loc_index = self.manager.IndexToNode(node)
                dropped_visits.append(self.request.locations[loc_index].id)

        for vehicle_id in range(self.num_vehicles):
            index = self.routing.Start(vehicle_id)
            stops: list[RouteStop] = []
            route_distance = 0
            route_duration = 0
            route_load = 0

            while not self.routing.IsEnd(index):
                node = self.manager.IndexToNode(index)
                loc = self.request.locations[node]

                arrival_time = self._get_arrival_time(solution, index)
                stops.append(RouteStop(
                    location_id=loc.id,
                    label=loc.label,
                    lat=loc.lat,
                    lng=loc.lng,
                    arrival_time=arrival_time,
                    cumulative_distance=route_distance,
                ))
                route_load += loc.demand

                next_index = solution.Value(self.routing.NextVar(index))
                next_node = self.manager.IndexToNode(next_index)
                route_distance += self.matrix[node][next_node]
                route_duration += self.duration_matrix[node][next_node]
                index = next_index

            # Add final depot stop
            node = self.manager.IndexToNode(index)
            loc = self.request.locations[node]
            arrival_time = self._get_arrival_time(solution, index)
            stops.append(RouteStop(
                location_id=loc.id,
                label=loc.label,
                lat=loc.lat,
                lng=loc.lng,
                arrival_time=arrival_time,
                cumulative_distance=route_distance,
            ))

            # Only include routes that actually visit at least one non-depot node
            non_depot_stops = [s for s in stops if s.location_id != self.request.locations[self.depot].id]
            if non_depot_stops:
                routes.append(VehicleRoute(
                    vehicle_id=vehicle_id,
                    stops=stops,
                    total_distance_m=route_distance,
                    total_duration_s=route_duration,
                    total_load=route_load if route_load > 0 else None,
                ))

        return SolveResponse(
            status="SUCCESS",
            problem_type=self.request.problem_type,
            objective_value=solution.ObjectiveValue(),
            routes=routes,
            dropped_visits=dropped_visits,
        )

    def _get_arrival_time(self, solution: pywrapcp.Assignment, index: int) -> int | None:
        """Override in VRPTW solver to return time dimension cumvar value."""
        return None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def solve(self) -> SolveResponse:
        start_ms = time.monotonic_ns() // 1_000_000

        self._create_manager_and_model()
        self._register_distance_callback()
        self._add_constraints()

        params = self._get_search_parameters()
        solution = self.routing.SolveWithParameters(params)

        elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

        if not solution:
            return SolveResponse(
                status="NO_SOLUTION",
                problem_type=self.request.problem_type,
                solver_wall_time_ms=elapsed_ms,
            )

        response = self._extract_solution(solution)
        response.solver_wall_time_ms = elapsed_ms
        return response
