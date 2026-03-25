"""
One-time conversion scripts for benchmark instances → shared JSON format.
Run: python -m tests.benchmarks.parsers
"""
import json
import math
import os
import urllib.request
from pathlib import Path

INSTANCES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "sample_datasets" / "benchmarks"

# Geographic center for coordinate mapping (Switzerland)
CENTER_LAT, CENTER_LNG = 47.25, 8.00
SPREAD = 0.3  # degrees spread for mapping


def _scale_coords(nodes, center_lat=CENTER_LAT, center_lng=CENTER_LNG, spread=SPREAD):
    """Scale abstract (x,y) coordinates to (lat,lng) within a geographic box."""
    if not nodes:
        return []
    xs = [n[0] for n in nodes]
    ys = [n[1] for n in nodes]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_range = x_max - x_min or 1
    y_range = y_max - y_min or 1

    result = []
    for x, y in nodes:
        lat = center_lat - spread / 2 + spread * (y - y_min) / y_range
        lng = center_lng - spread / 2 + spread * (x - x_min) / x_range
        result.append((round(lat, 6), round(lng, 6)))
    return result


def _euclidean_matrix(nodes):
    """Compute Euclidean distance matrix, rounded to nearest integer."""
    n = len(nodes)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            dx = nodes[i][0] - nodes[j][0]
            dy = nodes[i][1] - nodes[j][1]
            matrix[i][j] = round(math.sqrt(dx * dx + dy * dy))
    return matrix


def _download(url: str) -> str:
    """Download a URL and return its text content."""
    print(f"  Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "VRP-Benchmark-Downloader"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


# ── TSPLIB parser (burma14) ──────────────────────────────────────────

def parse_tsplib(text: str):
    """Parse a TSPLIB file. Returns (name, dimension, nodes[(x,y)])."""
    lines = text.strip().split("\n")
    name = ""
    dimension = 0
    nodes = []
    in_coords = False

    for line in lines:
        line = line.strip()
        if line.startswith("NAME"):
            name = line.split(":")[-1].strip()
        elif line.startswith("DIMENSION"):
            dimension = int(line.split(":")[-1].strip())
        elif line == "NODE_COORD_SECTION":
            in_coords = True
        elif line == "EOF":
            break
        elif in_coords:
            parts = line.split()
            if len(parts) >= 3:
                nodes.append((float(parts[1]), float(parts[2])))
    return name, dimension, nodes


def _geo_to_decimal(val):
    """Convert TSPLIB degree.minute format to decimal degrees.
    E.g., 38.24 means 38 degrees 24 minutes = 38.4 decimal degrees."""
    deg = int(val)
    minutes = val - deg
    return round(deg + 5.0 * minutes / 3.0, 6)


def _geo_distance(lat1, lon1, lat2, lon2):
    """TSPLIB GEO distance computation."""
    PI = 3.141592
    rlat1 = PI * _geo_to_decimal(lat1) / 180.0
    rlon1 = PI * _geo_to_decimal(lon1) / 180.0
    rlat2 = PI * _geo_to_decimal(lat2) / 180.0
    rlon2 = PI * _geo_to_decimal(lon2) / 180.0
    RRR = 6378.388
    q1 = math.cos(rlon1 - rlon2)
    q2 = math.cos(rlat1 - rlat2)
    q3 = math.cos(rlat1 + rlat2)
    return int(RRR * math.acos(0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)) + 1.0)


def _geo_matrix(nodes):
    """Compute TSPLIB GEO distance matrix."""
    n = len(nodes)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = _geo_distance(nodes[i][0], nodes[i][1], nodes[j][0], nodes[j][1])
    return matrix


# ── Generic TSPLIB GEO converter ──────────────────────────────────────

TSPLIB_REPO = "https://raw.githubusercontent.com/mastqe/tsplib/refs/heads/master"
TSPLIB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "sample_datasets" / "TSPLIB"

