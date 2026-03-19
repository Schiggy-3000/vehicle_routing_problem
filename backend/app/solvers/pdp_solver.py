from app.solvers.base_solver import BaseSolver


class PdpSolver(BaseSolver):
    """
    VRP with Pickups and Deliveries: pairs of pickup/delivery locations.
    Each pair must be served by the same vehicle, pickup before delivery.
    """

    def _add_constraints(self) -> None:
        max_distance = max(v.max_distance for v in self.request.vehicles)

        # Distance dimension is required for precedence constraints
        self.routing.AddDimension(
            self.transit_callback_index,
            0,
            max_distance,
            True,
            "Distance",
        )
        distance_dimension = self.routing.GetDimensionOrDie("Distance")

        locations = self.request.locations
        loc_id_to_index = {loc.id: i for i, loc in enumerate(locations)}

        for pair in self.request.pickup_delivery_pairs:
            pickup_node = loc_id_to_index[pair.pickup_id]
            delivery_node = loc_id_to_index[pair.delivery_id]

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
