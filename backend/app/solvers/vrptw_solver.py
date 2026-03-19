from __future__ import annotations

from ortools.constraint_solver import pywrapcp

from app.models.request_models import SolveRequest
from app.solvers.base_solver import BaseSolver


class VrptwSolver(BaseSolver):
    """
    VRP with Time Windows: each location has a [open, close] time window (seconds).
    Uses the duration matrix (travel time in seconds) instead of the distance matrix
    for the time dimension, while still minimising distance as the arc cost.
    """

    def __init__(self, request: SolveRequest):
        super().__init__(request)
        self._time_dimension_name = "Time"

    def _add_constraints(self) -> None:
        duration_matrix = self.request.duration_matrix
        if not duration_matrix:
            # Fall back to distance matrix if no durations provided
            duration_matrix = self.matrix

        # Register a separate time callback using the duration matrix
        def time_callback(from_index: int, to_index: int) -> int:
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            return duration_matrix[from_node][to_node]

        time_callback_index = self.routing.RegisterTransitCallback(time_callback)

        # Max time horizon: 24 hours in seconds
        max_time = 86400

        self.routing.AddDimension(
            time_callback_index,
            max_time,   # allow waiting at nodes (slack)
            max_time,
            False,      # don't force start cumul to zero (vehicles may depart anytime)
            self._time_dimension_name,
        )
        time_dimension = self.routing.GetDimensionOrDie(self._time_dimension_name)

        # Apply time windows per location
        for i, loc in enumerate(self.request.locations):
            index = self.manager.NodeToIndex(i)
            open_t, close_t = loc.time_window
            time_dimension.CumulVar(index).SetRange(open_t, close_t)

        # Minimise overall span (optional but improves solution quality)
        time_dimension.SetGlobalSpanCostCoefficient(10)

    def _get_arrival_time(self, solution: pywrapcp.Assignment, index: int) -> int | None:
        time_dimension = self.routing.GetDimensionOrDie(self._time_dimension_name)
        return solution.Min(time_dimension.CumulVar(index))
