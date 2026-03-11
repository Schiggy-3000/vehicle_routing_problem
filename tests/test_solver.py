"""Tests for the routing solver."""

import unittest
from src.models.data_model import create_data_model
from src.routing.solver import solve_vrp

class TestVRPSolver(unittest.TestCase):
    def test_solve_vrp(self):
        """Test that the VRP solver can find a valid solution for the basic data model."""
        data = create_data_model()
        manager, routing, solution = solve_vrp(data)
        
        self.assertIsNotNone(solution, "Solver should find a solution.")
        self.assertGreater(solution.ObjectiveValue(), 0, "Objective value should be > 0.")
        
if __name__ == '__main__':
    unittest.main()
