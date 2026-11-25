"""Tests for Student 3's knowledge-based IDSS modules.
Run from the project root: python -m unittest discover -s tests -v
"""
import unittest

from shared.schema import ROUTE_IDS, SimulationConfig, SimulationResult
from knowledge.rules import RULES, collect_facts
from knowledge.inference import evaluate_facts
from knowledge.explain import explain_recommendation
from knowledge.risk import analyze_risk


def make_config():
    return SimulationConfig(
        scenario_id="medium",
        vehicle_count=800,
        route_capacity={"R1": 300, **{f"R{i}": 250 for i in range(2, 9)}},
        departure_window_s=1800,
        seed=42,
        network_version="draft-network-v0",
    )


def make_allocation():
    return {route: 100 for route in ROUTE_IDS}


def make_result(allocation=None, delay=120.0, clearance=1600.0,
                status="success", completed=800, scenario="medium", seed=42):
    return SimulationResult(
        status=status,
        scenario_id=scenario,
        run_id="test-run",
        seed=seed,
        allocation_counts=make_allocation() if allocation is None else allocation,
        departed_vehicles=800,
        completed_vehicles=completed,
        average_delay_s=delay,
        clearance_time_s=clearance,
    )


class TestKnowledgeRepresentation(unittest.TestCase):
    def test_rules_are_production_rules(self):
        self.assertTrue(any(r.rule_id == "R04" and
                            "route_over_capacity" in r.conditions and
                            r.conclusion == "invalid_candidate" for r in RULES))
        self.assertTrue(any(r.rule_id == "MR1" for r in RULES))

    def test_collect_facts_for_valid_allocation(self):
        facts = collect_facts(make_config(), make_allocation())
        self.assertIn("candidate_valid", facts)
        self.assertIn("simulation_missing", facts)
        self.assertNotIn("route_over_capacity", facts)

    def test_capacity_violation_fact(self):
        allocation = {"R1": 350, "R2": 50, **{f"R{i}": 100 for i in range(3, 9)}}
        facts = collect_facts(make_config(), allocation)
        self.assertIn("route_over_capacity", facts)


class TestInference(unittest.TestCase):
    def test_missing_simulation_causes_review(self):
        output = evaluate_facts(make_config(), make_allocation())
        self.assertEqual(output["decision"], "review")
        self.assertIn("R05", output["fired_rule_ids"])
        self.assertIn("MR2", output["fired_rule_ids"])

    def test_successful_simulation_causes_accept(self):
        output = evaluate_facts(make_config(), make_allocation(), make_result())
        self.assertEqual(output["decision"], "accept")
        self.assertIn("MR3", output["fired_rule_ids"])

    def test_conflicting_reject_and_review_reject_wins(self):
        allocation = {"R1": 350, "R2": 50, **{f"R{i}": 100 for i in range(3, 9)}}
        output = evaluate_facts(make_config(), allocation)
        self.assertEqual(output["decision"], "reject")
        self.assertIn("R04", output["fired_rule_ids"])
        self.assertIn("MR1", output["fired_rule_ids"])
        self.assertIn("MR2", output["fired_rule_ids"])
        self.assertTrue(output["inference_trace"])

    def test_incomplete_simulation_causes_review(self):
        output = evaluate_facts(make_config(), make_allocation(),
                                make_result(completed=750))
        self.assertEqual(output["decision"], "review")
        self.assertIn("R07", output["fired_rule_ids"])


class TestExplain(unittest.TestCase):
    def test_improvement_explained(self):
        report = explain_recommendation(make_result(delay=120),
                                        make_result(delay=90, clearance=1500))
        self.assertEqual(report["recommendation"], "optimized")
        self.assertAlmostEqual(report["comparison"]["delay_change_pct"], -25.0)

    def test_worse_optimized_result_prefers_baseline(self):
        report = explain_recommendation(make_result(delay=90), make_result(delay=120))
        self.assertEqual(report["recommendation"], "baseline")

    def test_different_scenarios_require_review(self):
        report = explain_recommendation(make_result(), make_result(scenario="high"))
        self.assertEqual(report["recommendation"], "review")


