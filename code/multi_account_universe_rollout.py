import argparse
import csv
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONFIG = ROOT / "config"
OUT = ROOT / "out" / "execution"

ENV_FILE = CONFIG / "luma_live_keys.env"
UNIVERSE_FILE = ROOT / "out" / "live_universe_catalog.csv"
POLICY_FILE = CONFIG / "multi_account_policy.json"
GLOBAL_RUNTIME_FILE = CONFIG / "runtime_control.json"

REGISTRY_FILE = CONFIG / "live_account_registry.json"
ROLLOUT_FILE = OUT / "multi_account_rollout_plan.json"
CONSTRAINT_FILE = OUT / "multi_account_constraint_tags.json"
REMEDIATION_FILE = OUT / "multi_account_remediation.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def atomic_write_json(path: Path, payload: Any, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=indent)
    os.replace(tmp, path)


def parse_env(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            out[key] = value
    return out


def load_universe(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            symbol = str(r.get("symbol", "")).strip().upper()
            asset_class = str(r.get("asset_class", "unknown")).strip().lower()
            if symbol:
                rows.append({"symbol": symbol, "asset_class": asset_class})
    return rows


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-4:]}"


def _live_guard(policy: Dict[str, Any]) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    if not bool(policy.get("allow_live", False)):
        reasons.append("policy_allow_live_false")
        return False, reasons

    if bool(policy.get("require_env_arm", True)):
        env_var = str(policy.get("env_var", "LUMENCORE_ARM_MULTI_LIVE"))
        env_val = str(policy.get("env_value", "YES_ARM_MULTI_ACCOUNT_LIVE"))
        if os.environ.get(env_var, "") != env_val:
            reasons.append(f"env_guard_failed:{env_var}")

    if bool(policy.get("require_confirm_file", True)):
        confirm_file = ROOT / str(policy.get("confirm_file", "config/multi_live_arm.confirm"))
        phrase = str(policy.get("confirm_phrase", "ARM_MULTI_ACCOUNT_LIVE"))
        if not confirm_file.exists():
            reasons.append("confirm_file_missing")
        else:
            txt = confirm_file.read_text(encoding="utf-8", errors="ignore")
            if phrase not in txt:
                reasons.append("confirm_phrase_missing")

    return len(reasons) == 0, reasons


def discover_accounts(env: Dict[str, str]) -> List[Dict[str, Any]]:
    providers = {
        "KRAKEN": {"key": "KRAKEN_API_KEY", "secret": "KRAKEN_API_SECRET"},
        "ALPACA": {"key": "ALPACA_API_KEY", "secret": "ALPACA_API_SECRET"},
    }

    grouped: Dict[Tuple[str, str], Dict[str, Any]] = defaultdict(dict)

    for provider, pair in providers.items():
        key_base = pair["key"]
        sec_base = pair["secret"]

        for env_key, env_val in env.items():
            if env_key == key_base:
                grouped[(provider, "PRIMARY")]["api_key"] = env_val
            elif env_key == sec_base:
                grouped[(provider, "PRIMARY")]["api_secret"] = env_val
            elif env_key.startswith(f"{key_base}_"):
                suffix = env_key[len(key_base) + 1:]
                grouped[(provider, suffix)]["api_key"] = env_val
            elif env_key.startswith(f"{sec_base}_"):
                suffix = env_key[len(sec_base) + 1:]
                grouped[(provider, suffix)]["api_secret"] = env_val

    accounts: List[Dict[str, Any]] = []
    for (provider, suffix), creds in sorted(grouped.items(), key=lambda x: (x[0][0], x[0][1])):
        has_key = bool(creds.get("api_key"))
        has_secret = bool(creds.get("api_secret"))
        status = "ready" if has_key and has_secret else "partial"
        account_id = f"{provider}_{suffix}".upper()

        accounts.append(
            {
                "account_id": account_id,
                "provider": provider,
                "suffix": suffix,
                "status": status,
                "has_api_key": has_key,
                "has_api_secret": has_secret,
                "api_key_masked": _mask(str(creds.get("api_key", ""))),
                "api_secret_masked": _mask(str(creds.get("api_secret", ""))),
            }
        )

    return accounts


