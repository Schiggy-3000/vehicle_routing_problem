from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.response_models import DistanceMatrixResponse
from app.services import distance_service

router = APIRouter()


class DistanceMatrixRequest(BaseModel):
    addresses: list[str]


@router.post("/distance-matrix", response_model=DistanceMatrixResponse)
def compute_distance_matrix(request: DistanceMatrixRequest) -> DistanceMatrixResponse:
    if len(request.addresses) < 2:
        raise HTTPException(status_code=400, detail="At least 2 addresses required.")
    try:
        dist, dur = distance_service.get_distance_and_duration_matrices(request.addresses)
        return DistanceMatrixResponse(matrix=dist, duration_matrix=dur)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
