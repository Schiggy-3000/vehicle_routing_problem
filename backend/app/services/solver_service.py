from app.models.request_models import SolveRequest
from app.models.response_models import SolveResponse
from app.solvers.cvrp_solver import CvrpSolver
from app.solvers.pdp_solver import PdpSolver
from app.solvers.tsp_solver import TspSolver
from app.solvers.vrp_solver import VrpSolver
from app.solvers.vrptw_solver import VrptwSolver

_SOLVER_MAP = {
    "TSP": TspSolver,
    "VRP": VrpSolver,
    "CVRP": CvrpSolver,
    "PDP": PdpSolver,
    "VRPTW": VrptwSolver,
}


def solve(request: SolveRequest) -> SolveResponse:
    solver_class = _SOLVER_MAP[request.problem_type]
    return solver_class(request).solve()
