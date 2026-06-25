from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

OUT_JSON = OUT_OPS / "field_money_truth_sweep_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "field_money_truth_sweep.json"
OUT_MD = DOCS / "FIELD_MONEY_TRUTH_SWEEP_2026-06-25.md"

GEOMETRY_REGISTRY = ROOT / "config" / "geometry_championship_v1_registry.json"
LIVE_HARVEST_JSON = OUT_OPS / "live_evidence_max_harvest_latest.json"
ROLLING_JSON = OUT_OPS / "rolling_champion_gate_latest.json"
PROOF_CARD_JSON = OUT_OPS / "geometry_proof_card_pack_latest.json"
CLAIM_MAP_JSON = OUT_OPS / "claim_strength_value_unlock_map_latest.json"
DOLLAR_GATE_JSON = OUT_OPS / "dollar_claim_gate_latest.json"
CONTROL_ROOM_JSON = OUT_OPS / "proof_to_pilot_control_room_latest.json"
VAULT_JSON = OUT_OPS / "external_proof_vault_manifest_latest.json"

STEPS: list[tuple[str, str, list[str], int]] = [
    ("geometry_registry_readiness", "code/geometry_championship_v1.py", [], 120),
    ("live_evidence_max_harvest", "code/ops/BUILD_LIVE_EVIDENCE_MAX_HARVEST.py", [], 420),
    ("geometry_championship_bridge", "code/ops/BUILD_GEOMETRY_CHAMPIONSHIP_BRIDGE.py", [], 180),
    ("geometry_champion_asset_map", "code/ops/BUILD_GEOMETRY_CHAMPION_ASSET_MAP.py", [], 180),
    ("geometry_proof_card_pack", "code/ops/BUILD_GEOMETRY_PROOF_CARD_PACK.py", [], 180),
    ("geometry_repeat_proof_validation", "code/ops/BUILD_GEOMETRY_REPEAT_PROOF_VALIDATION.py", [], 180),
    ("geometry_repeat_uncertainty_report", "code/ops/BUILD_GEOMETRY_REPEAT_UNCERTAINTY_REPORT.py", [], 180),
    ("geometry_field_validation_protocol", "code/ops/BUILD_GEOMETRY_FIELD_VALIDATION_PROTOCOL.py", [], 180),
    ("dollar_claim_gate", "code/ops/BUILD_DOLLAR_CLAIM_GATE.py", [], 180),
    ("proof_to_pilot_control_room", "code/ops/BUILD_PROOF_TO_PILOT_CONTROL_ROOM.py", [], 180),
    ("paid_pilot_outreach_queue", "code/ops/BUILD_PAID_PILOT_OUTREACH_QUEUE.py", [], 180),
    ("claim_strength_value_unlock_map", "code/ops/BUILD_CLAIM_STRENGTH_VALUE_UNLOCK_MAP.py", [], 180),
]