def build_account_plan(accounts: List[Dict[str, Any]], universe: List[Dict[str, str]], policy: Dict[str, Any], apply_live: bool) -> Dict[str, Any]:
    providers_cfg = policy.get("providers", {}) or {}
    allow_live, live_reasons = _live_guard(policy)
    global_runtime = read_json(GLOBAL_RUNTIME_FILE, {})
    global_live_armed = (
        str(global_runtime.get("mode", "paper")).strip().lower() == "live"
        and bool(global_runtime.get("allow_live_orders", False))
        and not bool(global_runtime.get("paper_enabled", True))
        and not bool(global_runtime.get("kill_switch", False))
    )
    if apply_live and not global_live_armed:
        live_reasons.append("global_runtime_not_live_armed")
        allow_live = False

    plan_accounts: List[Dict[str, Any]] = []
    constraints: List[Dict[str, Any]] = []
    remediation: List[Dict[str, Any]] = []

    for acc in accounts:
        provider = str(acc.get("provider", "")).upper()
        provider_cfg = providers_cfg.get(provider, {}) or {}
        supported = set(str(x).lower() for x in provider_cfg.get("supports_asset_classes", []))

        executable = [u["symbol"] for u in universe if u["asset_class"] in supported]
        shadow = [u["symbol"] for u in universe if u["asset_class"] not in supported]

        account_constraints: List[Dict[str, Any]] = []
        if acc.get("status") != "ready":
            account_constraints.append(
                {
                    "tag": "missing_credentials",
                    "severity": "high",
                    "where": acc["account_id"],
                    "why": "API key/secret pair incomplete",
                    "fix": "Provide both API key and API secret for account suffix",
                }
            )

        if not executable:
            account_constraints.append(
                {
                    "tag": "no_executable_universe",
                    "severity": "warn",
                    "where": acc["account_id"],
                    "why": "Provider supports none of the configured asset classes",
                    "fix": "Update provider capabilities or adjust universe mapping",
                }
            )

        if apply_live and not allow_live:
            account_constraints.append(
                {
                    "tag": "live_arming_blocked",
                    "severity": "high",
                    "where": acc["account_id"],
                    "why": "; ".join(live_reasons),
                    "fix": "Satisfy policy env/confirm guards before enabling live",
                }
            )

        constraints.extend(account_constraints)
        remediation.extend(account_constraints)

        safe_live = apply_live and allow_live and acc.get("status") == "ready"
        mode = "live" if safe_live else str(policy.get("default_mode", "paper"))

        runtime_patch = {
            "mode": mode,
            "allow_live_orders": bool(safe_live),
            "paper_enabled": not bool(safe_live),
            "kill_switch": bool(global_runtime.get("kill_switch", False)),
            "inherits_global_live_gate": True,
            "symbol": "UNIVERSE",
            "loop_seconds": float(policy.get("default_loop_seconds", 0.5)),
            "x1000_auto_enabled": bool(policy.get("x1000_auto_enabled", True)),
            "x1000_interval_loops": int(policy.get("x1000_interval_loops", 20)),
            "x1000_passes": int(policy.get("x1000_passes", 2)),
            "x1000_auto_apply": bool(policy.get("x1000_auto_apply", False)),
            "account_id": acc["account_id"],
            "account_provider": provider,
            "account_execution_mode": str(provider_cfg.get("execution_mode", "observer")),
            "universe_executable_count": len(executable),
            "universe_shadow_count": len(shadow),
        }

        plan_accounts.append(
            {
                "account": acc,
                "runtime_patch": runtime_patch,
                "strategy_sets": {
                    "executable_universe": executable,
                    "shadow_universe": shadow,
                    "evolution_profile": "x1000_two_pass_hybrid",
                },
                "constraints": account_constraints,
            }
        )

    return {
        "generated_utc": now_utc(),
        "allow_live_requested": apply_live,
        "allow_live_effective": allow_live and apply_live and global_live_armed,
        "global_live_armed": global_live_armed,
        "live_guard_reasons": live_reasons,
        "accounts_total": len(accounts),
        "accounts_ready": sum(1 for a in accounts if a.get("status") == "ready"),
        "universe_total": len(universe),
        "plan_accounts": plan_accounts,
        "constraints": constraints,
        "remediation": remediation,
    }


