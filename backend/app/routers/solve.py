from fastapi import APIRouter, HTTPException

from app.models.request_models import SolveRequest
from app.models.response_models import SolveResponse
from app.services import solver_service

router = APIRouter()


@router.post("/solve", response_model=SolveResponse)
def solve(request: SolveRequest) -> SolveResponse:
    try:
        return solver_service.solve(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
