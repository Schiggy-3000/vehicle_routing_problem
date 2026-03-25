import { getVehicleColor, highlightRoute, unhighlightAllRoutes } from "../map.js";

/**
 * Renders the route breakdown table in the results panel.
 */
export function renderTable(solutionResponse, problemType, instanceExpected = null, distanceMetric = null) {
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

  let footerParts = [];
  if (solutionResponse.objective_value != null) {
    footerParts.push(`Objective: ${solutionResponse.objective_value.toLocaleString()}`);
  }
  if (solutionResponse.solver_wall_time_ms != null) {
    footerParts.push(`Solved in ${solutionResponse.solver_wall_time_ms} ms`);
  }

  // Best-known comparison
  let bestKnownNote = "";
  if (instanceExpected?.best_known_objective != null && solutionResponse.status === "SUCCESS") {
    const totalDist = solutionResponse.routes.reduce((sum, r) => sum + r.total_distance_m, 0);
    const bk = instanceExpected.best_known_objective;
    const bkMetric = instanceExpected.best_known_metric || null;
    const solverMetric = distanceMetric || null;
    const crossMetric = bkMetric && solverMetric && bkMetric !== solverMetric;

    const bkLabel = bkMetric ? ` (${bkMetric})` : "";
    const solverLabel = solverMetric ? ` (${solverMetric})` : "";

    if (crossMetric) {
      bestKnownNote = `<div class="best-known-note">Best known${bkLabel}: ${bk.toLocaleString()} · Solver${solverLabel}: ${totalDist.toLocaleString()}<br><small>Different distance metrics — ratio not directly comparable</small></div>`;
    } else {
      const ratio = (totalDist / bk).toFixed(2);
      bestKnownNote = `<div class="best-known-note">Best known${bkLabel}: ${bk.toLocaleString()} · Solver${solverLabel}: ${totalDist.toLocaleString()} (${ratio}x)</div>`;
    }
  }

  const obj = footerParts.length
    ? `<div class="results-footer">${footerParts.join(" · ")}</div>`
    : "";

  const legend = bestKnownNote
    ? `<div class="route-legend">
        <span class="route-legend-item"><span class="legend-line solid"></span> Solver</span>
        <span class="route-legend-item"><span class="legend-line dashed"></span> Best known</span>
      </div>`
    : "";

  content.innerHTML = routeRows + dropped + obj + bestKnownNote + legend;
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
