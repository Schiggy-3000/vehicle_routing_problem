"""
Check 6: Swiss Demo auto-computes distances via Google API and solves successfully.
Marked as slow because it depends on the Google Distance Matrix API.
"""
import pytest


@pytest.mark.slow
def test_swiss_demo_auto_computes_and_solves(loaded_page):
    """Load Swiss Demo (empty matrices), solve, verify success."""
    page = loaded_page

    page.select_option("#instance-select", "demo/swiss_demo")
    page.locator(".toast").wait_for(state="visible", timeout=10_000)

    # Matrices should be null (empty in JSON → triggers Google API auto-compute)
    dm = page.evaluate("window.__vrpState.distanceMatrix")
    assert dm is None

    dur = page.evaluate("window.__vrpState.durationMatrix")
    assert dur is None

    # 4 locations loaded
    assert page.locator("#location-list .loc-item").count() == 4

    # Solve (longer timeout — Google Distance Matrix API + solve)
    page.locator("#btn-solve").click()
    page.wait_for_function(
        "() => !document.getElementById('loader').classList.contains('visible')",
        timeout=60_000,
    )

    status = page.evaluate("window.__vrpState.solution.status")
    assert status == "SUCCESS"

    # Results panel visible with route rows
    assert page.locator("#results-panel").evaluate("el => el.classList.contains('visible')")
    assert page.locator("#results-content .route-row").count() >= 1
