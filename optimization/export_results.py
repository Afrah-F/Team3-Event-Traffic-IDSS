
"""Export optimization results for dashboard and evaluation."""

import csv
import json
from pathlib import Path

from shared.schema import ROUTE_IDS
from optimization.hill_climbing import OptimizationResult


def export_results(
    result: OptimizationResult,
    output_dir,
    *,
    network_version: str,
    data_source: str,
):
    """Export evaluated alternatives and optimization metadata."""

    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)

    alternatives = []

    for index, alternative in enumerate(
        result.alternatives, start=1
    ):
        row = alternative.to_dict()

        total = sum(
            alternative.allocation_counts.values()
        )

        row["alternative_id"] = f"Option_{index}"

        row["is_recommended"] = (
            alternative.allocation_counts
            == result.best_allocation
        )

        row["allocation_percentages"] = {
            route: (
                alternative.allocation_counts[route]
                / total * 100
            )
            for route in ROUTE_IDS
        }

        alternatives.append(row)

    payload = {
        "data_source": data_source,
        "network_version": network_version,
        "iterations": result.iterations,
        "evaluations": result.evaluations,
        "stop_reason": result.stop_reason,
        "best_allocation": result.best_allocation,
        "best_result": result.best_result.to_dict(),
        "alternatives": alternatives,
    }

    json_path = folder / "optimization_results.json"

    json_path.write_text(
        json.dumps(
            payload,
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    csv_path = folder / "alternatives.csv"

    fields = [
        "alternative_id",
        "is_recommended",
        "data_source",
        "network_version",
        "scenario_id",
        "run_id",
        "seed",
        "status",
        "departed_vehicles",
        "completed_vehicles",
        "average_delay_s",
        "clearance_time_s",
        "average_travel_time_s",
        "mean_queue_vehicles",
    ]

    fields += [
        f"{route}_count" for route in ROUTE_IDS
    ]

    fields += [
        f"{route}_percentage" for route in ROUTE_IDS
    ]

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields,
        )

        writer.writeheader()

        for alternative in alternatives:

            row = {
                key: alternative.get(key)
                for key in fields
            }

            row["data_source"] = data_source
            row["network_version"] = network_version

            for route in ROUTE_IDS:

                row[f"{route}_count"] = (
                    alternative["allocation_counts"][route]
                )

                row[f"{route}_percentage"] = round(
                    alternative[
                        "allocation_percentages"
                    ][route],
                    4,
                )

            writer.writerow(row)

    trace_path = folder / "search_trace.json"

    trace_path.write_text(
        json.dumps(
            result.search_trace,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Results exported successfully.")
    print("JSON:", json_path)
    print("CSV:", csv_path)
    print("Search trace:", trace_path)
    print("Alternatives:", len(alternatives))

    return json_path, csv_path, trace_path
