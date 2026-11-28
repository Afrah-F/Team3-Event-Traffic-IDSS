
"""Allocation constraints and feasible distribution utilities."""

from fractions import Fraction
from math import isfinite

from shared.schema import (
    ROUTE_IDS,
    SimulationConfig,
    validate_allocation,
)


def is_feasible(
    config: SimulationConfig,
    allocation_counts: dict[str, int],
) -> bool:
    """Return True if the allocation satisfies all constraints."""
    try:
        validate_allocation(config, allocation_counts)
        return True
    except ValueError:
        return False


def percentages_to_counts(
    percentages: dict[str, float],
    vehicle_count: int,
) -> dict[str, int]:
    """Convert percentages into exact integer vehicle counts."""

    if type(vehicle_count) is not int or vehicle_count <= 0:
        raise ValueError("Vehicle count must be a positive integer")

    if set(percentages) != set(ROUTE_IDS):
        raise ValueError("Percentages must contain R1 through R8")

    for value in percentages.values():
        if (
            type(value) not in (int, float)
            or not isfinite(value)
            or value < 0
        ):
            raise ValueError("Invalid percentage")

    weights = {
        route: Fraction(str(percentages[route]))
        for route in ROUTE_IDS
    }

    total = sum(weights.values())

    if abs(float(total) - 100) > 1e-6:
        raise ValueError("Percentages must sum to 100")

    raw = {
        route: weights[route] * vehicle_count / total
        for route in ROUTE_IDS
    }

    counts = {
        route: int(raw[route])
        for route in ROUTE_IDS
    }

    remaining = vehicle_count - sum(counts.values())

    ranked_routes = sorted(
        ROUTE_IDS,
        key=lambda route: raw[route] - counts[route],
        reverse=True,
    )

    for route in ranked_routes[:remaining]:
        counts[route] += 1

    return counts


def create_initial_allocation(
    config: SimulationConfig,
) -> dict[str, int]:
    """Create a feasible capacity-proportional allocation."""

    total_capacity = sum(config.route_capacity.values())

    if config.vehicle_count > total_capacity:
        raise ValueError("Insufficient total route capacity")

    raw = {
        route: Fraction(
            config.vehicle_count * config.route_capacity[route],
            total_capacity,
        )
        for route in ROUTE_IDS
    }

    counts = {
        route: int(raw[route])
        for route in ROUTE_IDS
    }

    remaining = config.vehicle_count - sum(counts.values())

    ranked_routes = sorted(
        ROUTE_IDS,
        key=lambda route: raw[route] - counts[route],
        reverse=True,
    )

    for route in ranked_routes:
        if remaining == 0:
            break

        if counts[route] < config.route_capacity[route]:
            counts[route] += 1
            remaining -= 1

    validate_allocation(config, counts)

    return counts
