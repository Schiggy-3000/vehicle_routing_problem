/**
 * Application controller.
 * Owns global state and wires all UI events to the correct modules.
 */
import { initMap, clearMarkers, addMarker, clearRoutes } from "./map.js";
import { addLocationFromMapClick, renderLocationList, resetLocations } from "./forms/location-form.js";
import { rebuildForm } from "./forms/form-builder.js";
import { solve } from "./api.js";
import { renderRoutes } from "./results/solution-renderer.js";
import { renderTable } from "./results/solution-table.js";

// ── Global state ────────────────────────────────────────────────────
export const state = {
  problemType: "VRP",
  depotIndex: 0,
  locations: [],
  vehicles: [{ id: 0, capacity: 0, max_distance: 100_000 }, { id: 1, capacity: 0, max_distance: 100_000 }],
  pickupDeliveryPairs: [],
  distanceMatrix: null,
  durationMatrix: null,
  solution: null,
};

export function setStatus(msg, isError = false) {
  const el = document.getElementById("status-msg");
  el.textContent = msg;
  el.style.color = isError ? "#c62828" : "#555";
}

// ── Memphis demo fixture ─────────────────────────────────────────────
const MEMPHIS_DEMO = {
  locations: [
    { id: "loc_0", label: "Hacks Cross Rd (Depot)", address: "3610 Hacks Cross Rd, Memphis, TN", lat: 35.0496, lng: -89.8581, demand: 0, time_window: [0, 86400] },
    { id: "loc_1", label: "Elvis Presley Blvd",     address: "1921 Elvis Presley Blvd, Memphis, TN", lat: 35.0465, lng: -90.0271, demand: 5, time_window: [0, 86400] },
    { id: "loc_2", label: "Union Avenue",           address: "149 Union Avenue, Memphis, TN", lat: 35.1495, lng: -90.0490, demand: 5, time_window: [0, 86400] },
    { id: "loc_3", label: "Audubon Drive",          address: "1034 Audubon Drive, Memphis, TN", lat: 35.1168, lng: -89.9549, demand: 5, time_window: [0, 86400] },
  ],
  distanceMatrix: [
    [0, 25288, 33362, 14933],
    [26314, 0, 8795, 11802],
    [34057, 8968, 0, 14082],
    [15511, 12071, 13930, 0],
  ],
  durationMatrix: [
    [0, 1823, 2403, 1076],
    [1896, 0, 634, 851],
    [2452, 646, 0, 1015],
    [1118, 870, 1004, 0],
  ],
};

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
    updateButtons();
    setStatus("");
  });

  // Solve
  document.getElementById("btn-solve").addEventListener("click", async () => {
    if (state.locations.length < 2) return;
    showLoader("Computing distances & solving…");
    clearRoutes();
    document.getElementById("results-panel").classList.remove("visible");
    try {
      const payload = buildPayload();
      const response = await solve(payload);
      state.solution = response;
      renderRoutes(response);
      renderTable(response, state.problemType);
      setStatus(response.status === "SUCCESS" ? "Solution found." : "No solution found.");
    } catch (err) {
      setStatus(`Error: ${err.message}`, true);
    } finally {
      hideLoader();
    }
  });

  // Load Memphis demo
  document.getElementById("btn-demo").addEventListener("click", () => {
    loadDemo();
  });

  // Reset
  document.getElementById("btn-reset").addEventListener("click", () => {
    clearMarkers();
    clearRoutes();
    resetLocations();
    state.pickupDeliveryPairs = [];
    state.solution = null;
    document.getElementById("results-panel").classList.remove("visible");
    setStatus("");
    updateButtons();
  });
}

// ── Helpers ──────────────────────────────────────────────────────────
function buildPayload() {
  return {
    problem_type: state.problemType,
    depot_index: state.depotIndex,
    locations: state.locations,
    vehicles: state.vehicles,
    pickup_delivery_pairs: state.pickupDeliveryPairs,
    distance_matrix: state.distanceMatrix ?? [],
    duration_matrix: state.durationMatrix ?? [],
  };
}

function loadDemo() {
  clearMarkers();
  clearRoutes();
  resetLocations();

  MEMPHIS_DEMO.locations.forEach((loc, i) => {
    state.locations.push({ ...loc });
    addMarker({ lat: loc.lat, lng: loc.lng, label: loc.label, isDepot: i === 0 });
  });

  state.distanceMatrix = MEMPHIS_DEMO.distanceMatrix;
  state.durationMatrix = MEMPHIS_DEMO.durationMatrix;

  renderLocationList();
  setStatus("Memphis demo loaded. Click Solve to run.");
  updateButtons();
}

function updateButtons() {
  document.getElementById("btn-solve").disabled = state.locations.length < 2;
}

function showLoader(msg = "Working…") {
  const loader = document.getElementById("loader");
  loader.textContent = msg;
  loader.classList.add("visible");
}

function hideLoader() {
  document.getElementById("loader").classList.remove("visible");
}

// ── Start ─────────────────────────────────────────────────────────────
init();
