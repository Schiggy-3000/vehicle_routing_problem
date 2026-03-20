import { clearRoutes, drawRoute } from "../map.js";

/**
 * Draws each vehicle's route on the map using the Directions API.
 */
export async function renderRoutes(solutionResponse) {
  clearRoutes();
  await Promise.all(
    solutionResponse.routes.map((route, i) => drawRoute(route.stops, i))
  );
}
