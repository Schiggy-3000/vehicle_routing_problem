import { getVehicleColor } from "../map.js";

/**
 * Renders the route breakdown table in the results panel.
 */
export function renderTable(solutionResponse, problemType) {
  const panel   = document.getElementById("results-panel");
  const content = document.getElementById("results-content");

  if (solutionResponse.status === "NO_SOLUTION") {
    content.innerHTML = `<p style="color:#c62828;">No solution found. Try relaxing constraints or adding more vehicles.</p>`;
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
    }).join(" → ");

    const distStr = `${(route.total_distance_m / 1000).toFixed(1)} km`;
    const timeStr = route.total_duration_s != null ? ` · ${Math.round(route.total_duration_s / 60)} min` : "";
    const loadStr = showLoad && route.total_load != null ? ` · Load: ${route.total_load}` : "";

    return `
      <div class="route-row">
        <strong style="color:${color}">Vehicle ${route.vehicle_id}</strong>
        &nbsp;<small>${distStr}${timeStr}${loadStr}</small><br/>
        <span class="route-stops">${stopsStr}</span>
      </div>`;
  }).join("");

  const dropped = solutionResponse.dropped_visits.length
    ? `<div style="margin-top:8px;">
         <strong>Dropped visits:</strong>
         ${solutionResponse.dropped_visits.map((id) => `<span class="badge-dropped">${id}</span>`).join("")}
       </div>`
    : "";

  const obj = solutionResponse.objective_value != null
    ? `<div style="margin-top:8px;font-size:0.75rem;color:#888;">Objective value: ${solutionResponse.objective_value.toLocaleString()} · Solved in ${solutionResponse.solver_wall_time_ms} ms</div>`
    : "";

  content.innerHTML = routeRows + dropped + obj;
  panel.classList.add("visible");
}

function _fmtTime(seconds) {
  const h = String(Math.floor(seconds / 3600)).padStart(2, "0");
  const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
  return `${h}:${m}`;
}
