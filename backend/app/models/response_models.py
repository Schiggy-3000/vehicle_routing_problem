from typing import Literal
from pydantic import BaseModel


class RouteStop(BaseModel):
    location_id: str
    label: str
    lat: float
    lng: float
    arrival_time: int | None = None        # seconds from midnight (VRPTW)
    cumulative_distance: int | None = None  # meters from route start


class VehicleRoute(BaseModel):
    vehicle_id: int
    stops: list[RouteStop]   # includes depot at start and end
    total_distance_m: int
    total_load: int | None = None  # CVRP


class SolveResponse(BaseModel):
    status: Literal["SUCCESS", "NO_SOLUTION", "ERROR"]
    problem_type: str
    objective_value: int | None = None
    routes: list[VehicleRoute] = []
    dropped_visits: list[str] = []     # location ids not served
    solver_wall_time_ms: int = 0
    error_message: str | None = None


class DistanceMatrixResponse(BaseModel):
    matrix: list[list[int]]           # driving distances in meters
    duration_matrix: list[list[int]]  # driving durations in seconds
