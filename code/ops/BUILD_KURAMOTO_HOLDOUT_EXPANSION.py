from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

READY_REPLAY_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_READY_SOURCE_REPLAY.py"
TOP_REPLAY_SCRIPT = ROOT / "code" / "ops" / "BUILD_TOP_GEOMETRY_LIVE_REPLAY_RESULTS.py"
MANIFEST_JSON = OUT_OPS / "geometry_live_source_manifest_latest.json"

OUT_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "kuramoto_holdout_expansion.json"
OUT_MD = DOCS / "KURAMOTO_HOLDOUT_EXPANSION_2026-06-26.md"

CANDIDATE = "kuramoto_phase_coupling"
NAMED_BASELINE = "kalman_filter"
LANE = "wave_resonance_timing"

EVIDENCE_BOUNDARY = (
    "Kuramoto holdout expansion is internal source-conditioned replay evidence. It uses local/uploaded measured "
    "source files from the geometry live-source manifest to derive deterministic benchmark stress profiles, then "
    "compares kuramoto_phase_coupling against kalman_filter and the best same-run baseline under the existing "
    "wave-resonance timing adapter. It is not field validation, not grid/RF/PLL hardware validation, not realized "
    "savings, not a fixed-dollar frozen-delta sale claim, not medical treatment evidence, and not a trading signal."
)

SOURCE_SYSTEM_PRIORITY = {
    "energy_grid": 0,
    "weather": 1,
    "rates": 2,
    "labor": 3,
    "air_quality": 4,
    "water_hydrology": 5,
    "space_weather": 6,
    "market_data": 7,
}

FORBIDDEN_TERMS = (
    "guaranteed",
    "undeniable",
    "money printer",
    "live_order_placement",
    "realized savings claim allowed",
    "heroin-like",
)

PRIVATE_PATH_PATTERN = re.compile(r"(?i)(?:(?<![a-z0-9+.-])[a-z]:[\\/]|/(?:users|home)/)")
_TRACKED_PATH_CACHE: dict[str, bool] = {}
SOURCE_HASH_MAX_BYTES = 2_000_000


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ready_replay_module():
    return load_module(READY_REPLAY_SCRIPT, "geometry_ready_replay_for_kuramoto_holdout")


def top_replay_module():
    return load_module(TOP_REPLAY_SCRIPT, "top_geometry_replay_for_kuramoto_holdout")


def resolve_path(ready: Any, source_path: str) -> Path:
    try:
        return ready.resolve_source_path(source_path)
    except Exception:
        path = Path(source_path)
        return path if path.is_absolute() else ROOT / source_path


def source_sha256(ready: Any, source_path: str) -> str:
    path = resolve_path(ready, source_path)
    if path.is_file():
        try:
            return ready.file_sha256(path, max_bytes=SOURCE_HASH_MAX_BYTES)
        except Exception:
            pass
    return ""


def path_within_repository(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
    except (OSError, ValueError):
        return False
    return True


def git_tracked_source(path: Path) -> bool:
    if not path_within_repository(path):
        return False
    relative = str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    if relative in _TRACKED_PATH_CACHE:
        return _TRACKED_PATH_CACHE[relative]
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "--", relative],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        tracked = result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        tracked = False
    _TRACKED_PATH_CACHE[relative] = tracked
    return tracked


def public_source_ref(source_system: str, source_hash: str, rank: int) -> str:
    digest = source_hash[:16] if source_hash else "unavailable"
    system = re.sub(r"[^a-z0-9_-]+", "-", source_system.lower()).strip("-") or "unknown"
    return f"source://{system}/{rank:03d}-{digest}"


