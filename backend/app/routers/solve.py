from fastapi import APIRouter, HTTPException

from app.models.request_models import SolveRequest
from app.models.response_models import SolveResponse
from app.services import distance_service, solver_service

router = APIRouter()


@router.post("/solve", response_model=SolveResponse)
def solve(request: SolveRequest) -> SolveResponse:
    try:
        # Auto-compute distance matrix from coordinates when not provided
        if not request.distance_matrix:
            origins = [f"{loc.lat},{loc.lng}" for loc in request.locations]
            dist, dur = distance_service.get_distance_and_duration_matrices(origins)
            request.distance_matrix = dist
            if not request.duration_matrix:
                request.duration_matrix = dur
        return solver_service.solve(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
