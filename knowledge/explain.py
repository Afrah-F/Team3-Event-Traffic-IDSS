
"""Evidence-based explanation of baseline vs optimized simulation results.

Compares alternatives and explains trade-offs; does not infer causality.
"""
from math import isfinite
from shared.schema import ROUTE_IDS, SimulationResult


def _good_metric(value):
    return type(value) in (int, float) and isfinite(value) and value >= 0


def explain_recommendation(baseline: SimulationResult,
                           optimized: SimulationResult,
                           tolerance_s: float = 1.0) -> dict:
    if not _good_metric(tolerance_s):
        raise ValueError("tolerance_s must be nonnegative and finite")
    warnings = []
    for label, result in (("Baseline", baseline), ("Optimized", optimized)):
        if result.status != "success":
            warnings.append(f"{label} run did not succeed")
        if (type(result.departed_vehicles) is not int
                or type(result.completed_vehicles) is not int
                or result.departed_vehicles <= 0
                or result.completed_vehicles != result.departed_vehicles):
            warnings.append(f"{label} run has incomplete/inconsistent trips")
        if not _good_metric(result.average_delay_s):
            warnings.append(f"{label} average delay is missing or invalid")
        if (not isinstance(result.allocation_counts, dict)
                or set(result.allocation_counts) != set(ROUTE_IDS)):
            warnings.append(f"{label} allocation is incomplete")
    if baseline.scenario_id != optimized.scenario_id:
        warnings.append("Scenarios differ")
    if baseline.seed != optimized.seed:
        warnings.append("Random seeds differ")
    if baseline.departed_vehicles != optimized.departed_vehicles:
        warnings.append("Vehicle counts differ")
    if warnings:
        return {"recommendation": "review", "summary": "Comparable simulation evidence is unavailable.",
                "comparison": {}, "route_shifts": {}, "warnings": warnings}

    old = baseline.average_delay_s
    new = optimized.average_delay_s
    delta = new - old
    shifts = {r: {"before": baseline.allocation_counts[r],
                  "after": optimized.allocation_counts[r],
                  "change": optimized.allocation_counts[r] - baseline.allocation_counts[r]}
              for r in ROUTE_IDS}
    clearance_delta = None
    if (_good_metric(baseline.clearance_time_s)
            and _good_metric(optimized.clearance_time_s)):
        clearance_delta = optimized.clearance_time_s - baseline.clearance_time_s

    if delta < -tolerance_s:
        choice = "optimized"
        summary = f"Optimized run had {-delta:.2f} s lower measured average delay."
    elif delta > tolerance_s:
        choice = "baseline"
        summary = f"Optimized run had {delta:.2f} s higher measured average delay."
    elif clearance_delta is None:
        choice = "review"
        summary = "Average delays were similar and clearance comparison is unavailable."
    elif clearance_delta < 0:
        choice = "optimized"
        summary = "Average delays were similar; optimized run had shorter clearance time."
    elif clearance_delta > 0:
        choice = "baseline"
        summary = "Average delays were similar; baseline run had shorter clearance time."
    else:
        choice = "review"
        summary = "Average delay and clearance time did not distinguish the runs."

    if clearance_delta is not None and delta * clearance_delta < 0:
        warnings.append("Average delay and clearance time move in opposite directions (trade-off).")
    warnings.append("Use only runs with the same network and departure assumptions; this must be checked by the team.")
    return {"recommendation": choice, "summary": summary,
            "comparison": {"baseline_delay_s": old, "optimized_delay_s": new,
                           "delay_change_s": delta,
                           "delay_change_pct": 100 * delta / old if old > 0 else None,
                           "clearance_change_s": clearance_delta},
            "route_shifts": shifts, "warnings": warnings}