def select_wave_routes(manifest: dict[str, Any], *, max_routes: int) -> list[dict[str, Any]]:
    rows = [
        row
        for row in manifest.get("manifest_rows", [])
        if isinstance(row, dict)
        and row.get("ready_for_benchmark")
        and row.get("lane") == LANE
        and row.get("candidate_family") == CANDIDATE
        and row.get("baseline_family") == NAMED_BASELINE
        and row.get("source_path")
    ]
    rows.sort(
        key=lambda row: (
            SOURCE_SYSTEM_PRIORITY.get(str(row.get("system", "")), 99),
            -safe_int(row.get("estimated_rows")),
            str(row.get("source_path", "")),
        )
    )

    selected: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    seen_systems: set[str] = set()

    for row in rows:
        if len(selected) >= max_routes:
            break
        source_path = str(row.get("source_path", ""))
        system = str(row.get("system", ""))
        if source_path in seen_paths or system in seen_systems:
            continue
        selected.append(dict(row))
        seen_paths.add(source_path)
        seen_systems.add(system)

    for row in rows:
        if len(selected) >= max_routes:
            break
        source_path = str(row.get("source_path", ""))
        if source_path in seen_paths:
            continue
        selected.append(dict(row))
        seen_paths.add(source_path)

    for rank, row in enumerate(selected, start=1):
        row["holdout_rank"] = rank
    return selected


def find_row(replay: Any, leaderboard: list[dict[str, Any]], family_id: str) -> dict[str, Any]:
    try:
        return replay.find_leaderboard_row(leaderboard, family_id)
    except Exception:
        for row in leaderboard:
            if row.get("family_id") == family_id or row.get("strategy") == family_id:
                return row
        return {}


def row_score(replay: Any, row: dict[str, Any]) -> float:
    try:
        return float(replay.score_value(row))
    except Exception:
        return safe_float(row.get("mean_score", row.get("score", 0.0)))


def baseline_rows(leaderboard: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in leaderboard if row.get("kind") == "baseline"]


def replay_holdout_route(route: dict[str, Any], ready: Any, replay: Any, *, sample_limit: int) -> dict[str, Any]:
    source_path = str(route.get("source_path", ""))
    resolved_source = resolve_path(ready, source_path)
    source_available = resolved_source.is_file()
    try:
        source_size_bytes = resolved_source.stat().st_size if source_available else 0
    except OSError:
        source_size_bytes = 0
    source_hash = source_sha256(ready, source_path)
    profile = ready.source_profile(route, sample_limit=sample_limit)
    adapter = replay.run_lane_adapter(LANE, [profile])
    leaderboard = adapter.get("leaderboard", []) if isinstance(adapter.get("leaderboard"), list) else []
    candidate_row = find_row(replay, leaderboard, CANDIDATE)
    kalman_row = find_row(replay, leaderboard, NAMED_BASELINE)
    best_baseline = baseline_rows(leaderboard)[0] if baseline_rows(leaderboard) else {}
    best_overall = leaderboard[0] if leaderboard else {}

    candidate_score = row_score(replay, candidate_row) if candidate_row else 0.0
    kalman_score = row_score(replay, kalman_row) if kalman_row else 0.0
    best_baseline_score = row_score(replay, best_baseline) if best_baseline else 0.0

    delta_vs_kalman = round(candidate_score - kalman_score, 6) if candidate_row and kalman_row else None
    delta_vs_best_baseline = round(candidate_score - best_baseline_score, 6) if candidate_row and best_baseline else None

    rank = safe_int(route.get("holdout_rank"))
    source_system = str(route.get("system", ""))
    source_ref = public_source_ref(source_system, source_hash, rank)
    fallback_used = bool(profile.get("fallback_used"))
    numeric_samples = safe_int(profile.get("numeric_count"))
    evidence_eligible = bool(source_available and source_hash and numeric_samples > 0 and not fallback_used)
    result = {
        "rank": rank,
        "lane": LANE,
        "candidate_family": CANDIDATE,
        "named_baseline": NAMED_BASELINE,
        "source_path": source_path,
        "source_ref": source_ref,
        "source_system": source_system,
        "source_sha256": source_hash,
        "source_sha256_scope_bytes": min(source_size_bytes, SOURCE_HASH_MAX_BYTES),
        "source_sha256_is_full_file": bool(source_available and source_size_bytes <= SOURCE_HASH_MAX_BYTES),
        "source_size_bytes": source_size_bytes,
        "source_available": source_available,
        "source_within_repository": path_within_repository(resolved_source),
        "source_git_tracked": source_available and git_tracked_source(resolved_source),
        "source_path_publication_allowed": False,
        "estimated_rows": safe_int(route.get("estimated_rows")),
        "profile": profile,
        "numeric_samples": numeric_samples,
        "fallback_used": fallback_used,
        "evidence_eligible": evidence_eligible,
        "adapter_status": adapter.get("adapter_status", ""),
        "candidate_rank": candidate_row.get("rank"),
        "candidate_score": round(candidate_score, 6),
        "kalman_score": round(kalman_score, 6),
        "best_baseline_family": best_baseline.get("family_id", best_baseline.get("strategy", "")),
        "best_baseline_score": round(best_baseline_score, 6),
        "best_overall_family": best_overall.get("family_id", best_overall.get("strategy", "")),
        "best_overall_score": row_score(replay, best_overall) if best_overall else 0.0,
        "delta_vs_kalman": delta_vs_kalman,
        "candidate_beats_kalman": bool(delta_vs_kalman is not None and delta_vs_kalman > 0),
        "delta_vs_best_baseline": delta_vs_best_baseline,
        "candidate_beats_best_baseline": bool(delta_vs_best_baseline is not None and delta_vs_best_baseline > 0),
        "claim_boundary": "Internal source-conditioned holdout replay; not field validation or a dollar claim.",
    }
    result["holdout_sha256"] = stable_sha256(
        {
            key: value
            for key, value in result.items()
            if key not in {"holdout_sha256", "source_path"}
        }
    )
    return result


