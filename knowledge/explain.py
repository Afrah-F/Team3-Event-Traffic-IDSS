
"""Explain baseline and optimized traffic simulation results."""

from shared.schema import ROUTE_IDS, SimulationResult


def explain_recommendation(
    baseline: SimulationResult,
    optimized: SimulationResult,
    tolerance_s: float = 1.0
) -> dict:
    """
    Compare two simulation results and explain the decision.

    Both results must represent comparable test conditions.
    """

    warnings = []
    route_shifts = {}

    # Step 1: Check simulation reliability.
    for name, result in [
        ("Baseline", baseline),
        ("Optimized", optimized)
    ]:
        if result.status != "success":
            warnings.append(
                f"{name} simulation status is {result.status}."
            )

        if result.completed_vehicles != result.departed_vehicles:
            warnings.append(
                f"{name} simulation has incomplete trips."
            )

        if result.average_delay_s is None:
            warnings.append(
                f"{name} average delay is missing."
            )

    # Step 2: Check comparability.
    if baseline.scenario_id != optimized.scenario_id:
        warnings.append(
            "Results use different traffic scenarios."
        )

    if baseline.seed != optimized.seed:
        warnings.append(
            "Results use different random seeds."
        )

    if baseline.departed_vehicles != optimized.departed_vehicles:
        warnings.append(
            "Results have different departed vehicle counts."
        )

    if set(baseline.allocation_counts) != set(ROUTE_IDS):
        warnings.append("Baseline route data is incomplete.")

    if set(optimized.allocation_counts) != set(ROUTE_IDS):
        warnings.append("Optimized route data is incomplete.")

    # Step 3: Stop if comparisons are not reliable.
    if warnings:
        return {
            "recommendation": "review",
            "summary": (
                "A reliable comparison cannot be made yet."
            ),
            "comparison": {},
            "route_shifts": {},
            "warnings": warnings
        }

    # Step 4: Calculate changes in average delay.
    old_delay = baseline.average_delay_s
    new_delay = optimized.average_delay_s

    delay_change_s = new_delay - old_delay

    if old_delay > 0:
        delay_change_pct = (
            delay_change_s / old_delay
        ) * 100
    else:
        delay_change_pct = None

    # Step 5: Calculate changes in route allocations.
    for route in ROUTE_IDS:
        before = baseline.allocation_counts[route]
        after = optimized.allocation_counts[route]

        route_shifts[route] = {
            "before": before,
            "after": after,
            "change": after - before
        }

    # Step 6: Compare clearance time, when available.
    clearance_change_s = None

    if (
        baseline.clearance_time_s is not None
        and optimized.clearance_time_s is not None
    ):
        clearance_change_s = (
            optimized.clearance_time_s
            - baseline.clearance_time_s
        )

    # Step 7: Make an evidence-based recommendation.
    if delay_change_s < -tolerance_s:
        recommendation = "optimized"
        summary = (
            f"Optimized allocation reduced average delay "
            f"by {-delay_change_s:.2f} seconds."
        )

    elif delay_change_s > tolerance_s:
        recommendation = "baseline"
        summary = (
            f"Optimized allocation increased average delay "
            f"by {delay_change_s:.2f} seconds."
        )

    else:
        # Delays are close; use clearance time to break a tie.
        if clearance_change_s is None:
            recommendation = "review"
            summary = (
                "Average delays are similar, but clearance "
                "time is unavailable for comparison."
            )

        elif clearance_change_s < 0:
            recommendation = "optimized"
            summary = (
                "Average delays are similar. Optimized "
                "allocation has a shorter clearance time."
            )

        elif clearance_change_s > 0:
            recommendation = "baseline"
            summary = (
                "Average delays are similar. Baseline "
                "allocation has a shorter clearance time."
            )

        else:
            recommendation = "review"
            summary = (
                "Both allocations have similar average delay "
                "and identical clearance time."
            )

    # Step 8: Report trade-offs.
    if (
        recommendation == "optimized"
        and clearance_change_s is not None
        and clearance_change_s > 0
    ):
        warnings.append(
            "Average delay improved, but clearance time "
            "increased."
        )

    if (
        recommendation == "baseline"
        and clearance_change_s is not None
        and clearance_change_s < 0
    ):
        warnings.append(
            "Optimized allocation has lower clearance time, "
            "but worse average delay."
        )

    # Step 9: Return results for Student 4's dashboard.
    return {
        "recommendation": recommendation,
        "summary": summary,
        "comparison": {
            "baseline_delay_s": old_delay,
            "optimized_delay_s": new_delay,
            "delay_change_s": delay_change_s,
            "delay_change_pct": delay_change_pct,
            "clearance_change_s": clearance_change_s
        },
        "route_shifts": route_shifts,
        "warnings": warnings
    }
