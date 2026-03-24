"""
Checks 1 & 2: Instance dropdown structure and instance loading.
"""


def test_dropdown_lists_all_instances(loaded_page):
    """Check 1: The instance dropdown has all 10 instances in 3 groups."""
    page = loaded_page

    optgroups = page.locator("#instance-select optgroup")
    assert optgroups.count() == 3

    labels = [optgroups.nth(i).get_attribute("label") for i in range(3)]
    assert labels == ["Demo", "Benchmarks", "Hand-Crafted"]

    options = page.locator("#instance-select option:not([disabled])")
    assert options.count() == 10

    # Verify specific values exist
    values = [options.nth(i).get_attribute("value") for i in range(options.count())]
    assert "demo/swiss_demo" in values
    assert "benchmarks/burma14" in values
    assert "benchmarks/A-n32-k5" in values
    assert "benchmarks/C101_25" in values
    assert "benchmarks/lc101_small" in values
    assert "handcrafted/tsp_triangle" in values
    assert "handcrafted/cvrp_forced_split" in values
    assert "handcrafted/vrptw_forced_order" in values
    assert "handcrafted/pdp_precedence" in values
    assert "handcrafted/vrp_max_dist_split" in values


def test_load_tsp_triangle_populates_state(loaded_page):
    """Check 2: Selecting TSP triangle populates locations, vehicles, matrices, problem type."""
    page = loaded_page

    page.select_option("#instance-select", "handcrafted/tsp_triangle")

    # Wait for toast confirming load
    page.locator(".toast").wait_for(state="visible", timeout=10_000)

    # Problem type set to TSP
    assert page.locator("#problem-type-select").input_value() == "TSP"

    # 3 locations in sidebar
    assert page.locator("#location-list .loc-item").count() == 3

    # State populated correctly
    matrix_len = page.evaluate("window.__vrpState.distanceMatrix.length")
    assert matrix_len == 3

    bkr_len = page.evaluate("window.__vrpState.bestKnownRoutes.length")
    assert bkr_len == 1

    # Solve button is enabled
    assert page.locator("#btn-solve").is_enabled()


def test_load_cvrp_shows_vehicle_section(loaded_page):
    """Check 2 (variant): Loading a CVRP instance shows vehicle/constraint sections."""
    page = loaded_page

    page.select_option("#instance-select", "handcrafted/cvrp_forced_split")
    page.locator(".toast").wait_for(state="visible", timeout=10_000)

    assert page.locator("#problem-type-select").input_value() == "CVRP"
    assert page.locator("#location-list .loc-item").count() == 4
    assert page.locator("#vehicle-section").is_visible()