def wilson_interval(wins: int, total: int, *, z: float = 1.959963984540054) -> dict[str, float]:
    if total <= 0:
        return {"lower": 0.0, "upper": 0.0}
    p = wins / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denom
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total) / denom
    return {"lower": round(max(0.0, center - margin), 6), "upper": round(min(1.0, center + margin), 6)}


def one_sided_sign_test_p_value(wins: int, total: int) -> float:
    if total <= 0:
        return 1.0
    tail = sum(math.comb(total, k) for k in range(wins, total + 1))
    return round(tail / (2**total), 8)


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in results if row.get("evidence_eligible")]
    deltas = [safe_float(row.get("delta_vs_kalman")) for row in eligible if row.get("delta_vs_kalman") is not None]
    wins = sum(1 for row in eligible if row.get("candidate_beats_kalman"))
    best_wins = sum(1 for row in eligible if row.get("candidate_beats_best_baseline"))
    total = len(deltas)
    interval = wilson_interval(wins, total)
    sign_p = one_sided_sign_test_p_value(wins, total)
    source_systems = sorted({str(row.get("source_system", "")) for row in eligible if row.get("source_system")})
    mean_delta = round(mean(deltas), 6) if deltas else 0.0
    route_count = len(results)
    missing_source_count = sum(not bool(row.get("source_available")) for row in results)
    fallback_count = sum(bool(row.get("fallback_used")) for row in results)
    tracked_source_count = sum(bool(row.get("source_git_tracked")) for row in eligible)
    full_file_hash_count = sum(bool(row.get("source_sha256_is_full_file")) for row in eligible)
    input_integrity_passed = bool(route_count > 0 and total == route_count and missing_source_count == 0 and fallback_count == 0)
    internal_gate = bool(
        total >= 20
        and wins >= 16
        and interval["lower"] > 0.50
        and sign_p <= 0.05
        and mean_delta > 0.0
        and input_integrity_passed
    )
    public_clean_checkout_replay_ready = bool(
        internal_gate and tracked_source_count == total and full_file_hash_count == total
    )
    return {
        "route_count": route_count,
        "holdout_count": total,
        "excluded_holdout_count": route_count - total,
        "source_system_count": len(source_systems),
        "source_systems": source_systems,
        "estimated_rows_replayed": sum(safe_int(row.get("estimated_rows")) for row in eligible),
        "numeric_samples_read": sum(safe_int(row.get("numeric_samples")) for row in eligible),
        "source_file_available_count": sum(bool(row.get("source_available")) for row in results),
        "missing_source_file_count": missing_source_count,
        "fallback_source_count": fallback_count,
        "repository_contained_source_count": sum(bool(row.get("source_within_repository")) for row in eligible),
        "git_tracked_source_count": tracked_source_count,
        "full_file_sha256_count": full_file_hash_count,
        "input_integrity_passed": input_integrity_passed,
        "public_clean_checkout_replay_ready": public_clean_checkout_replay_ready,
        "independent_reproduction_completed": False,
        "candidate": CANDIDATE,
        "named_baseline": NAMED_BASELINE,
        "wins_vs_kalman": wins,
        "losses_or_ties_vs_kalman": total - wins,
        "win_rate_vs_kalman": round(wins / total, 6) if total else 0.0,
        "wilson_95_win_rate_lower": interval["lower"],
        "wilson_95_win_rate_upper": interval["upper"],
        "one_sided_sign_test_p_value": sign_p,
        "wins_vs_best_baseline": best_wins,
        "mean_delta_vs_kalman": mean_delta,
        "min_delta_vs_kalman": round(min(deltas), 6) if deltas else 0.0,
        "max_delta_vs_kalman": round(max(deltas), 6) if deltas else 0.0,
        "passes_internal_20_holdout_gate": internal_gate,
        "ready_for_buyer_authorized_field_replay_request": internal_gate,
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
    }