def apply_account_runtime_configs(plan: Dict[str, Any]) -> List[str]:
    written: List[str] = []
    for row in plan.get("plan_accounts", []):
        acc = row.get("account", {})
        runtime_patch = row.get("runtime_patch", {})
        account_id = str(acc.get("account_id", "UNKNOWN"))
        out_path = CONFIG / "accounts" / account_id / "runtime_control.json"
        atomic_write_json(out_path, runtime_patch, indent=2)
        written.append(str(out_path))
    return written


def run(apply: bool, arm_live: bool) -> int:
    env = parse_env(ENV_FILE)
    policy = read_json(POLICY_FILE, {})
    universe = load_universe(UNIVERSE_FILE)

    if not policy:
        print("[MULTI-ROLLOUT] missing policy file")
        return 1
    if not env:
        print("[MULTI-ROLLOUT] no env keys found")
        return 1
    if not universe:
        print("[MULTI-ROLLOUT] missing universe catalog")
        return 1

    accounts = discover_accounts(env)
    max_accounts = int(policy.get("max_accounts_to_activate", 50) or 50)
    accounts = accounts[:max_accounts]

    plan = build_account_plan(accounts, universe, policy, apply_live=arm_live)

    registry_payload = {
        "generated_utc": now_utc(),
        "accounts_total": len(accounts),
        "accounts": accounts,
        "source_env": str(ENV_FILE),
    }

    constraint_payload = {
        "generated_utc": now_utc(),
        "constraint_count": len(plan.get("constraints", [])),
        "constraints": plan.get("constraints", []),
    }

    remediation_payload = {
        "generated_utc": now_utc(),
        "when": now_utc(),
        "where": [x.get("where") for x in plan.get("remediation", [])],
        "why": [x.get("why") for x in plan.get("remediation", [])],
        "what": [x.get("tag") for x in plan.get("remediation", [])],
        "fix": [x.get("fix") for x in plan.get("remediation", [])],
        "entries": plan.get("remediation", []),
    }

    atomic_write_json(REGISTRY_FILE, registry_payload, indent=2)
    atomic_write_json(ROLLOUT_FILE, plan, indent=2)
    atomic_write_json(CONSTRAINT_FILE, constraint_payload, indent=2)
    atomic_write_json(REMEDIATION_FILE, remediation_payload, indent=2)

    written_files: List[str] = []
    if apply:
        written_files = apply_account_runtime_configs(plan)

    print("[MULTI-ROLLOUT] complete")
    print(f"  accounts_total: {len(accounts)} | ready: {sum(1 for a in accounts if a.get('status') == 'ready')}")
    print(f"  universe_total: {len(universe)}")
    print(f"  allow_live_requested: {arm_live} | allow_live_effective: {plan.get('allow_live_effective')}")
    print(f"  constraints: {len(plan.get('constraints', []))}")
    print(f"  registry: {REGISTRY_FILE}")
    print(f"  rollout_plan: {ROLLOUT_FILE}")
    print(f"  runtime_files_written: {len(written_files)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy full-universe strategy plans across all key-backed accounts")
    parser.add_argument("--apply", action="store_true", help="Write per-account runtime config files")
    parser.add_argument("--arm-live", action="store_true", help="Request live arming (still policy-gated)")
    args = parser.parse_args()
    return run(apply=args.apply, arm_live=args.arm_live)


if __name__ == "__main__":
    raise SystemExit(main())
