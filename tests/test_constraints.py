
import json
import unittest
from pathlib import Path

from shared.schema import SimulationConfig, ROUTE_IDS
from optimization.constraints import (
    is_feasible,
    percentages_to_counts,
    create_initial_allocation,
)


class TestConstraints(unittest.TestCase):

    def setUp(self):
        path = Path(__file__).resolve().parents[1]
        data = json.loads(
            (path / "config" / "scenarios.json").read_text(
                encoding="utf-8"
            )
        )

        self.config = SimulationConfig(
            scenario_id="medium",
            vehicle_count=data["scenarios"]["medium"]["vehicle_count"],
            route_capacity=data["route_capacity"],
            departure_window_s=data["departure_window_s"],
            seed=data["seed"],
            network_version=data["network_version"],
        )

    def test_initial_allocation(self):
        counts = create_initial_allocation(self.config)

        self.assertEqual(sum(counts.values()), 800)
        self.assertTrue(is_feasible(self.config, counts))

    def test_percentages_conversion(self):
        percentages = {
            route: 12.5 for route in ROUTE_IDS
        }

        counts = percentages_to_counts(percentages, 803)

        self.assertEqual(sum(counts.values()), 803)

    def test_invalid_total(self):
        counts = create_initial_allocation(self.config)
        counts["R1"] += 1

        self.assertFalse(is_feasible(self.config, counts))

    def test_capacity_exceeded(self):
        counts = {route: 0 for route in ROUTE_IDS}
        counts["R1"] = 800

        self.assertFalse(is_feasible(self.config, counts))

    def test_invalid_percentages(self):
        percentages = {
            route: 10 for route in ROUTE_IDS
        }

        with self.assertRaises(ValueError):
            percentages_to_counts(percentages, 800)

    def test_infeasible_demand(self):
        config = SimulationConfig(
            scenario_id="custom",
            vehicle_count=3000,
            route_capacity=self.config.route_capacity,
            departure_window_s=1800,
            seed=42,
            network_version="test-network",
        )

        with self.assertRaises(ValueError):
            create_initial_allocation(config)


if __name__ == "__main__":
    unittest.main()
