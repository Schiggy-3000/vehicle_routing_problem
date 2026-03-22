/**
 * Application controller.
 * Owns global state and wires all UI events to the correct modules.
 */
import { initMap, clearMarkers, addMarker, clearRoutes, fitBoundsToLocations } from "./map.js";
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
  solution: null,
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

// ── Swiss demo fixture ───────────────────────────────────────────────
const SWISS_DEMO = {
  locations: [
    { id: "loc_0", label: "Galliker LC 3 (Depot)",  address: "Galliker LC 3, Industriepark, 6252 Dagmersellen", lat: 47.2080684, lng: 7.9770576, demand: 0, time_window: [0, 86400] },
    { id: "loc_1", label: "Ottos Sport Outlet",     address: "Infanteriestrasse 12, 6210 Sursee",               lat: 47.1807265, lng: 8.1049023, demand: 5, time_window: [0, 86400] },
    { id: "loc_2", label: "Adidas Outlet Cham",     address: "Brunnmatt 14, 6330 Cham",                         lat: 47.192036,  lng: 8.448365,  demand: 5, time_window: [0, 86400] },
    { id: "loc_3", label: "Coop Aarau",             address: "Tellistrasse 67, 5004 Aarau",                     lat: 47.3984877, lng: 8.0586177, demand: 5, time_window: [0, 86400] },
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
    document.getElementById("results-panel").classList.remove("visible");
    try {
      const payload = buildPayload();
      const response = await solve(payload);
      state.solution = response;

      if (response.status === "SUCCESS") {
        await renderRoutes(response);
        // Fit map AFTER rendering routes (routes are now plain Polylines, no viewport override)
        await fitBoundsToLocations(state.locations);
        renderTable(response, state.problemType);
        showToast("Solution found!", "success");
      } else {
        renderTable(response, state.problemType);
        showToast("No solution found. Try relaxing constraints or adding more vehicles.", "error", 7000);
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error", 7000);
    } finally {
      hideLoader();
    }
  });

  // Load demo
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
    state.optimizationObjective = "distance";
    document.querySelector('input[name="objective"][value="distance"]').checked = true;
    document.getElementById("results-panel").classList.remove("visible");
    setStatus("");
    updateButtonStates();
  });
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

function loadDemo() {
  clearMarkers();
  clearRoutes();
  resetLocations();

  SWISS_DEMO.locations.forEach((loc, i) => {
    state.locations.push({ ...loc });
    addMarker({ lat: loc.lat, lng: loc.lng, label: loc.label, isDepot: i === 0 });
  });

  // Advance the location counter past demo IDs so new pins don't collide
  setLocationCounter(SWISS_DEMO.locations.length);

  state.distanceMatrix = null;
  state.durationMatrix = null;

  renderLocationList();
  showToast("Demo data loaded. Click Solve to run.", "info");
  updateButtonStates();
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

// ── Start ─────────────────────────────────────────────────────────────
init();
