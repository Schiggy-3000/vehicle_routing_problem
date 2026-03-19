from app.solvers.base_solver import BaseSolver


class VrpSolver(BaseSolver):
    """
    Vehicle Routing Problem: multiple vehicles, minimize total distance.
    Adds a Distance dimension with a global span cost coefficient — identical
    to the pattern used in 02_solver.ipynb.
    """

    def _add_constraints(self) -> None:
        max_distance = max(v.max_distance for v in self.request.vehicles)

        self.routing.AddDimension(
            self.transit_callback_index,
            0,           # no slack
            max_distance,
            True,        # start_cumul_to_zero
            "Distance",
        )
        distance_dimension = self.routing.GetDimensionOrDie("Distance")
        # Penalise imbalanced routes — matches the notebook's coefficient
        distance_dimension.SetGlobalSpanCostCoefficient(100)
