
"""Visual demonstration using the temporary test network."""

import subprocess
from pathlib import Path

from sumolib import checkBinary

from shared.schema import SimulationConfig, ROUTE_IDS

from tests.real_optimization_test import create_test_network

from optimization.traci_runner import generate_route_file


def main():

    folder = Path("results/visual_demo").resolve()
    folder.mkdir(parents=True, exist_ok=True)

    network, route_edges = create_test_network(folder)

    config = SimulationConfig(
        scenario_id="custom",
        vehicle_count=80,
        route_capacity={
            route: 40 for route in ROUTE_IDS
        },
        departure_window_s=30,
        seed=42,
        network_version="visual-test-network",
    )

    # Recommended allocation from the previous test.
    allocation = {
        "R1": 30,
        "R2": 10,
        "R3": 10,
        "R4": 5,
        "R5": 5,
        "R6": 10,
        "R7": 5,
        "R8": 5,
    }

    route_file = folder / "demo.rou.xml"

    generate_route_file(
        config,
        allocation,
        route_edges,
        route_file,
        config.seed,
    )

    config_file = folder / "demo.sumocfg"

    config_file.write_text(
        """<configuration>
    <input>
        <net-file value="test.net.xml"/>
        <route-files value="demo.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="1800"/>
        <step-length value="1"/>
    </time>
    <random_number>
        <seed value="42"/>
    </random_number>
    <processing>
        <time-to-teleport value="-1"/>
    </processing>
</configuration>""",
        encoding="utf-8",
    )

    print("Visual simulation files created.")
    print("Total vehicles:", sum(allocation.values()))
    print("Opening SUMO GUI...")

    subprocess.Popen([
        checkBinary("sumo-gui"),
        "-c", str(config_file),
        "--delay", "100",
    ])


if __name__ == "__main__":
    main()
