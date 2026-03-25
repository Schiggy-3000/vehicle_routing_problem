"""
Checks 3 & 5: Solve flow — routes rendered, objective comparison.
Uses TSPLIB/burma14 (empty matrices — Google API computes road distances at solve time).
"""


def _load_and_solve(page, instance="TSPLIB/burma14", timeout=60_000):
    """Helper: load an instance and solve it."""
    page.select_option("#instance-select", instance)
    page.locator(".toast").wait_for(state="visible", timeout=10_000)

    page.locator("#btn-solve").click()

    # Wait for loader to disappear (solve complete)
    # Longer timeout: backend computes distance matrix via Google API
    page.wait_for_function(
        "() => !document.getElementById('loader').classList.contains('visible')",
        timeout=timeout,
    )


def test_solve_shows_routes(loaded_page):
    """Check 3: Solving produces routes — results panel visible, route rows exist."""
    page = loaded_page
    _load_and_solve(page)

    # Solution stored in state
    status = page.evaluate("window.__vrpState.solution.status")
    assert status == "SUCCESS"

    route_count = page.evaluate("window.__vrpState.solution.routes.length")
    assert route_count == 1  # TSP = single vehicle

    # Results panel is visible
    assert page.locator("#results-panel").evaluate("el => el.classList.contains('visible')")

    # At least one route row rendered
    assert page.locator("#results-content .route-row").count() >= 1

    # Polyline was created on the map
    map_routes = page.evaluate("window.__vrpGetRouteCount()")
    assert map_routes == 1


def test_results_show_comparison(loaded_page):
    """Check 5: Results panel shows best-known comparison with metric labels."""
    page = loaded_page
    _load_and_solve(page)

    # Best-known note exists
    note = page.locator("#results-content .best-known-note")
    assert note.count() >= 1

    note_text = note.inner_text()

    # burma14 best-known is 3,323,000 m (geodesic)
    assert "3,323" in note_text or "3323" in note_text

    # Cross-metric labels shown (geodesic best-known vs road solver)
    assert "geodesic" in note_text
    assert "road" in note_text

    # No ratio for cross-metric comparison
    assert "not directly comparable" in note_text
