"""Entry point for the VRP solver."""

from models.data_model import create_data_model
from routing.solver import solve_vrp
from utils.printer import print_solution

def main():
    """Main function to run the VRP solver."""
    print("Initializing Data Model...")
    data = create_data_model()

    print("Running Solver...")
    manager, routing, solution = solve_vrp(data)

    if solution:
        print("\nSolution Found:")
        print_solution(data, manager, routing, solution)
    else:
        print("No solution found!")

if __name__ == "__main__":
    main()
