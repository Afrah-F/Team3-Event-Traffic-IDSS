"""Team 3 IDSS shared data contract. Python 3.10+; standard library only."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ROUTE_IDS = tuple(f"R{i}" for i in range(1, 9))
SCENARIOS = ("low", "medium", "high", "custom")
STATUSES = ("success", "invalid_input", "infeasible", "simulation_failed", "incomplete")


def _nonnegative_int(value: Any, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")


def validate_route_counts(counts: dict[str, int], *, label: str) -> None:
    if not isinstance(counts, dict) or set(counts) != set(ROUTE_IDS):
        raise ValueError(f"{label} must contain exactly R1 through R8")
    for route, count in counts.items():
        _nonnegative_int(count, f"{label}[{route}]")


@dataclass(frozen=True)
class SimulationConfig:
    scenario_id: Literal["low", "medium", "high", "custom"]
    vehicle_count: int
    route_capacity: dict[str, int]
    departure_window_s: float
    seed: int
    network_version: str

    def __post_init__(self) -> None:
        if self.scenario_id not in SCENARIOS:
            raise ValueError("Unknown scenario_id")
        _nonnegative_int(self.vehicle_count, "vehicle_count")
        if self.vehicle_count == 0:
            raise ValueError("vehicle_count must be positive")
        validate_route_counts(self.route_capacity, label="route_capacity")
        if type(self.departure_window_s) not in (int, float) or not (0 < self.departure_window_s < float("inf")):
            raise ValueError("departure_window_s must be positive and finite")
        _nonnegative_int(self.seed, "seed")
        if not isinstance(self.network_version, str) or not self.network_version.strip():
            raise ValueError("network_version must be a nonempty string")


def validate_allocation(config: SimulationConfig, allocation_counts: dict[str, int]) -> None:
    """Validate an allocation; capacity is vehicles per departure_window_s."""
    validate_route_counts(allocation_counts, label="allocation_counts")
    if sum(allocation_counts.values()) != config.vehicle_count:
        raise ValueError("Allocation total must equal vehicle_count")
    if sum(config.route_capacity.values()) < config.vehicle_count:
        raise ValueError("Total modeled route capacity is insufficient")
    for route in ROUTE_IDS:
        if allocation_counts[route] > config.route_capacity[route]:
            raise ValueError(f"Allocation exceeds capacity for {route}")


@dataclass
class SimulationResult:
    status: Literal["success", "invalid_input", "infeasible", "simulation_failed", "incomplete"]
    scenario_id: str
    run_id: str
    seed: int
    allocation_counts: dict[str, int]
    departed_vehicles: int = 0
    completed_vehicles: int = 0
    average_delay_s: float | None = None
    clearance_time_s: float | None = None
    average_travel_time_s: float | None = None
    mean_queue_vehicles: float | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_candidate(config: SimulationConfig, allocation_counts: dict[str, int], seed: int) -> SimulationResult:
    """Interface contract ONLY. Student 2 implements the actual SUMO/TraCI evaluator.

    No synthetic/fabricated metrics are returned by this placeholder.
    """
    raise NotImplementedError("Student 2 must implement SUMO-backed candidate evaluation")
