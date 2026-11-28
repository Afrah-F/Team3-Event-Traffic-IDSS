
"""Unit tests using mock data, not real SUMO results."""

import unittest

from shared.schema import (
    ROUTE_IDS,
    SimulationConfig,
    SimulationResult,
)

from optimization.constraints import (
    is_feasible,
    create_initial_allocation,
)

from optimization.hill_climbing import (
    hill_climbing,
    generate_neighbors,
    is_better,
)


def mock_evaluator(config, allocation_counts, seed):
    """Artificial objective for unit testing only."""

    target = {
        "R1": 50,
        "R2": 50,
        "R3": 50,
        "R4": 50,
        "R5": 50,
        "R6": 50,
        "R7": 50,
        "R8": 50,
    }

    delay = sum(
        (allocation_counts[r] - target[r]) ** 2
        for r in ROUTE_IDS
    ) / config.vehicle_count

    return SimulationResult(
        status="success",
        scenario_id=config.scenario_id,
        run_id="mock-test",
        seed=seed,
        allocation_counts=allocation_counts.copy(),
        departed_vehicles=config.vehicle_count,
        completed_vehicles=config.vehicle_count,
        average_delay_s=delay,
        clearance_time_s=100 + delay,
        average_travel_time_s=60 + delay,
        mean_queue_vehicles=delay / 10,
        warnings=["MOCK DATA - TESTING ONLY"],
    )


class TestOptimizer(unittest.TestCase):

    def setUp(self):
        self.config = SimulationConfig(
            scenario_id="low",
            vehicle_count=400,
            route_capacity={
                route: 100 for route in ROUTE_IDS
            },
            departure_window_s=1800,
            seed=42,
            network_version="mock-network",
        )

        self.initial = {
            "R1": 100,
            "R2": 80,
            "R3": 60,
            "R4": 40,
            "R5": 30,
            "R6": 30,
            "R7": 30,
            "R8": 30,
        }

    def test_neighbors_are_feasible(self):
        neighbors = generate_neighbors(
            self.config,
            self.initial,
            step_size=10,
        )

        self.assertGreater(len(neighbors), 0)

        for candidate in neighbors:
            self.assertTrue(
                is_feasible(self.config, candidate)
            )
            self.assertEqual(
                sum(candidate.values()), 400
            )

    def test_optimizer_improves_delay(self):
        initial_result = mock_evaluator(
            self.config,
            self.initial,
            42,
        )

        result = hill_climbing(
            self.config,
            mock_evaluator,
            initial_allocation=self.initial,
            step_size=10,
            max_evaluations=500,
        )

        self.assertLess(
            result.best_result.average_delay_s,
            initial_result.average_delay_s,
        )

        self.assertTrue(
            is_feasible(
                self.config,
                result.best_allocation,
            )
        )

    def test_multiple_alternatives(self):
        result = hill_climbing(
            self.config,
            mock_evaluator,
            initial_allocation=self.initial,
        )

        self.assertGreater(
            len(result.alternatives), 1
        )

        for alternative in result.alternatives:
            self.assertTrue(
                is_feasible(
                    self.config,
                    alternative.allocation_counts,
                )
            )

    def test_evaluation_budget(self):
        result = hill_climbing(
            self.config,
            mock_evaluator,
            initial_allocation=self.initial,
            max_evaluations=5,
        )

        self.assertLessEqual(result.evaluations, 5)

    def test_no_improvement(self):
        initial = create_initial_allocation(
            self.config
        )

        result = hill_climbing(
            self.config,
            mock_evaluator,
            initial_allocation=initial,
        )

        self.assertEqual(result.iterations, 0)

    def test_clearance_time_tie_breaker(self):
        current = mock_evaluator(
            self.config, self.initial, 42
        )

        candidate = mock_evaluator(
            self.config, self.initial, 42
        )

        candidate.clearance_time_s -= 10

        self.assertTrue(
            is_better(candidate, current)
        )

    def test_failed_simulation(self):

        def failed_evaluator(config, counts, seed):
            raise RuntimeError("Mock simulation failure")

        with self.assertRaises(RuntimeError):
            hill_climbing(
                self.config,
                failed_evaluator,
                initial_allocation=self.initial,
            )

    def test_infeasible_initial_allocation(self):
        invalid = self.initial.copy()
        invalid["R1"] += 10

        with self.assertRaises(ValueError):
            hill_climbing(
                self.config,
                mock_evaluator,
                initial_allocation=invalid,
            )


if __name__ == "__main__":
    unittest.main()
