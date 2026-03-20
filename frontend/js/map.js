/**
 * Google Maps wrapper.
 * Loads the Maps JS API dynamically so the API key stays in config.js.
 */
import { MAPS_JS_API_KEY } from "./config.js";

const VEHICLE_COLORS = ["#1a73e8", "#e53935", "#43a047", "#fb8c00", "#8e24aa"];
const DEPOT_COLOR = "#212121";

let map = null;
let markers = [];
let polylines = [];       // stores Polylines or DirectionsRenderers
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
  const color = isDepot ? DEPOT_COLOR : "#1a73e8";

  const marker = new google.maps.Marker({
    position: { lat, lng },
    map,
    title: label,
    icon: _pinIcon(color),
    label: {
      text: isDepot ? "D" : String(markers.length),
      color: "#fff",
      fontSize: "11px",
      fontWeight: "bold",
    },
  });

  markers.push(marker);
  return marker;
}

export function clearMarkers() {
  markers.forEach((m) => m.setMap(null));
  markers = [];
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
      _drawStraightLine(stops, color);
      return;
    }

    const result = await directionsService.route({
      origin,
      destination,
      waypoints,
      travelMode: google.maps.TravelMode.DRIVING,
    });

    const renderer = new google.maps.DirectionsRenderer({
      map,
      directions: result,
      suppressMarkers: true,
      polylineOptions: {
        strokeColor: color,
        strokeWeight: 4,
        strokeOpacity: 0.85,
      },
    });

    polylines.push(renderer);
  } catch {
    // Fallback to straight lines if Directions API fails
    _drawStraightLine(stops, color);
  }
}

function _drawStraightLine(stops, color) {
  const path = stops.map((s) => ({ lat: s.lat, lng: s.lng }));
  const polyline = new google.maps.Polyline({
    path,
    geodesic: true,
    strokeColor: color,
    strokeOpacity: 0.85,
    strokeWeight: 4,
    map,
  });
  polylines.push(polyline);
}

export function clearRoutes() {
  polylines.forEach((p) => p.setMap(null));
  polylines = [];
  directionsService = null;
}

// ── Helpers ─────────────────────────────────────────────────────────

function _pinIcon(fillColor) {
  return {
    path: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z",
    fillColor,
    fillOpacity: 1,
    strokeColor: "#fff",
    strokeWeight: 1.5,
    scale: 1.5,
    anchor: new google.maps.Point(12, 22),
  };
}

export function fitBoundsToMarkers() {
  if (!map || markers.length === 0) return;
  const bounds = new google.maps.LatLngBounds();
  markers.forEach((m) => bounds.extend(m.getPosition()));
  map.fitBounds(bounds, 60); // 60px padding
}

export function getVehicleColor(vehicleIndex) {
  return VEHICLE_COLORS[vehicleIndex % VEHICLE_COLORS.length];
}
