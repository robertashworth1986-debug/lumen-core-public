import json
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONFIG = ROOT / "config"
OUT = ROOT / "out" / "execution"


def _load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    registry = CONFIG / "live_account_registry.json"
    plan = OUT / "multi_account_rollout_plan.json"
    constraints = OUT / "multi_account_constraint_tags.json"
    remediation = OUT / "multi_account_remediation.json"

    required = [registry, plan, constraints, remediation]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        print("[MULTI-ROLLOUT-SMOKE] missing outputs")
        for m in missing:
            print(f"  - {m}")
        return 1

    r = _load(registry)
    p = _load(plan)
    c = _load(constraints)
    m = _load(remediation)

    miss_registry = [k for k in ["accounts_total", "accounts"] if k not in r]
    miss_plan = [k for k in ["accounts_total", "plan_accounts", "allow_live_effective"] if k not in p]
    miss_constraints = [k for k in ["constraint_count", "constraints"] if k not in c]
    miss_remediation = [k for k in ["when", "what", "fix"] if k not in m]

    if miss_registry or miss_plan or miss_constraints or miss_remediation:
        print("[MULTI-ROLLOUT-SMOKE] FAIL")
        print(f"  missing_registry: {miss_registry}")
        print(f"  missing_plan: {miss_plan}")
        print(f"  missing_constraints: {miss_constraints}")
        print(f"  missing_remediation: {miss_remediation}")
        return 2

    print("[MULTI-ROLLOUT-SMOKE] PASS")
    print(f"  accounts_total: {p.get('accounts_total')}")
    print(f"  accounts_ready: {p.get('accounts_ready')}")
    print(f"  universe_total: {p.get('universe_total')}")
    print(f"  allow_live_effective: {p.get('allow_live_effective')}")
    print(f"  constraints: {c.get('constraint_count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
