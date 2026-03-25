"""
One-time conversion scripts for TSPLIB GEO benchmark instances → shared JSON format.
Run: python -m tests.backend.benchmarks.parsers
"""
import json
import os
import urllib.request
from pathlib import Path


def _download(url: str) -> str:
    """Download a URL and return its text content."""
    print(f"  Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "VRP-Benchmark-Downloader"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


# ── TSPLIB parser ────────────────────────────────────────────────────

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


# ── Generic TSPLIB GEO converter ──────────────────────────────────────

TSPLIB_REPO = "https://raw.githubusercontent.com/mastqe/tsplib/refs/heads/master"
TSPLIB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "sample_datasets" / "TSPLIB"

# Best-known objectives (geodesic, in meters = original TSPLIB values × 1000)
TSPLIB_INSTANCES = {
    "burma14": 3323000,
    "ulysses16": 6859000,
}


def convert_tsplib_instance(name, best_known):
    """Download and convert a TSPLIB GEO instance to JSON.
    Distance matrix is left empty — backend computes road distances via Google API at solve time.
    """
    url = f"{TSPLIB_REPO}/{name}.tsp"
    text = _download(url)
    _, dim, raw_nodes = parse_tsplib(text)

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
        "description": f"{dim} cities — best known (geodesic) = {best_known} m",
        "problem_type": "TSP",
        "category": "TSPLIB",
        "distance_metric": "road",
        "locations": locations,
        "vehicles": [{"id": 0, "capacity": 0, "max_distance": 100000000, "max_time": 100000000}],
        "pickup_delivery_pairs": [],
        "optimization_objective": "distance",
        "distance_matrix": [],
        "duration_matrix": [],
        "expected": {
            "status": "SUCCESS",
            "objective_value": None,
            "num_routes": 1,
            "best_known_objective": best_known,
            "best_known_metric": "geodesic",
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


if __name__ == "__main__":
    print("Converting TSPLIB instances...")
    convert_all_tsplib()
    print("Done!")
