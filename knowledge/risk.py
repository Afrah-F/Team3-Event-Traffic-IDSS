
"""Risk and sensitivity analysis for the traffic IDSS."""

from math import floor, isfinite
from shared.schema import (
    ROUTE_IDS,
    SimulationConfig,
    validate_allocation,
)


def _positive_number(value, name):
    if type(value) not in (int, float) or not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number")


def _scaled_allocation(counts, new_total):
    """Proportionally distribute new demand across eight routes."""

    old_total = sum(counts.values())

    if old_total <= 0:
        raise ValueError("Original demand must be positive")

    exact = {
        route: counts[route] * new_total / old_total
        for route in ROUTE_IDS
    }

    scaled = {
        route: floor(exact[route])
        for route in ROUTE_IDS
    }

    remaining = new_total - sum(scaled.values())

    order = sorted(
        ROUTE_IDS,
        key=lambda r: (-(exact[r] - scaled[r]), r)
    )

    for route in order[:remaining]:
        scaled[route] += 1

    return scaled


def _check_case(name, demand, allocation, capacities, note):
    """Check whether a scenario satisfies capacity constraints."""

    exceeded = [
        route for route in ROUTE_IDS
        if allocation[route] > capacities[route]
    ]

    total_capacity = sum(capacities.values())

    feasible = (
        demand <= total_capacity
        and not exceeded
    )

    warnings = []

    if demand > total_capacity:
        warnings.append(
            "Demand exceeds total assumed route capacity."
        )

    if exceeded:
        warnings.append(
            "Route capacity exceeded: " + ", ".join(exceeded)
        )

    if feasible:
        warnings.append(
            "Capacity checks pass, but SUMO testing is required."
        )

    return {
        "scenario": name,
        "capacity_feasible": feasible,
        "demand_vehicles": demand,
        "total_capacity_vehicles": total_capacity,
        "exceeded_routes": exceeded,
        "allocation_counts": allocation,
        "route_capacity": capacities,
        "assumption": note,
        "warnings": warnings
    }


def analyze_risk(
    config: SimulationConfig,
    allocation_counts: dict[str, int],
    demand_changes=(0.10, 0.20),
    capacity_reduction=0.20,
    reduced_route="R1",
    departure_window_factors=(0.75, 1.25)
) -> dict:
    """
    Evaluate sensitivity to changes in traffic assumptions.

    demand_changes: fractions of additional demand.
    capacity_reduction: fraction of capacity lost.
    departure_window_factors: relative departure-window lengths.
    """

    # Step 1: Check original allocation.
    validate_allocation(config, allocation_counts)

    if reduced_route not in ROUTE_IDS:
        raise ValueError("Unknown route")

    if (
        type(capacity_reduction) not in (int, float)
        or not (0 <= capacity_reduction <= 1)
    ):
        raise ValueError("Invalid capacity reduction")

    demand_changes = tuple(demand_changes)
    departure_window_factors = tuple(departure_window_factors)

    for change in demand_changes:
        if (
            type(change) not in (int, float)
            or not isfinite(change)
            or change < 0
        ):
            raise ValueError("Invalid demand change")

    for factor in departure_window_factors:
        _positive_number(factor, "Departure window factor")

    original = dict(allocation_counts)
    capacities = dict(config.route_capacity)
    cases = []

    # Step 2: Risk from increased traffic demand.
    for change in demand_changes:

        new_demand = round(
            config.vehicle_count * (1 + change)
        )

        new_allocation = _scaled_allocation(
            original, new_demand
        )

        cases.append(
            _check_case(
                f"demand_plus_{change:.0%}",
                new_demand,
                new_allocation,
                capacities.copy(),
                "Demand increased proportionally. "
                "Allocation has not been reoptimized."
            )
        )

    # Step 3: Risk from reduced capacity on one route.
    reduced_capacities = capacities.copy()

    reduced_capacities[reduced_route] = floor(
        capacities[reduced_route] * (1 - capacity_reduction)
    )

    cases.append(
        _check_case(
            f"{reduced_route}_capacity_minus_{capacity_reduction:.0%}",
            config.vehicle_count,
            original.copy(),
            reduced_capacities,
            "Selected route capacity was reduced."
        )
    )

    # Step 4: Risk from alternative departure windows.
    for factor in departure_window_factors:

        adjusted_capacities = {
            route: floor(capacities[route] * factor)
            for route in ROUTE_IDS
        }

        cases.append(
            _check_case(
                f"departure_window_x_{factor:g}",
                config.vehicle_count,
                original.copy(),
                adjusted_capacities,
                "Assumes route capacity scales linearly "
                "with departure-window length. "
                "This assumption must be verified."
            )
        )

    # Step 5: Summarize sensitivity results.
    sensitive = any(
        not case["capacity_feasible"]
        for case in cases
    )

    return {
        "baseline_demand_vehicles": config.vehicle_count,
        "baseline_departure_window_s": config.departure_window_s,
        "cases": cases,
        "sensitive_to_assumptions": sensitive,
        "warning": (
            "Preliminary sensitivity analysis only. "
            "Results do not predict vehicle delay, queues, "
            "or operational safety. SUMO evaluation is required."
        )
    }
