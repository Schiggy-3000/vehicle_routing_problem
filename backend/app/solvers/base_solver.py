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
        self.num_locations = len(request.locations)
        self.num_vehicles = len(request.vehicles)
        self.depot = request.depot_index

        self.manager: pywrapcp.RoutingIndexManager | None = None
        self.routing: pywrapcp.RoutingModel | None = None
        self.transit_callback_index: int | None = None

    # ------------------------------------------------------------------
    # Setup helpers (mirror the notebook's step-by-step pattern)
    # ------------------------------------------------------------------

    def _create_manager_and_model(self) -> None:
        self.manager = pywrapcp.RoutingIndexManager(
            self.num_locations, self.num_vehicles, self.depot
        )
        self.routing = pywrapcp.RoutingModel(self.manager)

    def _register_distance_callback(self) -> None:
        matrix = self.matrix

        def distance_callback(from_index: int, to_index: int) -> int:
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            return matrix[from_node][to_node]

        self.transit_callback_index = self.routing.RegisterTransitCallback(distance_callback)
        self.routing.SetArcCostEvaluatorOfAllVehicles(self.transit_callback_index)

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
                route_distance += self.matrix[node][self.manager.IndexToNode(next_index)]
                index = next_index

            # Add final depot stop
            node = self.manager.IndexToNode(index)
            loc = self.request.locations[node]
            stops.append(RouteStop(
                location_id=loc.id,
                label=loc.label,
                lat=loc.lat,
                lng=loc.lng,
                cumulative_distance=route_distance,
            ))

            # Only include routes that actually visit at least one non-depot node
            non_depot_stops = [s for s in stops if s.location_id != self.request.locations[self.depot].id]
            if non_depot_stops:
                routes.append(VehicleRoute(
                    vehicle_id=vehicle_id,
                    stops=stops,
                    total_distance_m=route_distance,
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
