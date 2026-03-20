from app.solvers.base_solver import BaseSolver


class CvrpSolver(BaseSolver):
    """
    Capacitated VRP: each location has a demand, each vehicle has a capacity limit.
    """

    def _add_constraints(self) -> None:
        self._add_distance_dimension()

        # Capacity dimension
        locations = self.request.locations

        def demand_callback(from_index: int) -> int:
            node = self.manager.IndexToNode(from_index)
            return locations[node].demand

        demand_callback_index = self.routing.RegisterUnaryTransitCallback(demand_callback)

        vehicle_capacities = [v.capacity for v in self.request.vehicles]

        self.routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,                   # null capacity slack
            vehicle_capacities,
            True,                # start_cumul_to_zero
            "Capacity",
        )

        self._add_time_dimension()
