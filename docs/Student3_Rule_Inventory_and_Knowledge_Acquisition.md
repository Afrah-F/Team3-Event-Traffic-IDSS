# Student 3 — Rule Inventory and Knowledge-Acquisition Note

**Project:** Team 3 Event Traffic Intelligent Decision Support System (ICS 487)  
**Module:** Knowledge representation, inference, explainability, and risk  
**Branch:** `feature/knowledge`  
**Primary teaching reference:** Dr. Tarek Helmy, *Weeks 8–11: Knowledge Representation Methods* (production rules, working memory, forward chaining and meta-rules).  
**Project reference:** *Team3 Parallel Development Task Distribution Plan*, §6 (Student 3), and shared project files `shared/schema.py`, `config/scenarios.json`.

## 1. Rule inventory

The following inventory reflects the current **revised** `knowledge/rules.py`. In each production rule, all named conditions must be true before the conclusion is added to working memory. Priority values are implementation settings and are **not** traffic-engineering standards.

| Rule ID (priority) | IF condition / fact | THEN action / inferred fact | Source or assumption | Existing unit test / coverage |
|---|---|---|---|---|
| **R01 (100)** | `invalid_route_counts`: assignment does not have exactly R1–R8 or includes non-integer/negative counts | Add `invalid_candidate`; describe invalid route counts | `shared/schema.py`; shared contract §3.1 | `test_R01_missing_route`, `test_R01_negative_count` (**covered**) |
| **R02 (100)** | `allocation_total_wrong`: sum of assigned vehicles differs from requested demand | Add `invalid_candidate`; warn of incorrect total | `shared/schema.py`; §6 example rule | `test_R02_wrong_allocation_total` (**covered**) |
| **R03 (100)** | `insufficient_total_capacity`: sum of route capacities is below vehicle demand | Add `invalid_candidate`; warn of infeasible demand | `shared/schema.py`; §6 example rule; capacity values are preliminary | `test_R03_insufficient_total_capacity` (**covered**) |
| **R04 (100)** | `route_over_capacity`: any assigned route count exceeds capacity for the declared departure window | Add `invalid_candidate`; identify the capacity violation | `shared/schema.py`; §6 example rule; preliminary capacities | `test_rules_are_production_rules`, `test_capacity_violation_fact`, `test_R04_route_capacity_exceeded`, `test_conflicting_reject_and_review_reject_wins`, `test_meta_rules_and_conflict_resolution` (**covered**) |
| **R05 (50)** | `simulation_missing`: no `SimulationResult` is supplied | Add `unverified_result`; request evidence | Team task plan §6; evidence-based recommendation requirement | `test_missing_simulation_causes_review`, `test_R05_missing_simulation` (**covered**) |
| **R06 (50)** | `simulation_not_successful`: simulation `status` is not `success` | Add `unverified_result`; warn about failed/incomplete run | Team task plan §6; shared result status contract §3.3 | `test_R06_failed_simulation` (**covered**) |
| **R07 (50)** | `trips_incomplete`: completed vehicles are below requested number | Add `unverified_result`; suppress unsupported outcome claims | Team task plan §6 example rule | `test_incomplete_simulation_causes_review`, `test_R07_incomplete_trips` (**covered**) |
| **R08 (50)** | `metrics_missing`: average delay or clearance time is missing, negative, or otherwise invalid | Add `unverified_result`; warn that measurement evidence is inadequate | Team task plan §6; shared result metrics contract §3.3 | `test_R08_missing_metric`, `test_R08_invalid_metric` (**covered**) |
| **R09 (50)** | `result_mismatch`: result scenario, random seed, or assignment differs from the request | Add `unverified_result`; warn of inconsistent evidence | Team task plan §6; shared contract on repeatability and matching assignments | `test_R09_mismatched_scenario`, `test_R09_mismatched_seed` (**covered**; allocation mismatch not separately tested) |
| **R10 (50)** | `vehicle_counts_inconsistent`: departed counts differ from demand, completed exceed departed, or counts are not valid integers | Add `unverified_result`; flag inconsistent vehicle counts | Team task plan §6; shared result contract §3.3 | `test_R10_inconsistent_departed_count` (**covered**; completed > departed not separately tested) |
| **MR1 (100)** | Derived fact `invalid_candidate` is present | Add `decision_reject` | Meta-rule / conflict-resolution concept from Weeks 8–11; **reject-first order is a project design choice** | `test_conflicting_reject_and_review_reject_wins`, `test_meta_rules_and_conflict_resolution` (**covered**) |
| **MR2 (50)** | Derived fact `unverified_result` is present | Add `decision_review` | Meta-rule concept from Weeks 8–11; **human-review result is a project design choice** | `test_missing_simulation_causes_review`, `test_conflicting_reject_and_review_reject_wins`, `test_meta_rules_and_conflict_resolution` (**covered**) |
| **MR3 (10)** | Both `candidate_valid` and `simulation_reliable` are present | Add `decision_accept` | Team task plan acceptance conditions; meta-rule representation from Weeks 8–11 | `test_successful_simulation_causes_accept`, `test_MR3_only_with_valid_candidate_and_reliable_simulation` (**covered**) |