class TestRisk(unittest.TestCase):
    def test_default_five_sensitivity_cases(self):
        report = analyze_risk(make_config(), make_allocation())
        self.assertEqual(len(report["cases"]), 5)
        self.assertEqual(report["cases"][0]["demand_vehicles"], 880)
        self.assertEqual(report["cases"][1]["demand_vehicles"], 960)
        self.assertEqual(report["cases"][2]["route_capacity"]["R1"], 240)

    def test_shorter_departure_window_violates_capacity(self):
        # R1 initially at 300. A 0.75-length window reduces its assumed capacity to 225.
        allocation = {"R1": 300, "R2": 0, "R3": 0, "R4": 100,
                      "R5": 100, "R6": 100, "R7": 100, "R8": 100}
        report = analyze_risk(make_config(), allocation)
        short = next(c for c in report["cases"] if c["scenario"] == "departure_window_x_0.75")
        self.assertFalse(short["capacity_feasible"])
        self.assertIn("R1", short["exceeded_routes"])

    def test_invalid_risk_parameter_raises(self):
        with self.assertRaises(ValueError):
            analyze_risk(make_config(), make_allocation(), reduced_route="R9")


class TestIndividualProductionRules(unittest.TestCase):
    """One focused check for each previously uncovered production rule."""

    def check_rule(self, rule_id, allocation=None, result=None, config=None,
                   expected_decision=None):
        config = make_config() if config is None else config
        allocation = make_allocation() if allocation is None else allocation
        output = evaluate_facts(config, allocation, result)
        self.assertIn(rule_id, output["fired_rule_ids"])
        self.assertTrue(any(step["rule_id"] == rule_id
                            for step in output["inference_trace"]))
        if expected_decision is not None:
            self.assertEqual(output["decision"], expected_decision)
        return output

    def test_R01_missing_route(self):
        allocation = make_allocation()
        del allocation["R8"]
        self.check_rule("R01", allocation=allocation, expected_decision="reject")

    def test_R01_negative_count(self):
        allocation = make_allocation()
        allocation["R1"] = -1
        self.check_rule("R01", allocation=allocation, expected_decision="reject")

    def test_R02_wrong_allocation_total(self):
        allocation = make_allocation()
        allocation["R1"] = 99
        self.check_rule("R02", allocation=allocation, expected_decision="reject")

    def test_R03_insufficient_total_capacity(self):
        config = SimulationConfig(
            scenario_id="medium", vehicle_count=800,
            route_capacity={route: 90 for route in ROUTE_IDS},
            departure_window_s=1800, seed=42,
            network_version="draft-network-v0")
        self.check_rule("R03", config=config, expected_decision="reject")

    def test_R04_route_capacity_exceeded(self):
        allocation = make_allocation()
        allocation["R1"] = 350
        allocation["R2"] = 50
        self.check_rule("R04", allocation=allocation, expected_decision="reject")

    def test_R05_missing_simulation(self):
        self.check_rule("R05", expected_decision="review")

    def test_R06_failed_simulation(self):
        self.check_rule("R06", result=make_result(status="simulation_failed"),
                        expected_decision="review")

    def test_R07_incomplete_trips(self):
        self.check_rule("R07", result=make_result(completed=700),
                        expected_decision="review")

    def test_R08_missing_metric(self):
        self.check_rule("R08", result=make_result(delay=None),
                        expected_decision="review")

    def test_R08_invalid_metric(self):
        self.check_rule("R08", result=make_result(clearance=-1),
                        expected_decision="review")

    def test_R09_mismatched_scenario(self):
        self.check_rule("R09", result=make_result(scenario="high"),
                        expected_decision="review")

    def test_R09_mismatched_seed(self):
        self.check_rule("R09", result=make_result(seed=7),
                        expected_decision="review")

    def test_R10_inconsistent_departed_count(self):
        result = make_result()
        result.departed_vehicles = 790
        self.check_rule("R10", result=result, expected_decision="review")

    def test_meta_rules_and_conflict_resolution(self):
        # Both reject and review become derivable; reject has precedence.
        allocation = make_allocation()
        allocation["R1"] = 350
        allocation["R2"] = 50
        output = evaluate_facts(make_config(), allocation)
        self.assertEqual(output["decision"], "reject")
        self.assertTrue({"MR1", "MR2"}.issubset(output["fired_rule_ids"]))
        trace_ids = [step["rule_id"] for step in output["inference_trace"]]
        self.assertLess(trace_ids.index("MR1"), trace_ids.index("MR2"))
        self.assertEqual(len(trace_ids), len(set(trace_ids)))

    def test_MR3_only_with_valid_candidate_and_reliable_simulation(self):
        accepted = evaluate_facts(make_config(), make_allocation(), make_result())
        self.assertEqual(accepted["decision"], "accept")
        self.assertIn("MR3", accepted["fired_rule_ids"])
        self.assertTrue({"candidate_valid", "simulation_reliable"}.issubset(
            accepted["working_memory"]))
        unverified = evaluate_facts(make_config(), make_allocation())
        self.assertNotIn("MR3", unverified["fired_rule_ids"])


if __name__ == "__main__":
    unittest.main()
