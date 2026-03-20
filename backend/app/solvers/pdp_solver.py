from app.solvers.base_solver import BaseSolver


class PdpSolver(BaseSolver):
    """
    VRP with Pickups and Deliveries: pairs of pickup/delivery locations.
    Each pair must be served by the same vehicle, pickup before delivery.
    """

    def _add_constraints(self) -> None:
        distance_dimension = self._add_distance_dimension(span_cost_coefficient=0)

        locations = self.request.locations
        loc_id_to_index = {loc.id: i for i, loc in enumerate(locations)}

        for pair in self.request.pickup_delivery_pairs:
            pickup_node = loc_id_to_index.get(pair.pickup_id)
            if pickup_node is None:
                raise ValueError(f"pickup_id '{pair.pickup_id}' not found in locations")
            delivery_node = loc_id_to_index.get(pair.delivery_id)
            if delivery_node is None:
                raise ValueError(f"delivery_id '{pair.delivery_id}' not found in locations")

            pickup_index = self.manager.NodeToIndex(pickup_node)
            delivery_index = self.manager.NodeToIndex(delivery_node)

            self.routing.AddPickupAndDelivery(pickup_index, delivery_index)

            # Pickup must come before delivery on the route
            self.routing.solver().Add(
                distance_dimension.CumulVar(pickup_index)
                <= distance_dimension.CumulVar(delivery_index)
            )
            # Both stops must be served by the same vehicle
            self.routing.solver().Add(
                self.routing.VehicleVar(pickup_index)
                == self.routing.VehicleVar(delivery_index)
            )

        self._add_time_dimension()
