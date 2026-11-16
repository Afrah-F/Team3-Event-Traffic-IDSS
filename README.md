# Event Traffic Management IDSS

**ICS 487 – Intelligent Decision Support Systems | Team 3**

## Project Overview

This project develops an Intelligent Decision Support System (IDSS) to improve vehicle distribution across eight exit routes (R1–R8) following large stadium events.

The system uses SUMO traffic simulation, Python, TraCI, and Simulation-Based Hill Climbing to evaluate alternative traffic distributions and recommend solutions that minimize average vehicle delay.

The final decision remains with the traffic manager.

## Technologies

- Python – Decision logic and optimization
- SUMO – Traffic simulation
- TraCI – Python–SUMO integration
- Streamlit – Web dashboard
- Hill Climbing – Route allocation optimization

## Team Responsibilities

| Member | Responsibility |
|---|---|
| Student 1 | SUMO network, traffic generation, and baseline simulation |
| Student 2 | TraCI integration and Hill Climbing optimization |
| Student 3 | Knowledge Base, reasoning, explainability, and risk analysis |
| Student 4 | Streamlit dashboard, evaluation, and final report coordination |

## Shared Project Files

All team members must use the shared files before implementing their modules.

- `shared/schema.py` – Defines common data structures, validation rules, and simulation results.
- `config/scenarios.json` – Contains traffic scenarios and simulation assumptions.
- `docs/Team3_Parallel_Development_Task_Distribution_Plan_Updated.pdf` – Defines individual tasks, deliverables, and integration requirements.

The shared data structure should remain consistent across all modules. Scenario values may be updated after SUMO network testing and team approval.

## Development Workflow

1. Review the task distribution plan.
2. Use the agreed shared files.
3. Create a separate GitHub branch for each module.
4. Implement and test assigned tasks.
5. Submit a Pull Request for review.
6. Integrate all modules and perform system testing.

## Expected Deliverables

- Eight-route SUMO traffic simulation
- Working IDSS prototype
- Recommended vehicle distribution
- Baseline vs. IDSS evaluation
- Interactive Streamlit dashboard
- Final report and project presentation

  ## Expected Final System Interface

The following image is a conceptual preview of our proposed
Event Traffic Management IDSS dashboard.

![IDSS Dashboard Preview]([Event Traffic Management Dashboard.png](url))

## Project Status

**In Development**

The team is currently preparing the shared architecture and implementing individual modules.
