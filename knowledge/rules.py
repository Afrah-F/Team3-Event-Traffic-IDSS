
"""Knowledge representation: production rules and working-memory facts.

"""
from dataclasses import dataclass
from typing import Tuple
from shared.schema import ROUTE_IDS, SimulationConfig, SimulationResult


@dataclass(frozen=True)
class ProductionRule:
    rule_id: str
    priority: int
    conditions: Tuple[str, ...]  # IF all named facts are true
    conclusion: str               # THEN add this fact to working memory
    explanation: str
    source: str


# Declarative production rules: knowledge is separate from the inference engine.
RULES = (
    ProductionRule("R01", 100, ("invalid_route_counts",), "invalid_candidate",
                   "Allocation must contain nonnegative integer counts for R1-R8.", "shared/schema.py"),
    ProductionRule("R02", 100, ("allocation_total_wrong",), "invalid_candidate",
                   "Assigned vehicles do not equal requested demand.", "shared/schema.py"),
    ProductionRule("R03", 100, ("insufficient_total_capacity",), "invalid_candidate",
                   "Demand exceeds total assumed route capacity.", "shared/schema.py"),
    ProductionRule("R04", 100, ("route_over_capacity",), "invalid_candidate",
                   "At least one route exceeds its assumed capacity.", "shared/schema.py"),
    ProductionRule("R05", 50, ("simulation_missing",), "unverified_result",
                   "A simulation result is required before accepting an allocation.", "team task plan"),
    ProductionRule("R06", 50, ("simulation_not_successful",), "unverified_result",
                   "The simulation did not report success.", "team task plan"),
    ProductionRule("R07", 50, ("trips_incomplete",), "unverified_result",
                   "Not all requested vehicles completed their trips.", "team task plan"),
    ProductionRule("R08", 50, ("metrics_missing",), "unverified_result",
                   "Average delay or clearance time is missing/invalid.", "team task plan"),
    ProductionRule("R09", 50, ("result_mismatch",), "unverified_result",
                   "The simulation's allocation or scenario differs from the request.", "team task plan"),
    ProductionRule("R10", 50, ("vehicle_counts_inconsistent",), "unverified_result",
                   "Departed/completed vehicle counts are inconsistent.", "team task plan"),
    # Meta rules: reject takes priority over review; evidence is needed for acceptance.
    ProductionRule("MR1", 100, ("invalid_candidate",), "decision_reject",
                   "Reject the invalid candidate.", "ICS 487 meta-rules + team constraints"),
    ProductionRule("MR2", 50, ("unverified_result",), "decision_review",
                   "Request human review or additional simulation evidence.", "ICS 487 meta-rules"),
    ProductionRule("MR3", 10, ("candidate_valid", "simulation_reliable"), "decision_accept",
                   "The candidate passed the defined checks; this is not a safety guarantee.", "team task plan"),
)


def _valid_number(value):
    return type(value) in (int, float) and 0 <= value < float("inf")


def collect_facts(config: SimulationConfig, allocation_counts: dict,
                  result: SimulationResult | None = None) -> set[str]:
    """Create working-memory facts from provided observations, without assumptions."""
    facts = set()
    valid_routes = (isinstance(allocation_counts, dict)
                    and set(allocation_counts) == set(ROUTE_IDS)
                    and all(type(n) is int and n >= 0 for n in allocation_counts.values()))
    if not valid_routes:
        facts.add("invalid_route_counts")
    else:
        if sum(allocation_counts.values()) != config.vehicle_count:
            facts.add("allocation_total_wrong")
        if any(allocation_counts[r] > config.route_capacity[r] for r in ROUTE_IDS):
            facts.add("route_over_capacity")
    if sum(config.route_capacity.values()) < config.vehicle_count:
        facts.add("insufficient_total_capacity")
    if not facts.intersection({"invalid_route_counts", "allocation_total_wrong",
                                "route_over_capacity", "insufficient_total_capacity"}):
        facts.add("candidate_valid")

    if result is None:
        facts.add("simulation_missing")
        return facts
    if result.status != "success":
        facts.add("simulation_not_successful")
    if result.completed_vehicles < config.vehicle_count:
        facts.add("trips_incomplete")
    if (not _valid_number(result.average_delay_s)
            or not _valid_number(result.clearance_time_s)):
        facts.add("metrics_missing")
    if (result.scenario_id != config.scenario_id
            or result.seed != config.seed
            or result.allocation_counts != allocation_counts):
        facts.add("result_mismatch")
    if (type(result.departed_vehicles) is not int
            or type(result.completed_vehicles) is not int
            or result.departed_vehicles != config.vehicle_count
            or result.completed_vehicles > result.departed_vehicles):
        facts.add("vehicle_counts_inconsistent")
    if not facts.intersection({"simulation_not_successful", "trips_incomplete",
                               "metrics_missing", "result_mismatch",
                               "vehicle_counts_inconsistent"}):
        facts.add("simulation_reliable")
    return facts

