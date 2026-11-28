
"""Simulation-based Hill Climbing optimization."""

from dataclasses import dataclass, field
from typing import Callable
from math import isfinite

from shared.schema import (
    ROUTE_IDS,
    SimulationConfig,
    SimulationResult,
)

from optimization.constraints import (
    is_feasible,
    create_initial_allocation,
)


Evaluator = Callable[
    [SimulationConfig, dict[str, int], int],
    SimulationResult,
]


@dataclass
class OptimizationResult:
    best_allocation: dict[str, int]
    best_result: SimulationResult
    alternatives: list[SimulationResult]
    iterations: int
    evaluations: int
    stop_reason: str
    search_trace: list[dict] = field(default_factory=list)


def generate_neighbors(
    config: SimulationConfig,
    allocation: dict[str, int],
    step_size: int = 10,
) -> list[dict[str, int]]:
    """Generate feasible neighboring allocations."""

    if type(step_size) is not int or step_size <= 0:
        raise ValueError("Step size must be a positive integer")

    neighbors = []

    for source in ROUTE_IDS:
        for destination in ROUTE_IDS:

            if source == destination:
                continue

            if allocation[source] < step_size:
                continue

            candidate = allocation.copy()

            candidate[source] -= step_size
            candidate[destination] += step_size

            if is_feasible(config, candidate):
                neighbors.append(candidate)

    return neighbors


def is_valid_result(
    result: SimulationResult,
    config: SimulationConfig,
) -> bool:
    """Check whether simulation results can be compared."""

    if result.status != "success":
        return False

    if result.completed_vehicles != config.vehicle_count:
        return False

    if result.departed_vehicles != config.vehicle_count:
        return False

    if result.scenario_id != config.scenario_id:
        return False

    if not is_feasible(config, result.allocation_counts):
        return False

    metrics = (
        result.average_delay_s,
        result.clearance_time_s,
        result.average_travel_time_s,
        result.mean_queue_vehicles,
    )

    return all(
        type(value) in (int, float)
        and isfinite(value)
        and value >= 0
        for value in metrics
    )


def is_better(
    candidate: SimulationResult,
    current: SimulationResult,
    tolerance: float = 0.01,
) -> bool:
    """Compare delay first, then clearance time."""

    difference = (
        current.average_delay_s
        - candidate.average_delay_s
    )

    if difference > tolerance:
        return True

    if abs(difference) <= tolerance:
        return (
            candidate.clearance_time_s
            < current.clearance_time_s
        )

    return False


def hill_climbing(
    config: SimulationConfig,
    evaluator: Evaluator,
    initial_allocation: dict[str, int] | None = None,
    step_size: int = 10,
    max_iterations: int = 20,
    max_evaluations: int = 200,
    tolerance: float = 0.01,
) -> OptimizationResult:
    """Find an improved feasible vehicle distribution."""

    if type(step_size) is not int or step_size <= 0:
        raise ValueError("Invalid step size")

    if type(max_iterations) is not int or max_iterations < 0:
        raise ValueError("Invalid iteration limit")

    if type(max_evaluations) is not int or max_evaluations < 1:
        raise ValueError("Invalid evaluation limit")

    if not isfinite(tolerance) or tolerance < 0:
        raise ValueError("Invalid tolerance")

    current = (
        create_initial_allocation(config)
        if initial_allocation is None
        else initial_allocation.copy()
    )

    if not is_feasible(config, current):
        raise ValueError("Initial allocation is infeasible")

    cache = {}
    alternatives = []
    search_trace = []
    visited = set()

    evaluations = 0
    iterations = 0

    def allocation_key(allocation):
        return tuple(
            allocation[route] for route in ROUTE_IDS
        )

    def evaluate(allocation):
        nonlocal evaluations

        key = allocation_key(allocation)

        if key in cache:
            return cache[key]

        if evaluations >= max_evaluations:
            return None

        evaluations += 1

        try:
            result = evaluator(
                config,
                allocation.copy(),
                config.seed,
            )
        except Exception as error:
            result = SimulationResult(
                status="simulation_failed",
                scenario_id=config.scenario_id,
                run_id=f"failed-{evaluations}",
                seed=config.seed,
                allocation_counts=allocation.copy(),
                warnings=[str(error)],
            )

        valid = (
            is_valid_result(result, config)
            and result.allocation_counts == allocation
            and result.seed == config.seed
        )

        search_trace.append({
            "evaluation": evaluations,
            "allocation": allocation.copy(),
            "status": result.status,
            "average_delay_s": result.average_delay_s,
            "clearance_time_s": result.clearance_time_s,
            "valid": valid,
        })

        if valid:
            alternatives.append(result)
            cache[key] = result
        else:
            cache[key] = None

        return cache[key]

    current_result = evaluate(current)

    if current_result is None:
        raise RuntimeError(
            "Initial simulation did not produce valid results"
        )

    visited.add(allocation_key(current))

    stop_reason = "Maximum iterations reached"

    while iterations < max_iterations:

        if evaluations >= max_evaluations:
            stop_reason = "Evaluation budget exhausted"
            break

        neighbors = generate_neighbors(
            config,
            current,
            step_size,
        )

        best_neighbor = None
        best_neighbor_result = current_result

        for candidate in neighbors:

            if allocation_key(candidate) in visited:
                continue

            result = evaluate(candidate)

            if result is None:
                continue

            if is_better(
                result,
                best_neighbor_result,
                tolerance,
            ):
                best_neighbor = candidate
                best_neighbor_result = result

        if best_neighbor is None:
            stop_reason = (
                "Evaluation budget exhausted"
                if evaluations >= max_evaluations
                else "No improving feasible neighbor"
            )
            break

        current = best_neighbor.copy()
        current_result = best_neighbor_result

        visited.add(allocation_key(current))
        iterations += 1

        search_trace.append({
            "event": "accepted_move",
            "iteration": iterations,
            "allocation": current.copy(),
            "average_delay_s": current_result.average_delay_s,
            "clearance_time_s": current_result.clearance_time_s,
        })

    # Rank all valid alternatives by the primary objective.
    ranked_alternatives = sorted(
        alternatives,
        key=lambda result: (
            result.average_delay_s,
            result.clearance_time_s,
        ),
    )

    # Apply the tie-breaker relative to the lowest measured delay.
    minimum_delay = ranked_alternatives[0].average_delay_s

    tied_results = [
        result
        for result in ranked_alternatives
        if result.average_delay_s <= minimum_delay + tolerance
    ]

    recommended = min(
        tied_results,
        key=lambda result: (
            result.clearance_time_s,
            result.average_delay_s,
        ),
    )

    return OptimizationResult(
        best_allocation=recommended.allocation_counts.copy(),
        best_result=recommended,
        alternatives=ranked_alternatives,
        iterations=iterations,
        evaluations=evaluations,
        stop_reason=stop_reason,
        search_trace=search_trace,
    )
