/**
 * Google Maps wrapper.
 * Loads the Maps JS API dynamically so the API key stays in config.js.
 */
import { MAPS_JS_API_KEY } from "./config.js";

const VEHICLE_COLORS = ["#2563eb", "#c4653a", "#2e7d32", "#9333ea", "#d97706"];
const DEPOT_COLOR = "#1a1a18";

let map = null;
let markers = [];
let routeObjects = [];   // { obj: Polyline, vehicleIndex, color }
let directionsService = null;

// ── Init ────────────────────────────────────────────────────────────

export function initMap(onClickCallback) {
  return new Promise((resolve) => {
    if (window.google?.maps) {
      _createMap(onClickCallback);
      resolve();
      return;
    }

    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${MAPS_JS_API_KEY}`;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      _createMap(onClickCallback);
      resolve();
    };
    document.head.appendChild(script);
  });
}

function _createMap(onClickCallback) {
  map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: 47.25, lng: 8.10 }, // Central Switzerland
    zoom: 9,
    mapTypeControl: false,
    streetViewControl: false,
  });

  if (onClickCallback) {
    map.addListener("click", (e) => {
      onClickCallback({ lat: e.latLng.lat(), lng: e.latLng.lng() });
    });
  }
}

// ── Markers ─────────────────────────────────────────────────────────

export function addMarker({ lat, lng, label, isDepot = false }) {
  const color = isDepot ? DEPOT_COLOR : "#2563eb";
  const index = markers.length;

  const marker = new google.maps.Marker({
    position: { lat, lng },
    map,
    title: label,
    icon: _pinIcon(color),
    label: {
      text: isDepot ? "D" : String(index),
      color: "#fff",
      fontSize: "11px",
      fontWeight: "bold",
    },
  });

  // Cross-highlighting with sidebar
  marker.addListener("mouseover", () => {
    document.dispatchEvent(new CustomEvent("marker-hover", { detail: { index } }));
  });
  marker.addListener("mouseout", () => {
    document.dispatchEvent(new CustomEvent("marker-hover-end"));
  });

  markers.push(marker);
  return marker;
}

export function clearMarkers() {
  markers.forEach((m) => m.setMap(null));
  markers = [];
}

export function highlightMarker(index) {
  if (!markers[index]) return;
  markers[index].setIcon(_pinIcon(markers[index].getIcon().fillColor, 2.0));
  markers[index].setZIndex(999);
}

export function unhighlightMarker(index) {
  if (!markers[index]) return;
  const isDepot = index === 0;
  markers[index].setIcon(_pinIcon(isDepot ? DEPOT_COLOR : "#2563eb"));
  markers[index].setZIndex(undefined);
}

// ── Routes ──────────────────────────────────────────────────────────

export async function drawRoute(stops, vehicleIndex) {
  const color = VEHICLE_COLORS[vehicleIndex % VEHICLE_COLORS.length];

  if (stops.length < 2) return;

  // Try Directions API for road-following routes
  try {
    if (!directionsService) {
      directionsService = new google.maps.DirectionsService();
    }

    const origin = { lat: stops[0].lat, lng: stops[0].lng };
    const destination = { lat: stops[stops.length - 1].lat, lng: stops[stops.length - 1].lng };
    const waypoints = stops.slice(1, -1).map((s) => ({
      location: { lat: s.lat, lng: s.lng },
      stopover: true,
    }));

    // Directions API supports up to 25 waypoints; fall back to polylines if exceeded
    if (waypoints.length > 23) {
      _drawStraightLine(stops, color, vehicleIndex);
      return;
    }

    const result = await directionsService.route({
      origin,
      destination,
      waypoints,
      travelMode: google.maps.TravelMode.DRIVING,
    });

    // Extract road-following path and draw as a regular Polyline
    // (DirectionsRenderer unreliably updates styles and overrides fitBounds)
    const path = result.routes[0].overview_path;
    const polyline = new google.maps.Polyline({
      path,
      geodesic: true,
      strokeColor: color,
      strokeOpacity: 0.85,
      strokeWeight: 4,
      map,
    });

    const routeObj = { obj: polyline, vehicleIndex, color };
    _addRouteHoverListeners(polyline, vehicleIndex);
    routeObjects.push(routeObj);
  } catch {
    // Fallback to straight lines if Directions API fails
    _drawStraightLine(stops, color, vehicleIndex);
  }
}

function _drawStraightLine(stops, color, vehicleIndex) {
  const path = stops.map((s) => ({ lat: s.lat, lng: s.lng }));
  const polyline = new google.maps.Polyline({
    path,
    geodesic: true,
    strokeColor: color,
    strokeOpacity: 0.85,
    strokeWeight: 4,
    map,
  });

  const routeObj = { obj: polyline, vehicleIndex, color };
  _addRouteHoverListeners(polyline, vehicleIndex);
  routeObjects.push(routeObj);
}

function _addRouteHoverListeners(target, vehicleIndex) {
  target.addListener("mouseover", () => {
    highlightRoute(vehicleIndex);
    document.dispatchEvent(new CustomEvent("route-hover", { detail: { vehicleIndex } }));
  });
  target.addListener("mouseout", () => {
    unhighlightAllRoutes();
    document.dispatchEvent(new CustomEvent("route-hover-end"));
  });
}

export function highlightRoute(vehicleIndex) {
  routeObjects.forEach((ro) => {
    if (ro.vehicleIndex === vehicleIndex) {
      _setRouteStyle(ro, { strokeWeight: 7, strokeOpacity: 1.0 });
    } else {
      _setRouteStyle(ro, { strokeWeight: 3, strokeOpacity: 0.3 });
    }
  });
}

export function unhighlightAllRoutes() {
  routeObjects.forEach((ro) => {
    _setRouteStyle(ro, { strokeWeight: 4, strokeOpacity: 0.85 });
  });
}

function _setRouteStyle(routeObj, { strokeWeight, strokeOpacity }) {
  routeObj.obj.setOptions({ strokeWeight, strokeOpacity });
}

export function clearRoutes() {
  routeObjects.forEach((ro) => ro.obj.setMap(null));
  routeObjects = [];
  directionsService = null;
}

// ── Fit bounds ──────────────────────────────────────────────────────

export function fitBoundsToLocations(locations) {
  return new Promise((resolve) => {
    if (!map || !locations || locations.length === 0) { resolve(); return; }
    const bounds = new google.maps.LatLngBounds();
    locations.forEach((loc) => bounds.extend({ lat: loc.lat, lng: loc.lng }));
    map.fitBounds(bounds, 60);
    // Wait for map to finish animating before resolving
    let resolved = false;
    const done = () => { if (!resolved) { resolved = true; resolve(); } };
    google.maps.event.addListenerOnce(map, "idle", done);
    setTimeout(done, 2000); // safety fallback
  });
}

// ── Helpers ─────────────────────────────────────────────────────────

function _pinIcon(fillColor, scale = 1.5) {
  // Solid teardrop pin — no hole, label sits in the filled circle area
  return {
    path: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z",
    fillColor,
    fillOpacity: 1,
    strokeColor: "#fff",
    strokeWeight: 1.5,
    scale,
    anchor: new google.maps.Point(12, 22),
    labelOrigin: new google.maps.Point(12, 9),
  };
}

export function getVehicleColor(vehicleIndex) {
  return VEHICLE_COLORS[vehicleIndex % VEHICLE_COLORS.length];
}