def build_payload(
    *,
    max_routes: int = 24,
    sample_limit: int = 3_000,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ready = ready_replay_module()
    source_manifest = manifest if isinstance(manifest, dict) else ready.ensure_manifest()
    routes = select_wave_routes(source_manifest, max_routes=max_routes)
    replay = top_replay_module()
    results = [replay_holdout_route(route, ready, replay, sample_limit=sample_limit) for route in routes]
    summary = summarize(results)
    payload = {
        "schema": "kuramoto_holdout_expansion_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "inputs": {
            "source_manifest": rel(MANIFEST_JSON),
            "source_manifest_mode": "injected" if manifest is not None else "local_generated_or_cached",
            "source_manifest_sha256": stable_sha256(source_manifest),
            "ready_source_replay_adapter": rel(READY_REPLAY_SCRIPT),
            "top_replay_adapter": rel(TOP_REPLAY_SCRIPT),
        },
        "outputs": {"json": rel(OUT_JSON), "dashboard_json": rel(DASHBOARD_JSON), "markdown": rel(OUT_MD)},
        "summary": summary,
        "holdout_results": results,
        "claim_gates": {
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "medical_or_addiction_treatment_claim_allowed": False,
            "buyer_authorized_field_pilot_required": True,
            "public_clean_checkout_replay_ready": bool(summary["public_clean_checkout_replay_ready"]),
            "independent_reproduction_completed": False,
        },
        "field_validation_unlock": [
            "Identify one external system owner with authority over a real operational or accepted historical holdout dataset.",
            "Pre-register the source files, time windows, incumbent baseline, metric, and pass/fail threshold before running.",
            "Run the incumbent baseline and Kuramoto candidate on the same held-out windows without tuning after seeing results.",
            "Convert any improvement to dollars only using buyer-approved cost factors such as MWh, downtime minutes, review minutes, or forecast error cost.",
            "Capture signoff, logs, hashes, and a reproducible replay packet from the external owner or evaluator.",
        ],
    }
    payload["summary"]["holdout_chain_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "results": [
                {
                    "rank": row["rank"],
                    "source_ref": row["source_ref"],
                    "source_sha256": row["source_sha256"],
                    "delta_vs_kalman": row["delta_vs_kalman"],
                    "holdout_sha256": row["holdout_sha256"],
                }
                for row in results
            ],
        }
    )
    serialized = json.dumps(payload, sort_keys=True, default=str).lower()
    for term in FORBIDDEN_TERMS:
        if term in serialized:
            raise ValueError(f"Forbidden claim term leaked into Kuramoto holdout expansion: {term}")
    return payload


