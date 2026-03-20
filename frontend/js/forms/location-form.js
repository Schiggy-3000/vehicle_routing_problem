/**
 * Manages the location list in the sidebar.
 * Adds locations from map clicks and renders per-location fields
 * (demand for CVRP, time windows for VRPTW).
 */
import { state, setStatus } from "../main.js";
import { addMarker, highlightMarker, unhighlightMarker } from "../map.js";

let _locationCounter = 0;
let _crossHighlightInitialized = false;

export function setLocationCounter(value) {
  _locationCounter = value;
}

export function addLocationFromMapClick({ lat, lng }) {
  const isDepot = state.locations.length === 0;
  const id = `loc_${_locationCounter++}`;
  const label = isDepot ? "Depot" : `Location ${_locationCounter}`;

  const location = {
    id,
    label,
    address: `${lat.toFixed(5)}, ${lng.toFixed(5)}`,
    lat,
    lng,
    demand: 0,
    time_window: [0, 86400],
  };

  state.locations.push(location);
  state.distanceMatrix = null;
  state.durationMatrix = null;
  addMarker({ lat, lng, label, isDepot });
  renderLocationList();
  updateButtonStates();
}

export function renderLocationList() {
  const ul = document.getElementById("location-list");
  const hint = document.getElementById("hint-click-map");

  // Set up cross-highlighting from map markers (once)
  if (!_crossHighlightInitialized) {
    _crossHighlightInitialized = true;
    document.addEventListener("marker-hover", (e) => {
      document.querySelectorAll(".loc-item").forEach((item) => item.classList.remove("loc-hover"));
      const target = document.querySelector(`.loc-item[data-index="${e.detail.index}"]`);
      if (target) target.classList.add("loc-hover");
    });
    document.addEventListener("marker-hover-end", () => {
      document.querySelectorAll(".loc-item").forEach((item) => item.classList.remove("loc-hover"));
    });
  }

  if (state.locations.length === 0) {
    ul.innerHTML = "";
    hint.style.display = "";
    return;
  }

  hint.style.display = "none";
  const showDemands     = state.problemType === "CVRP";
  const showTimeWindows = state.problemType === "VRPTW";

  ul.innerHTML = state.locations.map((loc, i) => {
    const isDepot = i === state.depotIndex;
    const badge = `<span class="loc-badge ${isDepot ? "depot" : ""}">${isDepot ? "Depot" : "Stop"}</span>`;
    const indexCircle = `<span class="loc-index ${isDepot ? "depot" : ""}">${isDepot ? "D" : i}</span>`;

    let extras = "";
    if (showDemands && !isDepot) {
      extras = `
        <div class="loc-extra">
          <label>Demand <input type="number" class="loc-demand" data-id="${loc.id}" min="0" value="${loc.demand}" style="width:60px;" /></label>
        </div>`;
    }
    if (showTimeWindows) {
      const openH  = String(Math.floor(loc.time_window[0] / 3600)).padStart(2, "0");
      const openM  = String(Math.floor((loc.time_window[0] % 3600) / 60)).padStart(2, "0");
      const closeH = String(Math.floor(loc.time_window[1] / 3600)).padStart(2, "0");
      const closeM = String(Math.floor((loc.time_window[1] % 3600) / 60)).padStart(2, "0");
      extras = `
        <div class="loc-extra">
          <label>Open  <input type="time" class="loc-tw-open"  data-id="${loc.id}" value="${openH}:${openM}" /></label>
          <label>Close <input type="time" class="loc-tw-close" data-id="${loc.id}" value="${closeH}:${closeM}" /></label>
        </div>`;
    }

    return `
      <li class="loc-item" data-index="${i}">
        ${indexCircle}
        <span class="loc-label">${loc.label}</span>
        ${badge}
        ${!isDepot ? `<button class="btn-remove" data-id="${loc.id}" title="Remove">&times;</button>` : ""}
      </li>
      ${extras}`;
  }).join("");

  // Remove-location handlers
  ul.querySelectorAll(".btn-remove").forEach((btn) => {
    btn.addEventListener("click", () => removeLocation(btn.dataset.id));
  });

  // Sidebar → map hover cross-highlighting
  ul.querySelectorAll(".loc-item").forEach((li) => {
    const index = parseInt(li.dataset.index);
    li.addEventListener("mouseenter", () => highlightMarker(index));
    li.addEventListener("mouseleave", () => unhighlightMarker(index));
  });

  // Demand input handlers
  ul.querySelectorAll(".loc-demand").forEach((input) => {
    input.addEventListener("change", () => {
      const loc = state.locations.find((l) => l.id === input.dataset.id);
      if (loc) loc.demand = parseInt(input.value) || 0;
      state.distanceMatrix = null; // invalidate cached matrix
    });
  });

  // Time window handlers
  ul.querySelectorAll(".loc-tw-open, .loc-tw-close").forEach((input) => {
    input.addEventListener("change", () => {
      const loc = state.locations.find((l) => l.id === input.dataset.id);
      if (!loc) return;
      const [h, m] = input.value.split(":").map(Number);
      const seconds = h * 3600 + m * 60;
      if (input.classList.contains("loc-tw-open"))  loc.time_window[0] = seconds;
      if (input.classList.contains("loc-tw-close")) loc.time_window[1] = seconds;
    });
  });
}

function removeLocation(id) {
  const idx = state.locations.findIndex((l) => l.id === id);
  if (idx === -1) return;
  state.locations.splice(idx, 1);
  state.distanceMatrix = null;
  state.durationMatrix = null;
  // Rebuild markers from scratch
  import("../map.js").then(({ clearMarkers, addMarker }) => {
    clearMarkers();
    state.locations.forEach((loc, i) => {
      addMarker({ lat: loc.lat, lng: loc.lng, label: loc.label, isDepot: i === state.depotIndex });
    });
  });
  renderLocationList();
  updateButtonStates();
  setStatus("");
}

export function updateButtonStates() {
  document.getElementById("btn-solve").disabled = state.locations.length < 2;
}

export function resetLocations() {
  _locationCounter = 0;
  state.locations = [];
  state.distanceMatrix = null;
  state.durationMatrix = null;
  renderLocationList();
  updateButtonStates();
}
