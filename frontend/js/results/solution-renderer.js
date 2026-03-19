import { clearRoutes, drawRoute } from "../map.js";

/**
 * Draws each vehicle's route as a coloured polyline on the map.
 */
export function renderRoutes(solutionResponse) {
  clearRoutes();
  solutionResponse.routes.forEach((route, i) => {
    drawRoute(route.stops, i);
  });
}