def build_public_projection(payload: dict[str, Any]) -> dict[str, Any]:
    public = json.loads(json.dumps(payload, sort_keys=True, default=str))
    for row in public.get("holdout_results", []):
        if not isinstance(row, dict):
            continue
        row.pop("source_path", None)
        profile = row.get("profile")
        if isinstance(profile, dict):
            profile.pop("source_path", None)
            profile["source"] = row.get("source_ref")
    public["privacy"] = {
        "private_source_paths_included": False,
        "public_source_references_are_hash_bound": True,
    }
    serialized = json.dumps(public, sort_keys=True, default=str)
    if PRIVATE_PATH_PATTERN.search(serialized):
        raise ValueError("Private absolute path leaked into Kuramoto public projection")
    return public


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Kuramoto Holdout Expansion",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Result",
        "",
        f"- Holdout routes replayed: `{summary['holdout_count']}`",
        f"- Configured routes: `{summary['route_count']}`",
        f"- Excluded routes: `{summary['excluded_holdout_count']}`",
        f"- Source systems covered: `{summary['source_system_count']}` ({', '.join(summary['source_systems'])})",
        f"- Estimated rows replayed: `{summary['estimated_rows_replayed']}`",
        f"- Numeric samples read: `{summary['numeric_samples_read']}`",
        f"- Candidate: `{summary['candidate']}`",
        f"- Named baseline: `{summary['named_baseline']}`",
        f"- Wins/losses vs Kalman: `{summary['wins_vs_kalman']}` / `{summary['losses_or_ties_vs_kalman']}`",
        f"- Win rate vs Kalman: `{summary['win_rate_vs_kalman']}`",
        f"- 95% Wilson win-rate interval: `{summary['wilson_95_win_rate_lower']}` to `{summary['wilson_95_win_rate_upper']}`",
        f"- One-sided sign-test p-value: `{summary['one_sided_sign_test_p_value']}`",
        f"- Mean delta vs Kalman: `{summary['mean_delta_vs_kalman']}`",
        f"- Delta range vs Kalman: `{summary['min_delta_vs_kalman']}` to `{summary['max_delta_vs_kalman']}`",
        f"- Passes internal 20-holdout gate: `{str(summary['passes_internal_20_holdout_gate']).lower()}`",
        f"- Ready for buyer-authorized field replay request: `{str(summary['ready_for_buyer_authorized_field_replay_request']).lower()}`",
        f"- Public clean-checkout replay ready: `{str(summary['public_clean_checkout_replay_ready']).lower()}`",
        f"- Independent reproduction completed: `{str(summary['independent_reproduction_completed']).lower()}`",
        f"- Holdout chain SHA-256: `{summary['holdout_chain_sha256']}`",
        "",
        "## Reviewer-Safe Interpretation",
        "",
        "This is stronger than the prior four-route replay because it broadens the held-out source-conditioned routes. "
        "It still cannot be called field validation until an external buyer, agency, lab, or system owner supplies or "
        "approves the held-out operational data, baseline, acceptance metric, and economic conversion.",
        "",
        "## Holdout Table",
        "",
        "| Rank | System | Source | Candidate Score | Kalman Score | Delta | Beats Kalman | Source Hash |",
        "| ---: | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in payload["holdout_results"]:
        source = str(row["source_ref"]).replace("|", "/")
        lines.append(
            f"| {row['rank']} | `{row['source_system']}` | `{source}` | `{row['candidate_score']}` | "
            f"`{row['kalman_score']}` | `{row['delta_vs_kalman']}` | `{str(row['candidate_beats_kalman']).lower()}` | "
            f"`{row['source_sha256'][:16]}` |"
        )
    lines.extend(["", "## Field Validation Unlock", ""])
    for item in payload["field_validation_unlock"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Closed Claim Gates",
            "",
            "- field_validation_claim_allowed: `false`",
            "- real_dollar_savings_claim_allowed: `false`",
            "- fixed_dollar_delta_sale_claim_allowed: `false`",
            "- live_trading_or_autonomous_execution_allowed: `false`",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    public_payload = build_public_projection(payload)
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, public_payload)
    write_text(OUT_MD, render_markdown(public_payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Holdout chain SHA256: {payload['summary']['holdout_chain_sha256']}")


if __name__ == "__main__":
    main()
