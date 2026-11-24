
"""Simple what-if/sensitivity cases; no fabricated simulation metrics.

Capacity values are draft vehicles per departure window, not physical guarantees.
"""
from math import floor, isfinite
from shared.schema import ROUTE_IDS, SimulationConfig, validate_allocation


def _scaled_counts(counts, total):
    """Keep original route shares for a demand what-if (not re-optimization)."""
    original_total = sum(counts.values())
    exact = {r: total * counts[r] / original_total for r in ROUTE_IDS}
    scaled = {r: floor(exact[r]) for r in ROUTE_IDS}
    left = total - sum(scaled.values())
    order = sorted(ROUTE_IDS, key=lambda r: (-(exact[r] - scaled[r]), r))
    for route in order[:left]:
        scaled[route] += 1
    return scaled


def _case(name, demand, assigned, capacities, assumption):
    violations = [r for r in ROUTE_IDS if assigned[r] > capacities[r]]
    feasible = demand <= sum(capacities.values()) and not violations
    return {"scenario": name, "capacity_feasible": feasible,
            "demand_vehicles": demand, "allocation_counts": assigned,
            "route_capacity": capacities, "exceeded_routes": violations,
            "assumption": assumption,
            "warning": ("Preliminary capacity checks only; requires SUMO evaluation." if feasible
                        else "Capacity feasibility check failed; review/re-optimize allocation.")}


def analyze_risk(config: SimulationConfig, allocation_counts: dict,
                 demand_changes=(0.10, 0.20), capacity_reduction=0.20,
                 reduced_route="R1", departure_window_factors=(0.75, 1.25)) -> dict:
    validate_allocation(config, allocation_counts)
    if reduced_route not in ROUTE_IDS:
        raise ValueError("Unknown route")
    if (type(capacity_reduction) not in (int, float)
            or not isfinite(capacity_reduction)
            or not 0 <= capacity_reduction <= 1):
        raise ValueError("capacity_reduction must be between 0 and 1")
    demand_changes = tuple(demand_changes)
    departure_window_factors = tuple(departure_window_factors)
    for change in demand_changes:
        if type(change) not in (int, float) or not isfinite(change) or change < 0:
            raise ValueError("demand changes must be nonnegative finite numbers")
    for factor in departure_window_factors:
        if type(factor) not in (int, float) or not isfinite(factor) or factor <= 0:
            raise ValueError("departure window factors must be positive finite numbers")

    base = dict(allocation_counts)
    capacities = dict(config.route_capacity)
    cases = []
    for change in demand_changes:
        demand = round(config.vehicle_count * (1 + change))
        cases.append(_case(f"demand_plus_{change:.0%}", demand,
                           _scaled_counts(base, demand), capacities.copy(),
                           "Demand rises; original allocation shares are retained."))
    changed = capacities.copy()
    changed[reduced_route] = floor(changed[reduced_route] * (1 - capacity_reduction))
    cases.append(_case(f"{reduced_route}_capacity_minus_{capacity_reduction:.0%}",
                       config.vehicle_count, base.copy(), changed,
                       "One route loses assumed capacity; allocation is unchanged."))
    for factor in departure_window_factors:
        adjusted = {r: floor(capacities[r] * factor) for r in ROUTE_IDS}
        cases.append(_case(f"departure_window_x_{factor:g}", config.vehicle_count,
                           base.copy(), adjusted,
                           "ASSUMPTION ONLY: modeled capacities scale linearly with window length."))
    return {"baseline_demand_vehicles": config.vehicle_count,
            "baseline_departure_window_s": config.departure_window_s,
            "cases": cases,
            "sensitive_to_assumptions": any(not c["capacity_feasible"] for c in cases),
            "warning": "Sensitivity checks are not measured delays or operational safety guarantees."}