**Conflict-resolution policy:** The forward-chaining engine can fire multiple rules. The **final decision** uses `reject` before `review` before `accept`, even when both rejection and review facts are derived. The engine sorts available rules by descending priority (then rule ID) and retains fired IDs and the reasoning trace. These are explicit implementation decisions, not rules asserted by the professor.

**Test status:** The expanded local suite returned `Ran 28 tests — OK` (as confirmed in the VS Code terminal). Every listed production rule (R01–R10) and meta-rule (MR1–MR3) has at least one named test. Some branches within individual rules (for example, an allocation mismatch in R09 and completed-vehicle count exceeding departed count in R10) are not separately tested. Passing these unit tests does not yet establish end-to-end integration with the teammates’ SUMO, optimizer and dashboard modules.

## 2. Knowledge-acquisition note

### 2.1 Purpose and knowledge sources

This knowledge base supports traffic-allocation recommendations for a **synthetic eight-route stadium exit network**. It uses declarative IF–THEN **production rules** and forward-chaining inference as taught in *Weeks 8–11: Knowledge Representation Methods*. The lecture provides the **representation and reasoning method**, not real-world road capacity limits or traffic policy.

Domain knowledge was gathered from the team's agreed shared interface (`shared/schema.py`), the preliminary scenario assumptions (`config/scenarios.json`), and the Student 3 requirements in §6 of the team task-distribution plan. R01–R04 reflect feasibility constraints on route allocations and vehicle demand. R05–R10 reflect evidence and reliability checks required to avoid unsupported conclusions from missing, failed, inconsistent or incomplete simulation results. MR1–MR3 express a transparent priority policy for invalid versus unverified versus validated recommendations.

### 2.2 Why appropriate for this project

The eight-route model requires **count conservation** (all requested vehicles must be allocated), **nonnegative whole-vehicle assignments**, **capacity feasibility in the defined departure window**, and **reliable evidence from simulation**. Named production rules make these assumptions easy to inspect and explain. Working memory records observed facts; the inference engine matches and fires rules, produces derived conclusions, and returns rule IDs, warnings and an inference trace for the dashboard.

A result marked `accept` means only that the **defined programmatic checks** passed. It does **not** certify the traffic plan as optimal, physically safe, or applicable to real roads. Real effects on travel times and queues must come from verified SUMO runs.

### 2.3 Assumptions and limitations

- `R1`–`R8`, capacity values and departure-window settings belong to the synthetic network; **numerical assumptions require team approval** and are not field-calibrated values.
- The result schema does not fully establish that two runs used the same network version or departure profile; the team must verify comparability outside the present explanation function or extend the shared schema.
- `risk.py` performs **what-if sensitivity** checks, not probabilistic risk prediction. In particular, proportional scaling of capacity with departure-window length is an explicitly labeled modeling assumption requiring validation.
- Explainability is based on measured baseline and optimized outputs when available; a rule cannot prove that changing route use alone *caused* a delay improvement.
- Domain rules are project-specific; the professor's slides were used to select **production-rule representation, forward chaining, working memory, meta-rules and explanations**, not to assert empirical traffic standards.

## 3. Example explanation templates (also requested in team §6)

**Non-improving optimization:** “In comparable SUMO runs, the optimized candidate did not reduce average delay beyond the declared tolerance. The baseline allocation remains preferred unless the documented clearance-time tie-breaker supports the alternative. This statement relies on the measured run fields, not on route shifts alone.”

**Infeasible optimization:** “The proposed candidate was rejected because one or more route allocations exceed the assumed capacity or the total allocation violates the demand constraint. Reallocate or re-optimize vehicles and rerun the SUMO evaluation; do not report an unsupported performance improvement.”

**Unverified run:** “The candidate requires review because the simulation did not provide complete and consistent evidence. No improvement or operational-safety conclusion is made until the simulation result is validated.”

## 4. References used

1. Dr. Tarek Helmy, *ICS 487 — Weeks 8–11, Knowledge Representation Methods*: IF–THEN production rules, working memory, inference, forward chaining, and meta-rules.
2. Dr. Tarek Helmy, *ICS 487 — Weeks 4–6, Intelligent Agents*: knowledge, model, decision and human-oversight layers.
3. Team 3, *Parallel Development Task Distribution Plan — Updated*, §3 and §6: shared schema, Student 3 requirements, examples, and acceptance criteria.
4. Team repository: `shared/schema.py`, `config/scenarios.json`, `knowledge/rules.py`, `knowledge/inference.py`, `knowledge/explain.py`, `knowledge/risk.py`, `tests/test_knowledge.py`.
