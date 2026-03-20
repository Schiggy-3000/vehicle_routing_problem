from app.models.request_models import SolveRequest, Vehicle
from app.solvers.base_solver import BaseSolver


class TspSolver(BaseSolver):
    """
    Traveling Salesman Problem: single vehicle, visit all locations, minimize distance.
    Forces exactly 1 vehicle regardless of what the request specifies.
    """

    def __init__(self, request: SolveRequest):
        # TSP always uses exactly 1 vehicle
        request.vehicles = [Vehicle(id=0, max_distance=10_000_000, max_time=360_000)]
        super().__init__(request)

    def _add_constraints(self) -> None:
        self._add_time_dimension()
