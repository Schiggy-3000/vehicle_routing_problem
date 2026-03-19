from typing import List, Literal, Optional
from pydantic import BaseModel


class RouteStop(BaseModel):
    location_id: str
    label: str
    lat: float
    lng: float
    arrival_time: Optional[int] = None        # seconds from midnight (VRPTW)
    cumulative_distance: Optional[int] = None  # meters from route start


class VehicleRoute(BaseModel):
    vehicle_id: int
    stops: List[RouteStop]   # includes depot at start and end
    total_distance_m: int
    total_load: Optional[int] = None  # CVRP


class SolveResponse(BaseModel):
    status: Literal["SUCCESS", "NO_SOLUTION", "ERROR"]
    problem_type: str
    objective_value: Optional[int] = None
    routes: List[VehicleRoute] = []
    dropped_visits: List[str] = []     # location ids not served
    solver_wall_time_ms: int = 0
    error_message: Optional[str] = None


class DistanceMatrixResponse(BaseModel):
    matrix: List[List[int]]           # driving distances in meters
    duration_matrix: List[List[int]]  # driving durations in seconds