TSPLIB_INSTANCES = {
    "burma14": 3323,
    "ulysses16": 6859,
    "ulysses22": 7013,
    "gr96": 55209,
}


def convert_tsplib_instance(name, best_known):
    """Download and convert a TSPLIB GEO instance to JSON."""
    url = f"{TSPLIB_REPO}/{name}.tsp"
    text = _download(url)
    _, dim, raw_nodes = parse_tsplib(text)

    dist_matrix = _geo_matrix(raw_nodes)
    # Convert TSPLIB degree.minute format to decimal degrees for map display
    coords = [(_geo_to_decimal(x), _geo_to_decimal(y)) for x, y in raw_nodes]

    locations = []
    for i, (lat, lng) in enumerate(coords):
        locations.append({
            "id": f"loc_{i}", "label": f"City {i}" if i > 0 else "Depot",
            "lat": lat, "lng": lng, "demand": 0, "time_window": [0, 86400]
        })

    data = {
        "name": f"{name} (TSPLIB)",
        "description": f"{dim} cities — best known = {best_known}",
        "problem_type": "TSP",
        "category": "TSPLIB",
        "locations": locations,
        "vehicles": [{"id": 0, "capacity": 0, "max_distance": 1000000, "max_time": 360000}],
        "pickup_delivery_pairs": [],
        "optimization_objective": "distance",
        "distance_matrix": dist_matrix,
        "duration_matrix": dist_matrix,
        "expected": {
            "status": "SUCCESS",
            "objective_value": None,
            "num_routes": 1,
            "best_known_objective": best_known,
            "quality_threshold": 5.0
        },
        "best_known_routes": []
    }

    out = TSPLIB_DIR / f"{name}.json"
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Written: {out}")


def convert_all_tsplib():
    """Convert all TSPLIB GEO instances."""
    os.makedirs(TSPLIB_DIR, exist_ok=True)
    for name, best_known in TSPLIB_INSTANCES.items():
        convert_tsplib_instance(name, best_known)


# ── Augerat CVRP parser (A-n32-k5) ──────────────────────────────────

def parse_augerat(text: str):
    """Parse Augerat/TSPLIB CVRP file."""
    lines = text.strip().split("\n")
    name = ""
    dimension = 0
    capacity = 0
    nodes = []
    demands = []
    depot = 0
    section = None

    for line in lines:
        line = line.strip()
        if line.startswith("NAME"):
            name = line.split(":")[-1].strip()
        elif line.startswith("DIMENSION"):
            dimension = int(line.split(":")[-1].strip())
        elif line.startswith("CAPACITY"):
            capacity = int(line.split(":")[-1].strip())
        elif "NODE_COORD_SECTION" in line:
            section = "coords"
        elif "DEMAND_SECTION" in line:
            section = "demand"
        elif "DEPOT_SECTION" in line:
            section = "depot"
        elif line == "EOF":
            break
        elif section == "coords":
            parts = line.split()
            if len(parts) >= 3:
                nodes.append((float(parts[1]), float(parts[2])))
        elif section == "demand":
            parts = line.split()
            if len(parts) >= 2:
                demands.append(int(parts[1]))
        elif section == "depot":
            val = int(line.strip())
            if val >= 0:
                depot = val - 1  # TSPLIB is 1-indexed

    return name, dimension, capacity, nodes, demands, depot


