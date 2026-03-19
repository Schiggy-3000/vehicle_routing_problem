from typing import List, Literal, Tuple
from pydantic import BaseModel, Field


class Location(BaseModel):
    id: str
    label: str
    address: str = ""
    lat: float
    lng: float
    demand: int = 0                                    # CVRP: units required at this stop
    time_window: Tuple[int, int] = (0, 86400)          # VRPTW: [open, close] in seconds from midnight


class PickupDeliveryPair(BaseModel):
    pickup_id: str
    delivery_id: str


class Vehicle(BaseModel):
    id: int
    capacity: int = 0           # CVRP: vehicle capacity (0 = unlimited)
    max_distance: int = 100000  # meters


class SolveRequest(BaseModel):
    problem_type: Literal["TSP", "VRP", "CVRP", "PDP", "VRPTW"]
    depot_index: int = 0
    locations: List[Location] = Field(min_length=2)
    vehicles: List[Vehicle] = Field(min_length=1)
    pickup_delivery_pairs: List[PickupDeliveryPair] = []
    distance_matrix: List[List[int]]    # pre-computed, always required
    duration_matrix: List[List[int]] = []  # VRPTW: travel times in seconds
