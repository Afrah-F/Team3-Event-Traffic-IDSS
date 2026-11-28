
"""SUMO-backed candidate evaluation using TraCI."""

import tempfile
import uuid
import xml.etree.ElementTree as ET

from pathlib import Path
from functools import partial

import traci
from sumolib import checkBinary

from shared.schema import (
    ROUTE_IDS,
    SimulationConfig,
    SimulationResult,
    validate_allocation,
)


def generate_route_file(
    config,
    allocation_counts,
    route_edges,
    output_path,
    seed,
):
    """Generate exact vehicle assignments and departures."""

    import random

    validate_allocation(config, allocation_counts)

    if set(route_edges) != set(ROUTE_IDS):
        raise ValueError("Route mapping must contain R1-R8")

    root = ET.Element("routes")

    ET.SubElement(
        root,
        "vType",
        id="passenger_car",
        vClass="passenger",
    )

    for route in ROUTE_IDS:
        ET.SubElement(
            root,
            "route",
            id=route,
            edges=route_edges[route],
        )

    assignments = []

    for route in ROUTE_IDS:
        assignments.extend(
            [route] * allocation_counts[route]
        )

    random.Random(seed).shuffle(assignments)

    for index, route in enumerate(assignments):

        departure = (
            index * config.departure_window_s
            / config.vehicle_count
        )

        ET.SubElement(
            root,
            "vehicle",
            id=f"car_{index}",
            type="passenger_car",
            route=route,
            depart=f"{departure:.3f}",
            departLane="best",
        )

    ET.ElementTree(root).write(
        output_path,
        encoding="utf-8",
        xml_declaration=True,
    )


def evaluate_candidate(
    config: SimulationConfig,
    allocation_counts: dict[str, int],
    seed: int,
    *,
    network_path: str | Path,
    route_edges: dict[str, str],
    max_simulation_s: int = 14400,
) -> SimulationResult:
    """Evaluate one allocation using actual SUMO metrics."""

    result = SimulationResult(
        status="simulation_failed",
        scenario_id=config.scenario_id,
        run_id=uuid.uuid4().hex,
        seed=seed,
        allocation_counts=allocation_counts.copy(),
    )

    try:
        validate_allocation(
            config,
            allocation_counts,
        )
    except ValueError as error:
        result.status = "infeasible"
        result.warnings.append(str(error))
        return result

    network = Path(network_path).resolve()

    if not network.is_file():
        result.status = "invalid_input"
        result.warnings.append(
            f"Network file not found: {network}"
        )
        return result

    if set(route_edges) != set(ROUTE_IDS):
        result.status = "invalid_input"
        result.warnings.append(
            "Route mapping must contain R1-R8"
        )
        return result

    if max_simulation_s <= config.departure_window_s:
        result.status = "invalid_input"
        result.warnings.append(
            "Simulation limit must exceed departure window"
        )
        return result

    label = result.run_id

    try:
        with tempfile.TemporaryDirectory() as folder:

            root = Path(folder)

            route_file = root / "candidate.rou.xml"
            tripinfo_file = root / "tripinfo.xml"

            generate_route_file(
                config,
                allocation_counts,
                route_edges,
                route_file,
                seed,
            )

            command = [
                checkBinary("sumo"),
                "-n", str(network),
                "-r", str(route_file),
                "--seed", str(seed),
                "--step-length", "1",
                "--tripinfo-output", str(tripinfo_file),
                "--tripinfo-output.write-unfinished", "true",
                "--no-step-log", "true",
                "--time-to-teleport", "-1",
            ]

            connection = None
            queue_samples = []
            teleported = 0
            collisions = 0
            clearance_time = 0.0

            try:
                traci.start(
                    command,
                    label=label,
                )

                connection = traci.getConnection(label)

                edges = sorted({
                    edge
                    for path in route_edges.values()
                    for edge in path.split()
                })

                available_edges = set(
                    connection.edge.getIDList()
                )

                if not set(edges).issubset(available_edges):
                    raise ValueError(
                        "Route mapping contains unknown edges"
                    )

                while (
                    connection.simulation
                    .getMinExpectedNumber() > 0
                ):

                    if (
                        connection.simulation.getTime()
                        >= max_simulation_s
                    ):
                        break

                    connection.simulationStep()

                    result.departed_vehicles += (
                        connection.simulation
                        .getDepartedNumber()
                    )

                    arrived = (
                        connection.simulation
                        .getArrivedNumber()
                    )

                    result.completed_vehicles += arrived

                    if arrived > 0:
                        clearance_time = (
                            connection.simulation.getTime()
                        )

                    teleported += (
                        connection.simulation
                        .getStartingTeleportNumber()
                    )

                    collisions += (
                        connection.simulation
                        .getCollidingVehiclesNumber()
                    )

                    queue_samples.append(
                        sum(
                            connection.edge
                            .getLastStepHaltingNumber(edge)
                            for edge in edges
                        )
                    )

            finally:
                if connection is not None:
                    connection.close()

            if (
                result.completed_vehicles
                != config.vehicle_count
                or result.departed_vehicles
                != config.vehicle_count
            ):
                result.status = "incomplete"
                result.warnings.append(
                    "Not all assigned vehicles completed trips"
                )
                return result

            if teleported or collisions:
                result.status = "simulation_failed"
                result.warnings.append(
                    "Teleportation or collision detected"
                )
                return result

            if not tripinfo_file.exists():
                raise RuntimeError(
                    "SUMO tripinfo output is missing"
                )

            trips = ET.parse(
                tripinfo_file
            ).getroot().findall("tripinfo")

            if len(trips) != config.vehicle_count:
                result.status = "incomplete"
                result.warnings.append(
                    "Tripinfo record count mismatch"
                )
                return result

            if any(
                float(trip.attrib["arrival"]) < 0
                for trip in trips
            ):
                result.status = "incomplete"
                result.warnings.append(
                    "Unfinished trips detected"
                )
                return result

            result.average_delay_s = (
                sum(
                    float(trip.attrib["timeLoss"])
                    for trip in trips
                ) / len(trips)
            )

            result.average_travel_time_s = (
                sum(
                    float(trip.attrib["duration"])
                    for trip in trips
                ) / len(trips)
            )

            result.clearance_time_s = clearance_time

            result.mean_queue_vehicles = (
                sum(queue_samples) / len(queue_samples)
                if queue_samples else 0.0
            )

            result.status = "success"

    except Exception as error:
        result.status = "simulation_failed"
        result.warnings.append(str(error))

    return result


def create_evaluator(
    network_path,
    route_edges,
    max_simulation_s=14400,
):
    """Create an evaluator compatible with Hill Climbing."""

    return partial(
        evaluate_candidate,
        network_path=network_path,
        route_edges=route_edges.copy(),
        max_simulation_s=max_simulation_s,
    )