def convert_A_n32_k5():
    """Download and convert A-n32-k5.vrp to JSON."""
    url = "https://raw.githubusercontent.com/mkalinowski/CVRP/master/dane/A-n32-k5.vrp"
    text = _download(url)
    name, dim, capacity, raw_nodes, demands, depot = parse_augerat(text)

    dist_matrix = _euclidean_matrix(raw_nodes)
    coords = _scale_coords(raw_nodes)

    # Reorder: depot first
    if depot != 0:
        # Swap depot to index 0
        raw_nodes[0], raw_nodes[depot] = raw_nodes[depot], raw_nodes[0]
        demands[0], demands[depot] = demands[depot], demands[0]
        coords[0], coords[depot] = coords[depot], coords[0]
        dist_matrix = _euclidean_matrix(raw_nodes)

    num_vehicles = 5  # from instance name "k5"
    locations = []
    for i, (lat, lng) in enumerate(coords):
        locations.append({
            "id": f"loc_{i}",
            "label": f"Depot" if i == 0 else f"Customer {i}",
            "lat": lat, "lng": lng,
            "demand": demands[i] if i < len(demands) else 0,
            "time_window": [0, 86400]
        })

    data = {
        "name": "A-n32-k5 (Augerat)",
        "description": "32 nodes, 5 vehicles, capacity 100 — optimal = 784",
        "problem_type": "CVRP",
        "category": "benchmark",
        "locations": locations,
        "vehicles": [{"id": i, "capacity": capacity, "max_distance": 10000000, "max_time": 360000}
                     for i in range(num_vehicles)],
        "pickup_delivery_pairs": [],
        "optimization_objective": "distance",
        "distance_matrix": dist_matrix,
        "duration_matrix": dist_matrix,
        "expected": {
            "status": "SUCCESS",
            "objective_value": None,
            "num_routes": None,
            "best_known_objective": 784,
            "quality_threshold": 5.0
        },
        "best_known_routes": []
    }

    out = INSTANCES_DIR / "A-n32-k5.json"
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Written: {out}")


# ── Solomon VRPTW parser (C101, 25 customers) ───────────────────────

def convert_C101_25():
    """Convert Solomon C101 (25-customer subset) to JSON.
    Data from: https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/
    Vehicle count: 25, Capacity: 200
    """
    # Solomon C101 first 25 customers + depot (well-known, embedded directly)
    # Format: id, x, y, demand, ready_time, due_time, service_time
    solomon_data = [
        (0,  40, 50,  0,    0, 1236, 0),
        (1,  45, 68, 10,  912,  967, 90),
        (2,  42, 66, 10,  825,  870, 90),
        (3,  42, 68, 20,   65,  146, 90),
        (4,  40, 69, 20,  727,  782, 90),
        (5,  40, 66, 10,   15,   67, 90),
        (6,  38, 68, 20,  621,  702, 90),
        (7,  38, 70, 30,  170,  225, 90),
        (8,  35, 66, 20,  255,  324, 90),
        (9,  35, 69, 10,  534,  605, 90),
        (10, 25, 85, 20,  357,  410, 90),
        (11, 22, 75, 30,  448,  505, 90),
        (12, 22, 85, 10,  652,  721, 90),
        (13, 20, 80, 40,   30,   92, 90),
        (14, 20, 85, 20,  567,  620, 90),
        (15, 18, 75, 20,  384,  429, 90),
        (16, 15, 75, 20,  475,  528, 90),
        (17, 15, 80, 10,   99,  148, 90),
        (18, 30, 50, 10,  179,  254, 90),
        (19, 30, 52, 20,  278,  345, 90),
        (20, 28, 52, 20,   10,   73, 90),
        (21, 28, 55, 10,  914,  965, 90),
        (22, 25, 50, 10,  812,  883, 90),
        (23, 25, 52, 40,  732,  777, 90),
        (24, 25, 55, 10,   65,  144, 90),
        (25, 23, 52, 10,  169,  224, 90),
    ]

    capacity = 200
    raw_nodes = [(d[1], d[2]) for d in solomon_data]
    dist_matrix = _euclidean_matrix(raw_nodes)
    coords = _scale_coords(raw_nodes)

    locations = []
    for i, d in enumerate(solomon_data):
        lat, lng = coords[i]
        locations.append({
            "id": f"loc_{i}",
            "label": "Depot" if i == 0 else f"Customer {d[0]}",
            "lat": lat, "lng": lng,
            "demand": d[3],
            "time_window": [d[4], d[5]]
        })

    num_vehicles = 10  # C101 best known uses 10 vehicles
    data = {
        "name": "C101-25 (Solomon)",
        "description": "25 customers, clustered, tight time windows — best known: 191.3 (10 vehicles)",
        "problem_type": "VRPTW",
        "category": "benchmark",
        "locations": locations,
        "vehicles": [{"id": i, "capacity": capacity, "max_distance": 10000000, "max_time": 360000}
                     for i in range(num_vehicles)],
        "pickup_delivery_pairs": [],
        "optimization_objective": "distance",
        "distance_matrix": dist_matrix,
        "duration_matrix": dist_matrix,
        "expected": {
            "status": "SUCCESS",
            "objective_value": None,
            "num_routes": None,
            "best_known_objective": 191,
            "quality_threshold": 5.0
        },
        "best_known_routes": []
    }

    out = INSTANCES_DIR / "C101_25.json"
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Written: {out}")