BOUNDARY = (
    "This sweep is a hard truth gate. It runs or reads the current live-evidence, geometry, proof, vault, and "
    "claim artifacts, then states which commercial claims are allowed. It does not turn field validation or "
    "real-dollar savings true unless buyer/agency-authorized field data, preregistered holdouts, named baselines, "
    "accepted economic conversion factors, and auditable result artifacts exist."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def tail(text: str | None, limit: int = 6000) -> str:
    return (text or "")[-limit:]


def run_step(
    label: str,
    rel_script: str,
    extra_args: list[str],
    timeout: int,
    env: dict[str, str],
) -> dict[str, Any]:
    script = ROOT / rel_script
    started = now_utc()
    if not script.exists():
        return {
            "label": label,
            "script": str(script),
            "ok": False,
            "return_code": None,
            "started_utc": started,
            "ended_utc": now_utc(),
            "stdout_tail": "",
            "stderr_tail": "script not found",
        }
    cmd = [sys.executable, str(script), *extra_args]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "label": label,
            "script": str(script),
            "ok": proc.returncode == 0,
            "return_code": proc.returncode,
            "started_utc": started,
            "ended_utc": now_utc(),
            "stdout_tail": tail(proc.stdout),
            "stderr_tail": tail(proc.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "label": label,
            "script": str(script),
            "ok": False,
            "return_code": None,
            "started_utc": started,
            "ended_utc": now_utc(),
            "stdout_tail": tail(exc.stdout if isinstance(exc.stdout, str) else ""),
            "stderr_tail": f"timeout after {timeout}s",
        }


def hydrate_env(extra_key_file: str = "") -> dict[str, str]:
    env = os.environ.copy()
    for rel_path in ("config/luma_live_keys.env", ".env.live", ".env.sports"):
        path = ROOT / rel_path
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and not env.get(key):
                env[key] = value
    if extra_key_file:
        env["LUMA_EXTRA_KEY_FILE"] = extra_key_file
    return env


def run_pipeline(skip_network: bool, stage_vault: bool, vault_root: str, extra_key_file: str) -> list[dict[str, Any]]:
    env = hydrate_env(extra_key_file)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results: list[dict[str, Any]] = []
    for label, rel_script, base_args, timeout in STEPS:
        args = list(base_args)
        if label == "geometry_registry_readiness":
            args.extend(["--run-tag", f"truth_sweep_{stamp}"])
        if label == "live_evidence_max_harvest":
            if skip_network:
                args.append("--skip-network")
            if extra_key_file:
                args.extend(["--extra-key-file", extra_key_file])
        results.append(run_step(label, rel_script, args, timeout, env))

    if stage_vault:
        target = vault_root or "E:/LumaProofVault"
        args = ["--target-root", target, "--package-name", f"LUMA_FIELD_MONEY_TRUTH_SWEEP_{stamp}"]
        results.append(run_step("stage_external_proof_vault", "code/ops/STAGE_EXTERNAL_PROOF_VAULT.py", args, 240, env))
    return results


def registry_counts() -> dict[str, Any]:
    registry = read_json(GEOMETRY_REGISTRY)
    families = registry.get("families", []) if isinstance(registry.get("families"), list) else []
    lanes = registry.get("lanes", {}) if isinstance(registry.get("lanes"), dict) else {}
    family_count = len([row for row in families if isinstance(row, dict)])
    benchmark_specified = sum(
        1
        for row in families
        if isinstance(row, dict)
        and row.get("benchmark_hypothesis")
        and row.get("promotion_metric")
        and row.get("failure_mode")
    )
    performance_ready = sum(1 for row in families if isinstance(row, dict) and row.get("status") in {"implemented", "validated"})
    return {
        "registered_family_count": family_count,
        "registered_lane_count": len(lanes),
        "benchmark_specified_family_count": benchmark_specified,
        "performance_ready_family_count": performance_ready,
    }


def summarize_artifacts() -> dict[str, Any]:
    live = read_json(LIVE_HARVEST_JSON)
    rolling = read_json(ROLLING_JSON)
    proof_cards = read_json(PROOF_CARD_JSON)
    claim_map = read_json(CLAIM_MAP_JSON)
    dollar_gate = read_json(DOLLAR_GATE_JSON)
    control_room = read_json(CONTROL_ROOM_JSON)
    vault = read_json(VAULT_JSON)
    live_summary = live.get("summary", {}) if isinstance(live.get("summary"), dict) else {}
    rolling_summary = rolling.get("summary", {}) if isinstance(rolling.get("summary"), dict) else {}
    proof_summary = proof_cards.get("summary", {}) if isinstance(proof_cards.get("summary"), dict) else {}
    claim_summary = claim_map.get("summary", {}) if isinstance(claim_map.get("summary"), dict) else {}
    dollar_summary = dollar_gate.get("summary", {}) if isinstance(dollar_gate.get("summary"), dict) else {}
    control_summary = control_room.get("summary", {}) if isinstance(control_room.get("summary"), dict) else {}
    vault_summary = vault.get("summary", {}) if isinstance(vault.get("summary"), dict) else {}

    return {
        **registry_counts(),
        "enabled_sources": live_summary.get("enabled_sources", 0),
        "measured_sources": live_summary.get("measured_sources", 0),
        "failed_or_thin_sources": live_summary.get("failed_or_thin_sources", 0),
        "total_measured_rows": live_summary.get("total_measured_rows", 0),
        "coverage_pct": live_summary.get("coverage_pct", 0),
        "top_live_replay_ready_count": live_summary.get("top_live_replay_ready_count", 0),
        "adapter_replay_count": live_summary.get("adapter_replay_count", 0),
        "candidate_beats_named_baseline_count": live_summary.get("candidate_beats_named_baseline_count", 0),
        "total_live_context_rows_evaluated": live_summary.get("total_live_context_rows_evaluated", 0),
        "unique_snapshot_sha256_count": live_summary.get("unique_snapshot_sha256_count", 0),
        "rolling_champion_count": rolling_summary.get("rolling_champion_count", 0),
        "triple_source_candidate_count": rolling_summary.get("triple_source_candidate_count", 0),
        "single_run_candidate_count": rolling_summary.get("single_run_candidate_count", 0),
        "proof_card_count": proof_summary.get("proof_card_count", len(proof_cards.get("proof_cards", []))),
        "robust_repeat_candidate_count": claim_summary.get("robust_repeat_candidate_count", control_summary.get("robust_candidate_count", 0)),
        "manual_paid_pilot_outreach_rows": claim_summary.get("manual_paid_pilot_outreach_rows", 0),
        "safe_estimated_hourly_value_usd": claim_summary.get(
            "safe_estimated_hourly_value_usd", dollar_summary.get("allowed_estimated_hourly_value_usd", 0)
        ),
        "safe_estimated_annual_value_usd": claim_summary.get(
            "safe_estimated_annual_value_usd", dollar_summary.get("allowed_estimated_annual_value_usd", 0)
        ),
        "blocked_context_annual_value_usd": claim_summary.get(
            "blocked_context_annual_value_usd", dollar_summary.get("blocked_context_only_annual_value_usd", 0)
        ),
        "vault_target_root": vault.get("target_root", ""),
        "vault_packet_dir": vault.get("packet_dir", ""),
        "vault_packet_ready": bool(vault_summary.get("packet_ready")),
        "vault_ready_count": vault_summary.get("ready_count", 0),
        "vault_artifact_count": vault_summary.get("artifact_count", 0),
        "vault_copied_count": vault.get("copy_result", {}).get("copied_count", 0)
        if isinstance(vault.get("copy_result"), dict)
        else 0,
        "vault_hashes_verified": bool(
            vault.get("copy_result", {}).get("all_copied_hashes_verified", False)
            if isinstance(vault.get("copy_result"), dict)
            else False
        ),
    }


def build_gates(summary: dict[str, Any]) -> dict[str, Any]:
    family_count = int(summary.get("registered_family_count", 0) or 0)
    adapter_replays = int(summary.get("adapter_replay_count", 0) or 0)
    benchmark_specified = int(summary.get("benchmark_specified_family_count", 0) or 0)
    rolling_champions = int(summary.get("rolling_champion_count", 0) or 0)
    triple_candidates = int(summary.get("triple_source_candidate_count", 0) or 0)
    measured_sources = int(summary.get("measured_sources", 0) or 0)
    live_rows = int(summary.get("total_measured_rows", 0) or 0)
    vault_target = str(summary.get("vault_target_root", "") or "").replace("\\", "/").lower()
    external_vault_target = vault_target.startswith("e:/") or vault_target.startswith("e:") or "lumaproofvault" in vault_target

    return {
        "registry_has_all_candidate_families": family_count >= 140,
        "all_families_have_benchmark_specs": family_count > 0 and benchmark_specified >= family_count,
        "all_registered_families_live_benchmarked": family_count > 0 and adapter_replays >= family_count,
        "live_data_available_for_benchmarking": measured_sources >= 3 and live_rows > 0,
        "double_dataset_frozen_assets_present": rolling_champions >= 1 or triple_candidates >= 1,
        "triple_dataset_frozen_assets_present": triple_candidates >= 1,
        "rolling_champion_present": rolling_champions >= 1,
        "glyph_or_external_vault_routed": external_vault_target
        and bool(summary.get("vault_packet_ready"))
        and bool(summary.get("vault_hashes_verified")),
        "vps_domain_live_dashboard_routed": False,
        "bounded_estimated_value_claim_allowed": float(summary.get("safe_estimated_annual_value_usd", 0) or 0) > 0,
        "paid_pilot_scoping_allowed": int(summary.get("manual_paid_pilot_outreach_rows", 0) or 0) > 0,
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
    }


def blockers(gates: dict[str, Any], summary: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    if not gates["all_registered_families_live_benchmarked"]:
        rows.append(
            "Only "
            f"{summary.get('adapter_replay_count', 0)} live adapter replay lanes are currently represented for "
            f"{summary.get('registered_family_count', 0)} registered families. This blocks all-family validation language."
        )
    if not gates["rolling_champion_present"]:
        rows.append("Rolling champion count is 0. Triple-source candidates exist, but repeat distinct-run champion status is not yet earned.")
    if not gates["glyph_or_external_vault_routed"]:
        rows.append("External/Glyph proof vault is not currently verified as staged with copied hashes in the latest manifest.")
    rows.append(
        "Field validation requires buyer or agency authorized operational data, preregistered holdouts, named incumbent baselines, accepted economic conversion factors, and auditable signed or traceable results."
    )
    rows.append("Real dollar savings require field validation plus accepted economics. Estimated value is allowed; realized savings is blocked.")
    rows.append("VPS/domain proof routing requires a verified deployed dashboard URL and fresh hosted artifact hashes; local dashboard JSON alone is not enough.")
    return rows


def build_payload(
    *,
    run_steps: bool = False,
    skip_network: bool = True,
    stage_vault: bool = False,
    vault_root: str = "E:/LumaProofVault",
    extra_key_file: str = "",
) -> dict[str, Any]:
    steps = run_pipeline(skip_network, stage_vault, vault_root, extra_key_file) if run_steps else []
    summary = summarize_artifacts()
    gates = build_gates(summary)
    payload = {
        "schema": "field_money_truth_sweep_v1",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "mode": {
            "run_steps": run_steps,
            "skip_network": skip_network,
            "stage_vault": stage_vault,
            "vault_root": vault_root,
        },
        "summary": summary,
        "gates": gates,
        "blockers": blockers(gates, summary),
        "allowed_claim_now": {
            "claim": "bounded estimated value signal plus paid pilot scoping",
            "estimated_hourly": money(summary.get("safe_estimated_hourly_value_usd")),
            "estimated_annual": money(summary.get("safe_estimated_annual_value_usd")),
            "language": "Use estimated, bounded, under-assumptions language only.",
        },
        "blocked_claim_now": {
            "field_validated": False,
            "real_dollar_savings": False,
            "fixed_delta_price": False,
            "context_only_annual_value_surface": money(summary.get("blocked_context_annual_value_usd")),
        },
        "next_commands": {
            "fresh_live_and_stage_vault": (
                "pwsh -ExecutionPolicy Bypass -File .\\tools\\Run-FieldMoneyTruthSweep.ps1 "
                "-FreshLivePull -StageGlyphVault"
            ),
            "reuse_existing_snapshots_fast": (
                "pwsh -ExecutionPolicy Bypass -File .\\tools\\Run-FieldMoneyTruthSweep.ps1 "
                "-StageGlyphVault"
            ),
        },
        "steps": steps,
    }
    payload["truth_sweep_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "gates": payload["gates"],
            "allowed_claim_now": payload["allowed_claim_now"],
            "blocked_claim_now": payload["blocked_claim_now"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    gates = payload["gates"]
    lines = [
        "# Field Money Truth Sweep",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["boundary"],
        "",
        "## Current Truth",
        "",
        f"- Registered families: `{summary.get('registered_family_count')}`",
        f"- Live adapter replay count: `{summary.get('adapter_replay_count')}`",
        f"- Measured sources / rows: `{summary.get('measured_sources')}` / `{summary.get('total_measured_rows')}`",
        f"- Candidate beats named baseline count: `{summary.get('candidate_beats_named_baseline_count')}`",
        f"- Triple-source candidates: `{summary.get('triple_source_candidate_count')}`",
        f"- Rolling champions: `{summary.get('rolling_champion_count')}`",
        f"- Safe estimated value signal: `{money(summary.get('safe_estimated_hourly_value_usd'))}/hour`, `{money(summary.get('safe_estimated_annual_value_usd'))}/year`",
        f"- Blocked context-only value surface: `{money(summary.get('blocked_context_annual_value_usd'))}/year`",
        "",
        "## Gates",
        "",
    ]
    for key, value in gates.items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend(["", "## Allowed Claim Now", ""])
    lines.append(
        f"{payload['allowed_claim_now']['claim']}: {payload['allowed_claim_now']['estimated_hourly']} / "
        f"{payload['allowed_claim_now']['estimated_annual']} under stated assumptions."
    )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {item}" for item in payload["blockers"])
    lines.extend(["", "## Commands", ""])
    lines.append("Fresh live pull and vault stage:")
    lines.append("")
    lines.append(f"```powershell\n{payload['next_commands']['fresh_live_and_stage_vault']}\n```")
    lines.append("Fast run using existing snapshots:")
    lines.append("")
    lines.append(f"```powershell\n{payload['next_commands']['reuse_existing_snapshots_fast']}\n```")
    if payload["steps"]:
        lines.extend(["", "## Step Results", ""])
        for step in payload["steps"]:
            lines.append(f"- `{step['label']}`: ok `{str(step['ok']).lower()}`, return `{step['return_code']}`")
    lines.extend(["", f"Truth-sweep hash: `{payload['truth_sweep_sha256']}`"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run/read the Luma field-money truth gate.")
    parser.add_argument("--run-pipeline", action="store_true")
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("--stage-vault", action="store_true")
    parser.add_argument("--vault-root", default="E:/LumaProofVault")
    parser.add_argument("--extra-key-file", default="")
    args = parser.parse_args()

    payload = build_payload(
        run_steps=args.run_pipeline,
        skip_network=args.skip_network,
        stage_vault=args.stage_vault,
        vault_root=args.vault_root,
        extra_key_file=args.extra_key_file,
    )
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(json.dumps({"gates": payload["gates"], "truth_sweep_sha256": payload["truth_sweep_sha256"]}, indent=2))
    return 0 if all(step.get("ok", True) for step in payload["steps"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
