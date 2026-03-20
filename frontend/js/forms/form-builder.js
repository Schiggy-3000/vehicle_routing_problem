/**
 * Renders the problem-type-specific sidebar sections.
 * Called whenever the user changes the problem type dropdown.
 */
import { state } from "../main.js";
import { renderLocationList } from "./location-form.js";

const PROBLEM_CONFIG = {
  TSP:   { showVehicles: false, showDemands: false, showTimeWindows: false, showPdPairs: false },
  VRP:   { showVehicles: true,  showDemands: false, showTimeWindows: false, showPdPairs: false },
  CVRP:  { showVehicles: true,  showDemands: true,  showTimeWindows: false, showPdPairs: false },
  PDP:   { showVehicles: true,  showDemands: false, showTimeWindows: false, showPdPairs: true  },
  VRPTW: { showVehicles: true,  showDemands: false, showTimeWindows: true,  showPdPairs: false },
};

export function rebuildForm() {
  const cfg = PROBLEM_CONFIG[state.problemType];

  // Vehicles section
  const vehicleSection = document.getElementById("vehicle-section");
  vehicleSection.style.display = cfg.showVehicles ? "" : "none";
  if (cfg.showVehicles) renderVehicleFields();

  // Constraint section (demands / time windows / PD pairs)
  const constraintSection = document.getElementById("constraint-section");
  const constraintTitle   = document.getElementById("constraint-title");
  const constraintContent = document.getElementById("constraint-content");

  if (cfg.showDemands) {
    constraintSection.style.display = "";
    constraintTitle.textContent = "Demands (per location)";
    constraintContent.innerHTML = "<p style='font-size:0.8rem;color:#888;'>Set demand for each location in the Locations list above.</p>";
  } else if (cfg.showTimeWindows) {
    constraintSection.style.display = "";
    constraintTitle.textContent = "Time Windows";
    constraintContent.innerHTML = "<p style='font-size:0.8rem;color:#888;'>Set open/close times for each location in the Locations list above.</p>";
  } else if (cfg.showPdPairs) {
    constraintSection.style.display = "";
    constraintTitle.textContent = "Pickup & Delivery Pairs";
    constraintContent.innerHTML = renderPdPairsHTML();
    attachPdPairHandlers();
  } else {
    constraintSection.style.display = "none";
  }

  // Re-render location list to show/hide per-location fields
  renderLocationList();
}

function renderVehicleFields() {
  const cfg = PROBLEM_CONFIG[state.problemType];
  const container = document.getElementById("vehicle-fields");
  container.innerHTML = `
    <div class="field-row">
      <label>Number of vehicles</label>
      <input type="number" id="input-vehicle-count" min="1" max="10" value="${state.vehicles.length || 2}" />
    </div>
    ${cfg.showDemands ? `
    <div class="field-row">
      <label>Vehicle capacity</label>
      <input type="number" id="input-vehicle-capacity" min="1" value="${state.vehicles[0]?.capacity || 10}" />
    </div>` : ""}
    <div class="field-row">
      <label>Max distance (km)</label>
      <input type="number" id="input-max-distance" min="1" value="${Math.round((state.vehicles[0]?.max_distance || 2000000) / 1000)}" step="1" />
    </div>
    <div class="field-row">
      <label>Max driving time (h)</label>
      <input type="number" id="input-max-time" min="1" value="${Math.round((state.vehicles[0]?.max_time || 57600) / 3600)}" step="1" />
    </div>
  `;

  container.querySelectorAll("input").forEach((el) => {
    el.addEventListener("change", syncVehiclesFromFields);
  });
  syncVehiclesFromFields();
}

function syncVehiclesFromFields() {
  const count    = parseInt(document.getElementById("input-vehicle-count")?.value || "2");
  const capacity = parseInt(document.getElementById("input-vehicle-capacity")?.value || "0");
  const maxDistKm = parseInt(document.getElementById("input-max-distance")?.value || "2000");
  const maxDist   = maxDistKm * 1000;
  const maxTimeH  = parseInt(document.getElementById("input-max-time")?.value || "16");
  const maxTime   = maxTimeH * 3600;

  state.vehicles = Array.from({ length: count }, (_, i) => ({
    id: i,
    capacity,
    max_distance: maxDist,
    max_time: maxTime,
  }));
}

function renderPdPairsHTML() {
  const locs = state.locations.filter((_, i) => i !== state.depotIndex);
  const options = locs.map((l) => `<option value="${l.id}">${l.label}</option>`).join("");
  const pairs = state.pickupDeliveryPairs
    .map((p, i) => `<li>${p.pickup_id} → ${p.delivery_id}
      <button class="btn-remove" data-idx="${i}" title="Remove">×</button></li>`)
    .join("");

  return `
    <ul id="pd-pairs-list">${pairs || "<li style='color:#aaa;font-size:0.8rem;'>No pairs yet.</li>"}</ul>
    <div class="pd-add-row">
      <select id="pd-pickup-sel">${options}</select>
      <select id="pd-delivery-sel">${options}</select>
      <button class="btn btn-outline" id="btn-add-pair" style="padding:4px 8px;font-size:0.8rem;">Add</button>
    </div>`;
}

function attachPdPairHandlers() {
  document.getElementById("btn-add-pair")?.addEventListener("click", () => {
    const pickup   = document.getElementById("pd-pickup-sel")?.value;
    const delivery = document.getElementById("pd-delivery-sel")?.value;
    if (!pickup || !delivery || pickup === delivery) return;
    state.pickupDeliveryPairs.push({ pickup_id: pickup, delivery_id: delivery });
    document.getElementById("constraint-content").innerHTML = renderPdPairsHTML();
    attachPdPairHandlers();
  });

  document.querySelectorAll("#pd-pairs-list .btn-remove").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.pickupDeliveryPairs.splice(parseInt(btn.dataset.idx), 1);
      document.getElementById("constraint-content").innerHTML = renderPdPairsHTML();
      attachPdPairHandlers();
    });
  });
}
