from typing import Literal
from pydantic import BaseModel, Field


class Location(BaseModel):
    id: str
    label: str
    address: str = ""
    lat: float
    lng: float
    demand: int = 0                         # CVRP: units required at this stop
    time_window: tuple[int, int] = (0, 86400)  # VRPTW: [open, close] in seconds from midnight


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
    locations: list[Location] = Field(min_length=2)
    vehicles: list[Vehicle] = Field(min_length=1)
    pickup_delivery_pairs: list[PickupDeliveryPair] = []
    distance_matrix: list[list[int]]    # pre-computed, always required
    duration_matrix: list[list[int]] = []  # VRPTW: travel times in seconds
