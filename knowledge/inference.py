
"""Forward-chaining inference engine: match -> fire -> add fact -> repeat."""
from shared.schema import SimulationConfig, SimulationResult
from knowledge.rules import RULES, collect_facts


def evaluate_facts(config: SimulationConfig, allocation_counts: dict,
                   result: SimulationResult | None = None) -> dict:
    # Working memory initially contains observed facts, not conclusions.
    memory = collect_facts(config, allocation_counts, result)
    fired = []
    trace = []

    # Iterate until no new rule can fire (forward chaining).
    while True:
        matches = [rule for rule in RULES
                   if rule.rule_id not in fired
                   and all(fact in memory for fact in rule.conditions)]
        if not matches:
            break
        # Meta-rule style conflict resolution: highest priority first.
        rule = sorted(matches, key=lambda r: (-r.priority, r.rule_id))[0]
        fired.append(rule.rule_id)
        memory.add(rule.conclusion)
        trace.append({"rule_id": rule.rule_id,
                      "if_facts": list(rule.conditions),
                      "then_fact": rule.conclusion,
                      "explanation": rule.explanation})

    # Conflict resolution: REJECT > REVIEW > ACCEPT.
    if "decision_reject" in memory:
        decision = "reject"
    elif "decision_review" in memory:
        decision = "review"
    elif "decision_accept" in memory:
        decision = "accept"
    else:
        decision = "review"

    return {"decision": decision,
            "fired_rule_ids": fired,
            "warnings": [step["explanation"] for step in trace
                         if step["rule_id"].startswith("R")],
            "inference_trace": trace,
            "working_memory": sorted(memory)}
