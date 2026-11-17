
"""IF-THEN validation rules for the traffic IDSS."""

from shared.schema import ROUTE_IDS


def check_rules(config, allocation_counts):
    """
    Check a proposed traffic allocation.

    Returns rule IDs, warnings, and a decision.
    """
    fired_rules = []
    warnings = []

    # Rule R01: Demand must be positive.
    if config.vehicle_count <= 0:
        fired_rules.append("R01")
        warnings.append("Vehicle demand must be positive.")

    # Rule R02: All eight routes must be present.
    if not isinstance(allocation_counts, dict) or set(allocation_counts) != set(ROUTE_IDS):
        fired_rules.append("R02")
        warnings.append("Allocation must include R1 through R8.")

    else:
        # Rule R03: Route counts cannot be negative.
        if any(type(v) is not int or v < 0 for v in allocation_counts.values()):
            fired_rules.append("R03")
            warnings.append("Route counts must be nonnegative integers.")

        else:
            # Rule R04: Total allocation equals demand.
            if sum(allocation_counts.values()) != config.vehicle_count:
                fired_rules.append("R04")
                warnings.append("Allocation does not equal total demand.")

            # Rule R05: No route exceeds its capacity.
            for route in ROUTE_IDS:
                if allocation_counts[route] > config.route_capacity[route]:
                    fired_rules.append("R05")
                    warnings.append(f"{route} exceeds its capacity.")

    # Rule R06: Total capacity must be sufficient.
    if sum(config.route_capacity.values()) < config.vehicle_count:
        fired_rules.append("R06")
        warnings.append("Total route capacity is insufficient.")

    return {
        "fired_rule_ids": list(dict.fromkeys(fired_rules)),
        "warnings": warnings,
        "decision": "reject" if fired_rules else "accept"
    }
