/**
 * Application controller.
 * Owns global state and wires all UI events to the correct modules.
 */
import { initMap, clearMarkers, addMarker, clearRoutes, clearBestKnownRoutes, drawBestKnownRoute, fitBoundsToLocations, getRouteCount, getBestKnownCount } from "./map.js";
import { addLocationFromMapClick, renderLocationList, resetLocations, setLocationCounter, updateButtonStates } from "./forms/location-form.js";
import { rebuildForm } from "./forms/form-builder.js";
import { solve } from "./api.js";
import { renderRoutes } from "./results/solution-renderer.js";
import { renderTable } from "./results/solution-table.js";

// ── Global state ────────────────────────────────────────────────────
export const state = {
  problemType: "VRP",
  depotIndex: 0,
  locations: [],
  vehicles: [{ id: 0, capacity: 0, max_distance: 2_000_000, max_time: 57600 }, { id: 1, capacity: 0, max_distance: 2_000_000, max_time: 57600 }],
  pickupDeliveryPairs: [],
  optimizationObjective: "distance",
  distanceMatrix: null,
  durationMatrix: null,
  distanceMetric: null,
  solution: null,
  bestKnownRoutes: null,
  instanceExpected: null,
};

export function setStatus(msg, isError = false) {
  const el = document.getElementById("status-msg");
  el.textContent = msg;
  el.style.color = isError ? "var(--error)" : "var(--text-muted)";
}

// ── Toast notifications ─────────────────────────────────────────────
export function showToast(message, type = "info", duration = 5000) {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  // Trigger slide-in on next frame
  requestAnimationFrame(() => {
    requestAnimationFrame(() => toast.classList.add("visible"));
  });

  // Auto-dismiss
  setTimeout(() => {
    toast.classList.remove("visible");
    toast.addEventListener("transitionend", () => toast.remove(), { once: true });
    // Fallback removal if transitionend doesn't fire
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 500);
  }, duration);
}

// ── Instance loader ──────────────────────────────────────────────────

// ── Bootstrap ────────────────────────────────────────────────────────
async function init() {
  await initMap(addLocationFromMapClick);
  rebuildForm();

  // Problem type dropdown
  document.getElementById("problem-type-select").addEventListener("change", (e) => {
    state.problemType = e.target.value;
    state.distanceMatrix = null; // force recompute on type change
    clearRoutes();
    document.getElementById("results-panel").classList.remove("visible");
    rebuildForm();
    renderLocationList();
    updateButtonStates();
    setStatus("");
  });

  // Optimization objective radio buttons
  document.querySelectorAll('input[name="objective"]').forEach((radio) => {
    radio.addEventListener("change", (e) => {
      state.optimizationObjective = e.target.value;
    });
  });

  // Solve
  document.getElementById("btn-solve").addEventListener("click", async () => {
    if (state.locations.length < 2) return;
    showLoader("Computing distances & solving…");
    clearRoutes();
    clearMapGlow();
    document.getElementById("results-panel").classList.remove("visible");
    try {
      const payload = buildPayload();
      const response = await solve(payload);
      state.solution = response;
      clearBestKnownRoutes();

      if (response.status === "SUCCESS") {
        const usedStraightLines = await renderRoutes(response);
        if (usedStraightLines) {
          showToast("Road data unavailable for some routes — showing straight lines", "info", 5000);
        }

        // Draw best-known routes as dashed overlay
        if (state.bestKnownRoutes) {
          const locMap = Object.fromEntries(state.locations.map((l) => [l.id, l]));
          state.bestKnownRoutes.forEach((bkr, i) => {
            const stops = bkr.stop_ids.map((id) => locMap[id]).filter(Boolean);
            if (stops.length >= 2) drawBestKnownRoute(stops, i);
          });
        }

        // Fit map AFTER rendering routes (routes are now plain Polylines, no viewport override)
        await fitBoundsToLocations(state.locations);

        // Resolve best-known stop IDs to location objects for the table
        let bestKnownStops = null;
        if (state.bestKnownRoutes?.length) {
          const locMap = Object.fromEntries(state.locations.map((l) => [l.id, l]));
          bestKnownStops = state.bestKnownRoutes[0].stop_ids.map((id) => locMap[id]).filter(Boolean);
        }
        renderTable(response, state.problemType, state.instanceExpected, state.distanceMetric, bestKnownStops);
        flashMapGlow("success");
        showToast("Solution found!", "success");
      } else {
        renderTable(response, state.problemType, state.instanceExpected, state.distanceMetric);
        flashMapGlow("error");
        showToast("No solution found. Try relaxing constraints or adding more vehicles.", "error", 7000);
      }
    } catch (err) {
      flashMapGlow("error");
      showToast(`Error: ${err.message}`, "error", 7000);
    } finally {
      hideLoader();
    }
  });

  // Load instance
  document.getElementById("instance-select").addEventListener("change", (e) => {
    if (e.target.value) loadInstance(e.target.value);
  });

  // Reset
  document.getElementById("btn-reset").addEventListener("click", () => {
    clearMarkers();
    clearRoutes();
    clearBestKnownRoutes();
    resetLocations();
    state.pickupDeliveryPairs = [];
    state.solution = null;
    state.distanceMetric = null;
    state.bestKnownRoutes = null;
    state.instanceExpected = null;
    state.optimizationObjective = "distance";
    document.querySelector('input[name="objective"][value="distance"]').checked = true;
    document.getElementById("instance-select").selectedIndex = 0;
    document.getElementById("results-panel").classList.remove("visible");
    setStatus("");
    updateButtonStates();
  });

  // Expose test hooks for Playwright E2E tests
  window.__vrpState = state;
  window.__vrpGetRouteCount = getRouteCount;
  window.__vrpGetBestKnownCount = getBestKnownCount;
}

