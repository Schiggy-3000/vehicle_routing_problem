import { getVehicleColor, highlightRoute, unhighlightAllRoutes, highlightBestKnown, unhighlightBestKnown } from "../map.js";

/**
 * Renders the route breakdown table in the results panel.
 */
export function renderTable(solutionResponse, problemType, instanceExpected = null, distanceMetric = null, bestKnownStops = null) {
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
  const bkComputed = bestKnownStops?.length >= 2 ? computeGeoTourDistance(bestKnownStops) : null;
  const bk = bkComputed ?? instanceExpected?.best_known_objective ?? null;
  const bkMetric = bkComputed ? "geodesic" : (instanceExpected?.best_known_metric || null);

  let bestKnownNote = "";
  if (bk != null && solutionResponse.status === "SUCCESS") {
    const totalDist = solutionResponse.routes.reduce((sum, r) => sum + r.total_distance_m, 0);
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

  // Best-known route row (mirrors solver route rows)
  let bestKnownRow = "";
  if (bestKnownStops && bestKnownStops.length >= 2) {
    const bkStopsStr = bestKnownStops.map((s) => s.label).join(" &rarr; ");
    const bkDistStr = bk != null ? `${(bk / 1000).toFixed(1)} km` : "—";
    const bkMetricLabel = bkMetric ? ` <small>(${bkMetric})</small>` : "";

    bestKnownRow = `
      <div class="route-row best-known-row" style="border-left-color: #888;">
        <div class="route-header">
          <strong style="color:#888">Best known</strong>
          <small class="route-meta">${bkDistStr}${bkMetricLabel}</small>
        </div>
        <span class="route-stops">${bkStopsStr}</span>
      </div>`;
  }

  const legend = bestKnownNote
    ? `<div class="route-legend">
        <span class="route-legend-item"><span class="legend-line solid"></span> Solver</span>
        <span class="route-legend-item"><span class="legend-line dashed"></span> Best known</span>
      </div>`
    : "";

  content.innerHTML = routeRows + bestKnownRow + dropped + obj + bestKnownNote + legend;
  panel.classList.add("visible");

  // Cross-highlighting: hover route card → highlight map route
  content.querySelectorAll(".route-row:not(.best-known-row)").forEach((row) => {
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

  // Cross-highlighting: hover best-known card → highlight best-known on map
  const bkRow = content.querySelector(".best-known-row");
  if (bkRow) {
    bkRow.addEventListener("mouseenter", () => {
      highlightBestKnown();
      bkRow.classList.add("route-hover");
    });
    bkRow.addEventListener("mouseleave", () => {
      unhighlightBestKnown();
      bkRow.classList.remove("route-hover");
    });
  }

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
  document.addEventListener("best-known-hover", () => {
    const bk = document.querySelector(".best-known-row");
    if (bk) bk.classList.add("route-hover");
  });
  document.addEventListener("best-known-hover-end", () => {
    const bk = document.querySelector(".best-known-row");
    if (bk) bk.classList.remove("route-hover");
  });
}

function _fmtTime(seconds) {
  const h = String(Math.floor(seconds / 3600)).padStart(2, "0");
  const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
  return `${h}:${m}`;
}

// ── TSPLIB GEO distance (exact formula from TSPLIB95 spec) ──────────

function _tsplibGeoEdge(a, b) {
  const PI = 3.141592;
  const RRR = 6378.388;
  const latA = PI * a.lat / 180.0;
  const lngA = PI * a.lng / 180.0;
  const latB = PI * b.lat / 180.0;
  const lngB = PI * b.lng / 180.0;
  const q1 = Math.cos(lngA - lngB);
  const q2 = Math.cos(latA - latB);
  const q3 = Math.cos(latA + latB);
  return Math.floor(RRR * Math.acos(0.5 * ((1 + q1) * q2 - (1 - q1) * q3)) + 1.0);
}

export function computeGeoTourDistance(stops) {
  let total = 0;
  for (let i = 0; i < stops.length - 1; i++) {
    total += _tsplibGeoEdge(stops[i], stops[i + 1]);
  }
  return total * 1000; // km → meters
}
