
# Student 2 — Optimization and TraCI Integration

## Implementation Status

Independent development and temporary-network testing completed.
Final stadium network integration is pending.

## Implemented Components

- Allocation validation and capacity constraints.
- Percentage-to-integer vehicle allocation.
- Simulation-Based Hill Climbing.
- Feasible neighbor generation.
- Average delay minimization.
- Clearance time tie-breaking.
- Candidate caching and stopping conditions.
- Python-SUMO integration using TraCI.
- Multiple evaluated distribution alternatives.
- JSON and CSV result export.
- Optimization search trace.

## Environment

- Python 3.12.10
- SUMO 1.28.0
- TraCI 1.28.0
- SUMOLib 1.28.0

## Dependencies

Install SUMO separately and configure SUMO_HOME and PATH.

Install Python dependencies:

    python -m pip install traci==1.28.0 sumolib==1.28.0

## Source Files

- optimization/constraints.py
- optimization/hill_climbing.py
- optimization/traci_runner.py
- optimization/export_results.py

## Testing

Run unit tests from the repository root:

    python -m unittest discover -s tests -p "test_*.py" -v

Run the SUMO connectivity test:

    python tests/sumo_smoke_test.py

Run real simulation-based optimization:

    python -m tests.real_optimization_test

Run the visual demonstration:

    python -m tests.visual_demo

## Verified Results

- 14 unit tests passed.
- SUMO and TraCI connectivity test passed.
- Real SUMO optimization test passed.
- 80 vehicles evaluated on a temporary eight-route network.
- 25 valid distribution alternatives generated.
- Export validation passed.

## Output Files

Located in results/optimization_test/:

- optimization_results.json
- alternatives.csv
- search_trace.json

Student 3 can use these outputs for reasoning and explanation.

Student 4 can use these outputs for dashboard development,
alternative comparison, and human decision selection.

## Integration Interface

The optimizer accepts a SUMO-backed evaluator created using:

    create_evaluator(network_path, route_edges)

The route mapping must contain R1 through R8.

The optimizer returns the recommended allocation,
evaluated alternatives, performance metrics, and search trace.

## Remaining Integration Tasks

- Connect Student 1's final SUMO network.
- Confirm route identifiers and edge mappings.
- Synchronize baseline and optimized departure generation.
- Verify final route capacities and demand assumptions.
- Preserve raw simulation evidence and experiment configurations.
- Test low, medium, and high demand scenarios.
- Integrate with the Knowledge Base and Streamlit dashboard.

## Limitations

Current results are real SUMO measurements from a temporary
test network, not the final stadium network.

Hill Climbing does not guarantee a global optimum.

The search stopped after reaching the configured evaluation budget.

The final traffic manager remains responsible for selecting
the preferred distribution.
