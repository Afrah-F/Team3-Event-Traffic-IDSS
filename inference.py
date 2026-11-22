
"""Reasoning engine for the Event Traffic IDSS."""

from shared.schema import SimulationConfig, SimulationResult
from knowledge.rules import check_rules


def evaluate_facts(
    config: SimulationConfig,
    allocation_counts: dict,
    result: SimulationResult | None = None
) -> dict:
    """
    Apply traffic rules and assess simulation reliability.

    Decisions:
    - accept: valid allocation with a reliable result
    - review: more evidence or human review is needed
    - reject: invalid or infeasible allocation
    """

    # Step 1: Apply the allocation rules.
    rule_output = check_rules(config, allocation_counts)

    fired_rules = list(rule_output["fired_rule_ids"])
    warnings = list(rule_output["warnings"])

    # Step 2: Reject invalid allocations.
    if rule_output["decision"] == "reject":
        return {
            "decision": "reject",
            "fired_rule_ids": fired_rules,
            "warnings": warnings
        }

    # Step 3: A simulation result is required
    # before accepting a recommendation.
    if result is None:
        fired_rules.append("R07")
        warnings.append(
            "No simulation result is available yet."
        )
        decision = "review"

    else:
        decision = "accept"

        # Step 4: Check simulation status.
        if result.status != "success":
            fired_rules.append("R08")
            warnings.append(
                f"Simulation status: {result.status}."
            )
            decision = "review"

        # Step 5: Check whether all vehicles finished.
        if result.completed_vehicles < config.vehicle_count:
            fired_rules.append("R09")
            warnings.append(
                "Not all expected vehicles completed their trips."
            )
            decision = "review"

        # Step 6: Check essential performance metrics.
        if (
            result.average_delay_s is None
            or result.clearance_time_s is None
        ):
            fired_rules.append("R10")
            warnings.append(
                "Important simulation metrics are missing."
            )
            decision = "review"

        # Step 7: Check result consistency.
        if result.allocation_counts != allocation_counts:
            fired_rules.append("R11")
            warnings.append(
                "Simulation allocation does not match "
                "the proposed allocation."
            )
            decision = "review"

        if result.departed_vehicles < result.completed_vehicles:
            fired_rules.append("R12")
            warnings.append(
                "Completed vehicles exceed departed vehicles."
            )
            decision = "review"

    # Step 8: Return a structured result.
    return {
        "decision": decision,
        "fired_rule_ids": fired_rules,
        "warnings": warnings
    }
