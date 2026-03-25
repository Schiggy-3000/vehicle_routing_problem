"""
Check 7: Reset clears all state, UI, and instance selection.
"""


def test_reset_clears_all_state(loaded_page):
    """Load an instance, then reset — verify everything is cleared."""
    page = loaded_page

    # Load an instance first
    page.select_option("#instance-select", "TSPLIB/burma14")
    page.locator(".toast").wait_for(state="visible", timeout=10_000)

    # Verify it's loaded
    assert page.locator("#location-list .loc-item").count() == 14

    # Click reset
    page.locator("#btn-reset").click()

    # Instance dropdown reset to placeholder
    selected_index = page.evaluate("document.getElementById('instance-select').selectedIndex")
    assert selected_index == 0

    # No locations in sidebar
    assert page.locator("#location-list .loc-item").count() == 0

    # Results panel hidden
    assert not page.locator("#results-panel").evaluate("el => el.classList.contains('visible')")

    # Solve button disabled
    assert not page.locator("#btn-solve").is_enabled()

    # State cleared
    loc_count = page.evaluate("window.__vrpState.locations.length")
    assert loc_count == 0

    solution = page.evaluate("window.__vrpState.solution")
    assert solution is None

    metric = page.evaluate("window.__vrpState.distanceMetric")
    assert metric is None

    bkr = page.evaluate("window.__vrpState.bestKnownRoutes")
    assert bkr is None

    expected = page.evaluate("window.__vrpState.instanceExpected")
    assert expected is None
