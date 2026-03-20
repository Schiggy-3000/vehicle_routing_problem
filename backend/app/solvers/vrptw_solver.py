from __future__ import annotations

from ortools.constraint_solver import pywrapcp

from app.solvers.base_solver import BaseSolver


class VrptwSolver(BaseSolver):
    """
    VRP with Time Windows: each location has a [open, close] time window (seconds).
    Uses the duration matrix (travel time in seconds) instead of the distance matrix
    for the time dimension, while still minimising distance as the arc cost.
    """

    def __init__(self, request):
        super().__init__(request)
        self._time_dimension_name = "Time"

    def _add_constraints(self) -> None:
        time_callback_index = self.duration_callback_index

        # Time horizon must cover the full day for time windows to work,
        # but also respect user's max_time if larger than 24h.
        vehicle_max_time = max(v.max_time for v in self.request.vehicles)
        max_time = max(86400, vehicle_max_time)

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
