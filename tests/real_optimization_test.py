
"""Real SUMO optimization test using a temporary network."""

import subprocess
import tempfile
import xml.etree.ElementTree as ET

from pathlib import Path
from math import cos, sin, pi

from sumolib import checkBinary

from shared.schema import (
    ROUTE_IDS,
    SimulationConfig,
)

from optimization.constraints import is_feasible
from optimization.hill_climbing import hill_climbing
from optimization.traci_runner import create_evaluator
from optimization.export_results import export_results


def create_test_network(folder):
    """Create eight temporary routes with different characteristics."""

    root = Path(folder)

    nodes_file = root / "test.nod.xml"
    edges_file = root / "test.edg.xml"
    network_file = root / "test.net.xml"

    nodes = ET.Element("nodes")
    edges = ET.Element("edges")

    route_edges = {}

    for index, route in enumerate(ROUTE_IDS):

        angle = index * 2 * pi / 8

        start = f"start_{route}"
        end = f"end_{route}"
        edge = f"road_{route}"

        length = 500 + index * 100

        ET.SubElement(
            nodes,
            "node",
            id=start,
            x=str(100 * cos(angle)),
            y=str(100 * sin(angle)),
        )

        ET.SubElement(
            nodes,
            "node",
            id=end,
            x=str((100 + length) * cos(angle)),
            y=str((100 + length) * sin(angle)),
        )

        ET.SubElement(
            edges,
            "edge",
            id=edge,
            **{
                "from": start,
                "to": end,
                "numLanes": str(1 if index < 4 else 2),
                "speed": str(10 + index * 2),
            },
        )

        route_edges[route] = edge

    ET.ElementTree(nodes).write(
        nodes_file,
        encoding="utf-8",
        xml_declaration=True,
    )

    ET.ElementTree(edges).write(
        edges_file,
        encoding="utf-8",
        xml_declaration=True,
    )

    subprocess.run(
        [
            checkBinary("netconvert"),
            "--node-files", str(nodes_file),
            "--edge-files", str(edges_file),
            "--output-file", str(network_file),
        ],
        check=True,
    )

    return network_file, route_edges


def main():

    with tempfile.TemporaryDirectory() as folder:

        network, route_edges = create_test_network(folder)

        config = SimulationConfig(
            scenario_id="custom",
            vehicle_count=80,
            route_capacity={
                route: 40 for route in ROUTE_IDS
            },
            departure_window_s=30,
            seed=42,
            network_version="temporary-test-network",
        )

        initial = {
            "R1": 30,
            "R2": 15,
            "R3": 10,
            "R4": 5,
            "R5": 5,
            "R6": 5,
            "R7": 5,
            "R8": 5,
        }

        evaluator = create_evaluator(
            network_path=network,
            route_edges=route_edges,
            max_simulation_s=1800,
        )

        print("\n===== INITIAL SIMULATION =====")

        baseline = evaluator(
            config,
            initial,
            config.seed,
        )

        print("Status:", baseline.status)
        print("Completed:", baseline.completed_vehicles)
        print("Average delay:", baseline.average_delay_s)
        print("Clearance time:", baseline.clearance_time_s)
        print("Warnings:", baseline.warnings)

        assert baseline.status == "success", baseline.warnings

        print("\n===== RUNNING HILL CLIMBING =====")

        result = hill_climbing(
            config=config,
            evaluator=evaluator,
            initial_allocation=initial,
            step_size=5,
            max_iterations=3,
            max_evaluations=25,
        )

        print("\n===== OPTIMIZATION RESULTS =====")

        print(
            "Initial delay:",
            baseline.average_delay_s,
        )

        print(
            "Recommended delay:",
            result.best_result.average_delay_s,
        )

        print(
            "Initial clearance:",
            baseline.clearance_time_s,
        )

        print(
            "Recommended clearance:",
            result.best_result.clearance_time_s,
        )

        print("Iterations:", result.iterations)
        print("Evaluations:", result.evaluations)
        print("Stop reason:", result.stop_reason)

        print("\nRecommended distribution:")

        for route, count in result.best_allocation.items():

            percentage = (
                count / config.vehicle_count * 100
            )

            print(
                f"{route}: {count} cars "
                f"({percentage:.2f}%)"
            )

        print(
            "\nValid alternatives:",
            len(result.alternatives),
        )

        assert is_feasible(
            config,
            result.best_allocation,
        )

        assert result.best_result.status == "success"

        assert (
            result.best_result.completed_vehicles
            == config.vehicle_count
        )

        assert len(result.alternatives) > 1

        assert result.evaluations <= 25

        assert (
            result.best_result.average_delay_s
            <= baseline.average_delay_s + 0.01
        )

        print("\nREAL SUMO OPTIMIZATION TEST PASSED")

        print("\n===== EXPORTING RESULTS =====")

        export_results(
            result,
            "results/optimization_test",
            network_version=config.network_version,
            data_source="REAL SUMO - TEMPORARY TEST NETWORK",
        )

        print("\nEXPORT COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()
