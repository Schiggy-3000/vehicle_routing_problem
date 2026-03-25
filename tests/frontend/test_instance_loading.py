"""
Checks 1 & 2: Instance dropdown structure and instance loading.
"""


def test_dropdown_lists_all_instances(loaded_page):
    """Check 1: The instance dropdown has all instances in 2 groups."""
    page = loaded_page

    optgroups = page.locator("#instance-select optgroup")
    assert optgroups.count() == 2

    labels = [optgroups.nth(i).get_attribute("label") for i in range(2)]
    assert labels == ["Demo", "TSPLIB"]

    options = page.locator("#instance-select option:not([disabled])")
    assert options.count() == 5

    # Verify specific values exist
    values = [options.nth(i).get_attribute("value") for i in range(options.count())]
    assert "demo/swiss_demo" in values
    assert "TSPLIB/burma14" in values
    assert "TSPLIB/ulysses16" in values
    assert "TSPLIB/ulysses22" in values
    assert "TSPLIB/gr96" in values


def test_load_burma14_populates_state(loaded_page):
    """Check 2: Selecting burma14 populates locations, vehicles, matrices, problem type."""
    page = loaded_page

    page.select_option("#instance-select", "TSPLIB/burma14")

    # Wait for toast confirming load
    page.locator(".toast").wait_for(state="visible", timeout=10_000)

    # Problem type set to TSP
    assert page.locator("#problem-type-select").input_value() == "TSP"

    # 14 locations in sidebar
    assert page.locator("#location-list .loc-item").count() == 14

    # State populated correctly
    matrix_len = page.evaluate("window.__vrpState.distanceMatrix.length")
    assert matrix_len == 14

    bkr_len = page.evaluate("window.__vrpState.bestKnownRoutes.length")
    assert bkr_len == 0  # TSPLIB instances have no best-known routes

    # Solve button is enabled
    assert page.locator("#btn-solve").is_enabled()
