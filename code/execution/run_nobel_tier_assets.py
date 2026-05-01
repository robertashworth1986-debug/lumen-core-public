from build_nobel_tier_assets import run


if __name__ == "__main__":
    payload = run()
    headline = payload.get("headline", {}) if isinstance(payload, dict) else {}
    print("Nobel-tier assets generated")
    print(f"Projected failure cost: ${headline.get('projected_failure_cost_usd', 0.0):,.2f}")
    print(f"Estimated avoided cost: ${headline.get('estimated_avoided_cost_usd', 0.0):,.2f}")
