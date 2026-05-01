from cross_sector_intel_pipeline import run_pipeline


if __name__ == "__main__":
    result = run_pipeline()
    print("Cross-sector intelligence pipeline complete")
    print(f"Estimated avoided cost: ${result.get('estimated_avoided_cost_usd', 0.0):,.2f}")
