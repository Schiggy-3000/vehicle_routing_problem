"""
Fixtures for frontend E2E tests using Playwright.
Starts a local HTTP server and provides a loaded page with Google Maps ready.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
import urllib.request
import urllib.error

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
PORT = 5500
BASE_URL = f"http://127.0.0.1:{PORT}"
PAGE_URL = f"{BASE_URL}/index.html"


@pytest.fixture(scope="session")
def local_server():
    """Copy sample_datasets into frontend/ and start a local HTTP server."""
    # Mirror CI: copy sample_datasets into frontend/ so relative fetch paths work
    datasets_src = PROJECT_ROOT / "sample_datasets"
    datasets_dst = FRONTEND_DIR / "sample_datasets"
    if datasets_dst.exists():
        shutil.rmtree(datasets_dst)
    shutil.copytree(datasets_src, datasets_dst)

    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd=str(FRONTEND_DIR),
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
        shutil.rmtree(datasets_dst, ignore_errors=True)
        pytest.fail("Local HTTP server did not start in time")

    yield BASE_URL

    proc.terminate()
    proc.wait(timeout=5)
    shutil.rmtree(datasets_dst, ignore_errors=True)


@pytest.fixture()
def loaded_page(local_server, page):
    """Navigate to the app and wait for Google Maps API + app state to be ready."""
    page.goto(PAGE_URL, wait_until="networkidle")

    # Wait for Google Maps JS API to load
    page.wait_for_function("() => !!window.google?.maps", timeout=20_000)

    # Wait for app state to be exposed
    page.wait_for_function("() => !!window.__vrpState", timeout=5_000)

    return page
