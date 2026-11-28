
"""Real SUMO/TraCI connectivity smoke test."""

import subprocess
import tempfile
from pathlib import Path

import traci
from sumolib import checkBinary


def main():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)

        nodes = root / "test.nod.xml"
        edges = root / "test.edg.xml"
        network = root / "test.net.xml"
        routes = root / "test.rou.xml"

        nodes.write_text(
            """<nodes>
    <node id="A" x="0" y="0"/>
    <node id="B" x="500" y="0"/>
</nodes>""",
            encoding="utf-8",
        )

        edges.write_text(
            """<edges>
    <edge id="road1" from="A" to="B"
          numLanes="1" speed="13.89"/>
</edges>""",
            encoding="utf-8",
        )

        subprocess.run(
            [
                checkBinary("netconvert"),
                "--node-files", str(nodes),
                "--edge-files", str(edges),
                "--output-file", str(network),
            ],
            check=True,
        )

        routes.write_text(
            """<routes>
    <route id="test_route" edges="road1"/>
    <vehicle id="car1" route="test_route" depart="0"/>
    <vehicle id="car2" route="test_route" depart="5"/>
    <vehicle id="car3" route="test_route" depart="10"/>
</routes>""",
            encoding="utf-8",
        )

        print("Starting SUMO...")

        traci.start([
            checkBinary("sumo"),
            "-n", str(network),
            "-r", str(routes),
            "--seed", "42",
            "--no-step-log", "true",
        ])

        departed = 0
        arrived = 0
        total_delay = 0.0
        steps = 0

        try:
            print("TraCI connection successful!")

            while traci.simulation.getMinExpectedNumber() > 0:
                if steps >= 1000:
                    raise RuntimeError("Simulation timeout")

                traci.simulationStep()
                steps += 1

                departed += (
                    traci.simulation.getDepartedNumber()
                )

                arrived += (
                    traci.simulation.getArrivedNumber()
                )

                for vehicle in traci.vehicle.getIDList():
                    total_delay += (
                        traci.vehicle.getWaitingTime(vehicle) > 0
                    )

            clearance_time = traci.simulation.getTime()

            print("\n===== REAL SUMO RESULTS =====")
            print("Departed vehicles:", departed)
            print("Completed vehicles:", arrived)
            print("Clearance time:", clearance_time, "seconds")
            print("Total sampled waiting:", total_delay, "vehicle-seconds")

            if departed != 3 or arrived != 3:
                raise RuntimeError("Incomplete simulation")

            print("\nSUMO + TraCI smoke test PASSED")

        finally:
            traci.close()


if __name__ == "__main__":
    main()
