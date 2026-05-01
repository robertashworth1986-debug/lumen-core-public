from federal_brief_builder import run


if __name__ == "__main__":
    payload = run()
    impact = payload.get("financial_impact", {}) if isinstance(payload, dict) else {}
    print("Federal brief generated")
    print(f"Projected failure cost: ${impact.get('projected_failure_cost_usd', 0.0):,.2f}")
    print(f"Estimated avoided cost: ${impact.get('estimated_avoided_cost_usd', 0.0):,.2f}")