# ── Li & Lim PDP parser (small hand-crafted subset) ─────────────────

def convert_lc101_small():
    """Create a small PDP instance based on Li & Lim lc101 format.
    Since Li & Lim instances are large (100+ tasks), we create a small
    representative subset with 4 pickup-delivery pairs (9 nodes total).
    """
    # Hand-crafted small PDP instance in Li & Lim style
    # 8 task nodes + 1 depot = 9 nodes
    raw_nodes = [
        (40, 50),   # 0: depot
        (25, 65),   # 1: pickup 1
        (55, 65),   # 2: delivery 1
        (25, 35),   # 3: pickup 2
        (55, 35),   # 4: delivery 2
        (15, 50),   # 5: pickup 3
        (65, 50),   # 6: delivery 3
        (35, 75),   # 7: pickup 4
        (45, 25),   # 8: delivery 4
    ]

    dist_matrix = _euclidean_matrix(raw_nodes)
    coords = _scale_coords(raw_nodes)

    locations = []
    labels = ["Depot", "Pickup 1", "Delivery 1", "Pickup 2", "Delivery 2",
              "Pickup 3", "Delivery 3", "Pickup 4", "Delivery 4"]
    for i, (lat, lng) in enumerate(coords):
        locations.append({
            "id": f"loc_{i}", "label": labels[i],
            "lat": lat, "lng": lng, "demand": 0, "time_window": [0, 86400]
        })

    pairs = [
        {"pickup_id": "loc_1", "delivery_id": "loc_2"},
        {"pickup_id": "loc_3", "delivery_id": "loc_4"},
        {"pickup_id": "loc_5", "delivery_id": "loc_6"},
        {"pickup_id": "loc_7", "delivery_id": "loc_8"},
    ]

    data = {
        "name": "PDP Small (Li & Lim style)",
        "description": "4 pickup-delivery pairs, 9 nodes — verifies precedence and same-vehicle constraints",
        "problem_type": "PDP",
        "category": "benchmark",
        "locations": locations,
        "vehicles": [{"id": i, "capacity": 0, "max_distance": 10000000, "max_time": 360000}
                     for i in range(3)],
        "pickup_delivery_pairs": pairs,
        "optimization_objective": "distance",
        "distance_matrix": dist_matrix,
        "duration_matrix": dist_matrix,
        "expected": {
            "status": "SUCCESS",
            "objective_value": None,
            "num_routes": None,
            "best_known_objective": None,
            "quality_threshold": None
        },
        "best_known_routes": []
    }

    out = INSTANCES_DIR / "lc101_small.json"
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Written: {out}")


if __name__ == "__main__":
    os.makedirs(INSTANCES_DIR, exist_ok=True)
    print("Converting benchmark instances...")
    convert_A_n32_k5()
    convert_C101_25()
    convert_lc101_small()
    print("Converting TSPLIB instances...")
    convert_all_tsplib()
    print("Done!")
