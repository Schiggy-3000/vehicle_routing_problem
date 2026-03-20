from app.solvers.base_solver import BaseSolver


class VrpSolver(BaseSolver):
    """
    Vehicle Routing Problem: multiple vehicles, minimize total distance.
    Adds a Distance dimension with a global span cost coefficient — identical
    to the pattern used in 02_solver.ipynb.
    """

    def _add_constraints(self) -> None:
        self._add_distance_dimension()
        self._add_time_dimension()
