import { clearRoutes, drawRoute } from "../map.js";

/**
 * Draws each vehicle's route on the map using the Directions API.
 * Returns true if any route fell back to straight lines.
 */
export async function renderRoutes(solutionResponse) {
  clearRoutes();
  const fallbacks = await Promise.all(
    solutionResponse.routes.map((route, i) => drawRoute(route.stops, i))
  );
  return fallbacks.some(Boolean);
}
