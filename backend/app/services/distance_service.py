"""
Distance matrix calculation using Google Distance Matrix API.
Ported directly from 01_create_distance_matrix.ipynb.

The API limits requests to 10 origins × 10 destinations per call, so we tile
larger inputs into chunks and stitch the results together.
"""

import json
import urllib.parse
import urllib.request
from math import ceil

from app.config import settings

_API_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
_CHUNK_SIZE = 10  # Google Distance Matrix API limit per request


def get_distance_and_duration_matrices(
    addresses: list[str],
) -> tuple[list[list[int]], list[list[int]]]:
    """
    Returns (distance_matrix_meters, duration_matrix_seconds) for the given addresses.
    Raises RuntimeError if the Google API returns an error status.
    """
    n = len(addresses)
    distance_matrix = [[0] * n for _ in range(n)]
    duration_matrix = [[0] * n for _ in range(n)]

    # Tile requests to stay within the 10×10 API limit
    for row_start in range(0, n, _CHUNK_SIZE):
        row_end = min(row_start + _CHUNK_SIZE, n)
        origins = addresses[row_start:row_end]

        for col_start in range(0, n, _CHUNK_SIZE):
            col_end = min(col_start + _CHUNK_SIZE, n)
            destinations = addresses[col_start:col_end]

            response = _send_request(origins, destinations)
            _fill_matrices(
                response,
                distance_matrix,
                duration_matrix,
                row_start,
                col_start,
            )

    return distance_matrix, duration_matrix


def _send_request(
    origins: list[str],
    destinations: list[str],
) -> dict:
    """Makes a single request to the Google Distance Matrix API."""
    params = {
        "origins": "|".join(origins),
        "destinations": "|".join(destinations),
        "mode": "driving",
        "units": "metric",
        "language": "en",
        "key": settings.google_maps_api_key,
    }
    url = f"{_API_URL}?{urllib.parse.urlencode(params)}"

    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.loads(response.read().decode())

    if data["status"] != "OK":
        raise RuntimeError(
            f"Google Distance Matrix API error: {data.get('status')} — "
            f"{data.get('error_message', 'no details')}"
        )

    return data


def _fill_matrices(
    response: dict,
    distance_matrix: list[list[int]],
    duration_matrix: list[list[int]],
    row_offset: int,
    col_offset: int,
) -> None:
    """Writes API response values into the appropriate cells of each matrix."""
    for i, row in enumerate(response["rows"]):
        for j, element in enumerate(row["elements"]):
            if element["status"] != "OK":
                raise RuntimeError(
                    f"No route found for pair ({row_offset + i}, {col_offset + j}): "
                    f"{element['status']}"
                )
            distance_matrix[row_offset + i][col_offset + j] = element["distance"]["value"]
            duration_matrix[row_offset + i][col_offset + j] = element["duration"]["value"]
