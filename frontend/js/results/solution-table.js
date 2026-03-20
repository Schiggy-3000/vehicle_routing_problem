import { getVehicleColor, highlightRoute, unhighlightAllRoutes } from "../map.js";

/**
 * Renders the route breakdown table in the results panel.
 */
export function renderTable(solutionResponse, problemType) {
  const panel   = document.getElementById("results-panel");
  const content = document.getElementById("results-content");

  if (solutionResponse.status === "NO_SOLUTION") {
    content.innerHTML = `<div class="no-solution-card">No solution found. Try relaxing constraints or adding more vehicles.</div>`;
    panel.classList.add("visible");
    return;
  }

  const showTime = problemType === "VRPTW";
  const showLoad = problemType === "CVRP";

  const routeRows = solutionResponse.routes.map((route, i) => {
    const color = getVehicleColor(i);
    const stopsStr = route.stops.map((s) => {
      let extra = "";
      if (showTime && s.arrival_time != null) {
        extra = ` <small>(${_fmtTime(s.arrival_time)})</small>`;
      }
      return `${s.label}${extra}`;
    }).join(" &rarr; ");

    const distStr = `${(route.total_distance_m / 1000).toFixed(1)} km`;
    const timeStr = route.total_duration_s != null ? ` · ${Math.round(route.total_duration_s / 60)} min` : "";
    const loadStr = showLoad && route.total_load != null ? ` · Load: ${route.total_load}` : "";

    return `
      <div class="route-row" data-vehicle="${i}" style="border-left-color: ${color};">
        <div class="route-header">
          <strong style="color:${color}">Vehicle ${route.vehicle_id}</strong>
          <small class="route-meta">${distStr}${timeStr}${loadStr}</small>
        </div>
        <span class="route-stops">${stopsStr}</span>
      </div>`;
  }).join("");

  const dropped = solutionResponse.dropped_visits.length
    ? `<div style="margin-top:10px;">
         <strong style="font-size:0.85rem;">Dropped visits:</strong>
         ${solutionResponse.dropped_visits.map((id) => `<span class="badge-dropped">${id}</span>`).join("")}
       </div>`
    : "";

  const obj = solutionResponse.objective_value != null
    ? `<div class="results-footer">Objective: ${solutionResponse.objective_value.toLocaleString()} · Solved in ${solutionResponse.solver_wall_time_ms} ms</div>`
    : "";

  content.innerHTML = routeRows + dropped + obj;
  panel.classList.add("visible");

  // Cross-highlighting: hover route card → highlight map route
  content.querySelectorAll(".route-row").forEach((row) => {
    const vehicleIdx = parseInt(row.dataset.vehicle);
    row.addEventListener("mouseenter", () => {
      highlightRoute(vehicleIdx);
      row.classList.add("route-hover");
    });
    row.addEventListener("mouseleave", () => {
      unhighlightAllRoutes();
      row.classList.remove("route-hover");
    });
  });

  // Listen for map route hover → highlight corresponding card
  _setupMapRouteHoverListener();
}

let _mapRouteListenerInitialized = false;

function _setupMapRouteHoverListener() {
  if (_mapRouteListenerInitialized) return;
  _mapRouteListenerInitialized = true;

  document.addEventListener("route-hover", (e) => {
    document.querySelectorAll(".route-row").forEach((row) => {
      const isTarget = parseInt(row.dataset.vehicle) === e.detail.vehicleIndex;
      row.classList.toggle("route-hover", isTarget);
    });
  });
  document.addEventListener("route-hover-end", () => {
    document.querySelectorAll(".route-row").forEach((row) => row.classList.remove("route-hover"));
  });
}

function _fmtTime(seconds) {
  const h = String(Math.floor(seconds / 3600)).padStart(2, "0");
  const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
  return `${h}:${m}`;
}
