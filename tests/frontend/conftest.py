"""
Fixtures for frontend E2E tests using Playwright.
Starts a local HTTP server and provides a loaded page with Google Maps ready.
"""
import subprocess
import sys
import time
from pathlib import Path

import pytest
import urllib.request
import urllib.error

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PORT = 5500
BASE_URL = f"http://127.0.0.1:{PORT}"
PAGE_URL = f"{BASE_URL}/frontend/index.html"


@pytest.fixture(scope="session")
def local_server():
    """Start a local HTTP server serving the repo root on port 5500."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for the server to be ready
    for _ in range(30):
        try:
            urllib.request.urlopen(PAGE_URL, timeout=1)
            break
        except (urllib.error.URLError, ConnectionRefusedError):
            time.sleep(0.2)
    else:
        proc.terminate()
        pytest.fail("Local HTTP server did not start in time")

    yield BASE_URL

    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture()
def loaded_page(local_server, page):
    """Navigate to the app and wait for Google Maps API + app state to be ready."""
    page.goto(PAGE_URL, wait_until="networkidle")

    # Wait for Google Maps JS API to load
    page.wait_for_function("() => !!window.google?.maps", timeout=20_000)

    # Wait for app state to be exposed
    page.wait_for_function("() => !!window.__vrpState", timeout=5_000)

    return page