// ── Helpers ──────────────────────────────────────────────────────────
function buildPayload() {
  return {
    problem_type: state.problemType,
    depot_index: state.depotIndex,
    optimization_objective: state.optimizationObjective,
    locations: state.locations,
    vehicles: state.vehicles,
    pickup_delivery_pairs: state.pickupDeliveryPairs,
    distance_matrix: state.distanceMatrix ?? [],
    duration_matrix: state.durationMatrix ?? [],
  };
}

async function loadInstance(path) {
  try {
    const resp = await fetch(`sample_datasets/${path}.json`);
    if (!resp.ok) throw new Error(`Failed to load instance: ${resp.status}`);
    const data = await resp.json();

    // Clear current state
    clearMarkers();
    clearRoutes();
    clearBestKnownRoutes();
    resetLocations();
    document.getElementById("results-panel").classList.remove("visible");

    // Set problem type
    state.problemType = data.problem_type;
    document.getElementById("problem-type-select").value = data.problem_type;

    // Load locations
    data.locations.forEach((loc, i) => {
      state.locations.push({ ...loc });
      addMarker({ lat: loc.lat, lng: loc.lng, label: loc.label, isDepot: i === 0 });
    });
    setLocationCounter(data.locations.length);

    // Set vehicles
    state.vehicles = data.vehicles.map((v) => ({ ...v }));

    // Set pickup-delivery pairs
    state.pickupDeliveryPairs = (data.pickup_delivery_pairs || []).map((p) => ({ ...p }));

    // Set matrices (empty arrays trigger Google API auto-compute)
    const dm = data.distance_matrix || [];
    const tm = data.duration_matrix || [];
    state.distanceMatrix = dm.length > 0 ? dm : null;
    state.durationMatrix = tm.length > 0 ? tm : null;

    // Set optimization objective
    state.optimizationObjective = data.optimization_objective || "distance";
    const objRadio = document.querySelector(`input[name="objective"][value="${state.optimizationObjective}"]`);
    if (objRadio) objRadio.checked = true;

    // Store distance metric and best-known data for comparison after solve
    state.distanceMetric = data.distance_metric || null;
    state.bestKnownRoutes = data.best_known_routes?.length ? data.best_known_routes : null;
    state.instanceExpected = data.expected || null;

    // Rebuild UI
    rebuildForm();
    renderLocationList();
    updateButtonStates();
    await fitBoundsToLocations(state.locations);

    showToast(`Loaded: ${data.name}. Click Solve to run.`, "info");
  } catch (err) {
    showToast(`Error loading instance: ${err.message}`, "error", 7000);
  }
}

function showLoader(msg = "Working…") {
  const loader = document.getElementById("loader");
  const span = loader.querySelector("span");
  if (span) span.textContent = msg;
  loader.classList.add("visible");
}

function hideLoader() {
  document.getElementById("loader").classList.remove("visible");
}

function flashMapGlow(type) {
  const mc = document.getElementById("map-container");
  mc.classList.remove("glow-success", "glow-error");
  mc.classList.add(`glow-${type}`);
  // Auto-remove after 4 seconds
  setTimeout(() => mc.classList.remove(`glow-${type}`), 4000);
}

function clearMapGlow() {
  document.getElementById("map-container").classList.remove("glow-success", "glow-error");
}

// ── Start ─────────────────────────────────────────────────────────────
init();
