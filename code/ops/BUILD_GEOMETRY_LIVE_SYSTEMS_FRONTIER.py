from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

REGISTRY_JSON = CONFIG / "geometry_championship_v1_registry.json"
CHAMPION_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
ASSET_BOARD_JSON = OUT_OPS / "geometry_asset_wiring_board_latest.json"
ACTION_LEDGER_JSON = OUT_OPS / "geometry_action_replay_ledger_latest.json"
ACTION_BOARD_JSON = OUT_OPS / "geometry_execution_action_board_latest.json"
FIELD_MONEY_JSON = OUT_OPS / "field_money_truth_sweep_latest.json"
LIVE_SOURCE_MAX_JSON = OUT_OPS / "live_source_measurement_maximizer_latest.json"
LIVE_BREADTH_BRIDGE_JSON = OUT_OPS / "live_breadth_replay_bridge_latest.json"
TOP_REPLAY_JSON = OUT_OPS / "top_geometry_live_replay_results_latest.json"
ROLLING_JSON = OUT_OPS / "rolling_champion_gate_latest.json"

OUT_JSON = OUT_OPS / "geometry_live_systems_frontier_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_live_systems_frontier.json"
OUT_MD = DOCS / "GEOMETRY_LIVE_SYSTEMS_FRONTIER_2026-06-26.md"

BOUNDARY = (
    "Geometry live-systems frontier only. It ranks local evidence and uploaded measured-data candidates for "
    "next benchmark wiring. It does not establish field validation, clinical validation, safety certification, "
    "live trading permission, fixed-dollar frozen-delta value, realized savings, or grant-award certainty."
)

LOCAL_DATA_ROOTS = [
    ROOT / "data",
    ROOT / "clean_data",
    Path("C:/Users/Novac/AppData/Local/Temp"),
    Path("C:/Users/Novac/Downloads"),
    Path("C:/Users/Novac/iCloudDrive/EIA reports_"),
    Path("C:/Users/Novac/iCloudDrive/Kraken api"),
    Path("C:/Users/Novac/iCloudDrive/DoD"),
    Path("C:/Users/Novac/DOE_SBIR_LumenCore_PhaseI"),
    Path("C:/WhiteHole/_SOURCE_OF_TRUTH/PUBLIC_SOURCES/RAW"),
    Path("C:/WhiteHole/_SOURCE_OF_TRUTH/PUBLIC_SOURCES/OUT"),
    Path("E:/LumaProofVault"),
    Path("E:/GLYPH_DRIVE"),
]

DATA_SUFFIXES = {".csv", ".json", ".jsonl", ".txt", ".xlsx", ".xls", ".zip", ".parquet", ".duckdb"}
MAX_FILES_PER_ROOT = 650
MAX_TOTAL_FILES = 3500
MAX_ROW_COUNT_LINES = 250_000

SYSTEM_PATTERNS = [
    (
        "energy_grid",
        ("eia", "eba", "electric", "generation", "grid", "nuclear", "outage", "plant", "coal", "solar", "wind"),
    ),
    ("market_data", ("kraken", "ohlc", "coin", "crypto", "price", "trade", "ticker")),
    ("macro_rates_labor", ("fred", "dgs", "unrate", "cpiaucsl", "cpi", "rates", "labor", "macro")),
    ("weather_climate", ("noaa", "weather", "climate", "ncei", "temperature", "storm")),
    ("air_quality", ("epa", "aqs", "air_quality", "emiss", "emission", "pm25", "ozone")),
    ("water_hydrology", ("water", "hydrology", "usgs", "river", "stream", "flood")),
    ("maritime_ais", ("ais", "harbor", "vessel", "ship", "maritime", "port")),
    ("federal_opportunity", ("grant", "sam", "darpa", "dod", "sbir", "sttr", "baa", "nofo")),
    ("sports_market", ("sports", "odds", "game", "team")),
]

SYSTEM_TO_LANES = {
    "energy_grid": [
        "wave_resonance_timing",
        "thermal_ventilation",
        "branching_transport",
        "energy_price_pressure_proxy",
    ],
    "market_data": ["wave_resonance_timing", "market_signal_geometry", "energy_price_pressure_proxy"],
    "macro_rates_labor": ["wave_resonance_timing", "market_signal_geometry", "energy_price_pressure_proxy"],
    "weather_climate": ["thermal_ventilation", "branching_transport", "field_guided_control"],
    "air_quality": ["thermal_ventilation", "field_guided_control"],
    "water_hydrology": ["branching_transport", "mission_network_routing"],
    "maritime_ais": ["branching_transport", "field_guided_control", "optimal_curve_transport"],
    "federal_opportunity": ["resource_aware_scheduling", "multi_agent_coordination"],
    "sports_market": ["market_signal_geometry", "wave_resonance_timing"],
}

RUNNER_BY_LANE = {
    "optimal_curve_transport": (
        "python code\\geometry_optimal_curve_transport_benchmark.py "
        f"--out-root \"{(ROOT / 'out' / 'action_replays' / 'optimal_curve_transport').resolve()}\" "
        "--run-tag NEXT_LIVE_SYSTEM_FRONTIER --development-scenarios 8 --validation-scenarios 20"
    ),
    "wave_resonance_timing": (
        "python code\\geometry_wave_resonance_timing_benchmark.py "
        f"--out-root \"{(ROOT / 'out' / 'action_replays' / 'wave_resonance_timing').resolve()}\" "
        "--run-tag NEXT_LIVE_SYSTEM_FRONTIER --development-scenarios 8 --validation-scenarios 20"
    ),
    "thermal_ventilation": (
        "python code\\geometry_thermal_ventilation_benchmark.py "
        f"--out-root \"{(ROOT / 'out' / 'action_replays' / 'thermal_ventilation').resolve()}\" "
        "--run-tag NEXT_LIVE_SYSTEM_FRONTIER --development-scenarios 8 --validation-scenarios 20"
    ),
    "branching_transport": (
        "python code\\geometry_branching_transport_benchmark.py "
        f"--out-root \"{(ROOT / 'out' / 'action_replays' / 'branching_transport').resolve()}\" "
        "--run-tag NEXT_LIVE_SYSTEM_FRONTIER --development-scenarios 8 --validation-scenarios 20"
    ),
    "energy_price_pressure_proxy": "python code\\ops\\BUILD_ENERGY_PRICE_PRESSURE_FORECAST.py",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
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


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path)


def safe_path_text(path: Path) -> str:
    text = str(path).replace("\\", "/")
    text = re.sub(r"(?i)(api[_-]?key|token|secret|password)[^/\\]*", "[REDACTED]", text)
    return text


def classify_system(path: Path) -> str:
    text = safe_path_text(path).lower()
    scores: dict[str, int] = {}
    for system, terms in SYSTEM_PATTERNS:
        scores[system] = sum(1 for term in terms if term in text)
    best_system, best_score = max(scores.items(), key=lambda item: (item[1], item[0]))
    return best_system if best_score > 0 else "unclassified_measured_file"


def estimate_rows(path: Path) -> tuple[int, bool]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls", ".zip", ".parquet", ".duckdb"}:
        return 0, False
    if suffix in {".csv", ".txt"}:
        try:
            with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
                count = 0
                for count, _line in enumerate(handle, start=1):
                    if count >= MAX_ROW_COUNT_LINES:
                        return max(0, count - 1), True
                return max(0, count - 1), False
        except Exception:
            return 0, False
    if suffix == ".jsonl":
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                count = 0
                for count, _line in enumerate(handle, start=1):
                    if count >= MAX_ROW_COUNT_LINES:
                        return count, True
                return count, False
        except Exception:
            return 0, False
    if suffix == ".json":
        payload = read_json(path)
        if not payload:
            return 0, False
        for key in ("rows", "data", "provider_rows", "replay_cards", "families"):
            values = payload.get(key)
            if isinstance(values, list):
                return len(values), False
        return 1, False
    return 0, False


def sniff_csv_columns(path: Path) -> list[str]:
    if path.suffix.lower() != ".csv":
        return []
    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.reader(handle)
            return [str(col).strip()[:80] for col in next(reader, [])[:24]]
    except Exception:
        return []


def iter_candidate_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    try:
        iterator = root.rglob("*")
        for path in iterator:
            if len(files) >= MAX_FILES_PER_ROOT:
                break
            if not path.is_file():
                continue
            if path.suffix.lower() not in DATA_SUFFIXES:
                continue
            name = path.name.lower()
            if any(skip in name for skip in ("api_key", "secret", "password", "token")):
                continue
            files.append(path)
    except Exception:
        return files
    return files


def local_live_file_inventory() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in LOCAL_DATA_ROOTS:
        for path in iter_candidate_files(root):
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            try:
                stat = path.stat()
            except Exception:
                continue
            row_count, truncated = estimate_rows(path)
            system = classify_system(path)
            columns = sniff_csv_columns(path)
            rows.append(
                {
                    "path": safe_path_text(path),
                    "root": safe_path_text(root),
                    "name": path.name,
                    "suffix": path.suffix.lower(),
                    "size_bytes": stat.st_size,
                    "last_write_utcish": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "estimated_rows": row_count,
                    "row_count_truncated": truncated,
                    "system": system,
                    "candidate_lanes": SYSTEM_TO_LANES.get(system, []),
                    "columns": columns,
                    "file_sha256_basis": stable_sha256(
                        {
                            "path": safe_path_text(path),
                            "size_bytes": stat.st_size,
                            "last_write": stat.st_mtime,
                            "estimated_rows": row_count,
                            "system": system,
                        }
                    ),
                }
            )
            if len(rows) >= MAX_TOTAL_FILES:
                return rows
    rows.sort(key=lambda item: (-int(item["estimated_rows"]), -int(item["size_bytes"]), item["path"]))
    return rows


def representative_file_sample(rows: list[dict[str, Any]], *, limit: int = 120) -> list[dict[str, Any]]:
    """Keep the highest-volume rows while guaranteeing system coverage."""
    if len(rows) <= limit:
        return list(rows)
    selected: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    seen_systems: set[str] = set()
    for row in rows:
        system = str(row.get("system", "unclassified_measured_file"))
        path = str(row.get("path", ""))
        if system in seen_systems or not path:
            continue
        selected.append(row)
        seen_paths.add(path)
        seen_systems.add(system)
    for row in rows:
        if len(selected) >= limit:
            break
        path = str(row.get("path", ""))
        if not path or path in seen_paths:
            continue
        selected.append(row)
        seen_paths.add(path)
    return selected


def provider_file_inventory(live_source: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for provider in as_list(live_source.get("provider_rows")):
        if not isinstance(provider, dict):
            continue
        for key in ("snapshot_json", "snapshot_csv", "snapshot_latest_json"):
            value = str(provider.get(key, "")).strip()
            if not value:
                continue
            path = ROOT / value
            if not path.exists():
                continue
            row_count, truncated = estimate_rows(path)
            rows.append(
                {
                    "source": provider.get("source", ""),
                    "sector": provider.get("sector", ""),
                    "path": rel(path),
                    "estimated_rows": row_count,
                    "row_count_truncated": truncated,
                    "system": classify_system(path),
                    "candidate_lanes": SYSTEM_TO_LANES.get(classify_system(path), []),
                    "snapshot_sha256": provider.get("snapshot_sha256", ""),
                }
            )
    return rows


def summarize_systems(local_rows: list[dict[str, Any]], provider_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "system": "",
            "file_count": 0,
            "estimated_rows": 0,
            "candidate_lanes": set(),
            "top_files": [],
            "source": "local_uploaded_or_live_snapshot",
        }
    )
    for row in [*local_rows, *provider_rows]:
        system = str(row.get("system", "unclassified_measured_file"))
        item = grouped[system]
        item["system"] = system
        item["file_count"] += 1
        item["estimated_rows"] += int(row.get("estimated_rows") or 0)
        item["candidate_lanes"].update(row.get("candidate_lanes") or [])
        if len(item["top_files"]) < 8:
            item["top_files"].append(
                {
                    "path": row.get("path", ""),
                    "estimated_rows": row.get("estimated_rows", 0),
                    "size_bytes": row.get("size_bytes", 0),
                }
            )
    out = []
    for item in grouped.values():
        item["candidate_lanes"] = sorted(item["candidate_lanes"])
        item["system_score"] = int(item["estimated_rows"]) + (int(item["file_count"]) * 100)
        out.append(item)
    out.sort(key=lambda item: (-int(item["system_score"]), item["system"]))
    return out


def family_index(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for row in as_list(registry.get("families")):
        if isinstance(row, dict) and row.get("id"):
            out[str(row["id"])] = row
    return out


def rows_by_key(rows: list[Any], key: str) -> dict[str, dict[str, Any]]:
    out = {}
    for row in rows:
        if isinstance(row, dict) and row.get(key):
            out[str(row[key])] = row
    return out


def score_family(
    family: dict[str, Any],
    asset_row: dict[str, Any],
    ledger_row: dict[str, Any],
    rolling_row: dict[str, Any],
    top_replay_row: dict[str, Any],
    system_rows: list[dict[str, Any]],
) -> tuple[float, list[str], list[str]]:
    lane = str(family.get("lane", ""))
    score = 0.0
    evidence: list[str] = []
    blockers: list[str] = []

    if family.get("benchmark_hypothesis"):
        score += 8
        evidence.append("benchmark_hypothesis_present")
    if family.get("natural_logic"):
        score += 4
        evidence.append("natural_logic_present")
    if asset_row:
        score += min(float(asset_row.get("asset_score") or 0), 300.0) / 3.0
        evidence.append("asset_board_ranked")
        if asset_row.get("paid_pilot_ready"):
            score += 15
            evidence.append("paid_pilot_scoping_candidate")
        if asset_row.get("robust_repeat_uncertainty_gate_passed"):
            score += 20
            evidence.append("robust_repeat_uncertainty_gate_passed")
    if rolling_row:
        score += 30
        evidence.append(str(rolling_row.get("status", "rolling_gate_present")))
        score += min(float(rolling_row.get("source_count") or 0), 10.0) * 2.0
        if int(rolling_row.get("distinct_run_hash_count") or 0) >= 2:
            score += 10
            evidence.append("distinct_run_hash_count_ge_2")
    if ledger_row:
        delta = float(ledger_row.get("score_delta_vs_best_baseline") or 0)
        score += max(0.0, delta) * 120.0
        evidence.append("action_replay_lane_winner")
    if top_replay_row:
        delta = float(top_replay_row.get("candidate_score_delta_vs_named_baseline") or 0)
        score += max(0.0, delta) * 90.0
        evidence.append("live_context_replay_card")

    lane_system_rows = [row for row in system_rows if lane in row.get("candidate_lanes", [])]
    if lane_system_rows:
        rows = sum(int(row.get("estimated_rows") or 0) for row in lane_system_rows)
        files = sum(int(row.get("file_count") or 0) for row in lane_system_rows)
        score += min(rows / 1000.0, 40.0) + min(files, 20.0)
        evidence.append("local_live_system_files_available")
    else:
        blockers.append("No local uploaded/live system file inventory mapped to this lane yet.")

    if not ledger_row and lane in RUNNER_BY_LANE:
        blockers.append("Runner exists but this family is not the current lane replay winner.")
    if not rolling_row:
        blockers.append("Not a rolling champion yet.")
    if not asset_row:
        blockers.append("Not in current asset wiring board.")

    return round(score, 3), evidence, blockers[:8]


def ranked_families(
    registry: dict[str, Any],
    champion: dict[str, Any],
    asset_board: dict[str, Any],
    ledger: dict[str, Any],
    top_replay: dict[str, Any],
    rolling: dict[str, Any],
    system_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    asset_rows = rows_by_key(as_list(champion.get("family_asset_rankings")), "family")
    wiring_rows = rows_by_key(as_list(asset_board.get("wiring_rows")), "family_id")
    ledger_by_family = rows_by_key(as_list(ledger.get("replay_rows")), "best_geometry")
    top_replay_by_family = rows_by_key(as_list(top_replay.get("replay_cards")), "candidate_family_id")
    rolling_by_family = rows_by_key(as_list(rolling.get("promotion_board")), "family_id")

    rows = []
    for family_id, family in family_index(registry).items():
        asset_row = dict(asset_rows.get(family_id, {}))
        asset_row.update(wiring_rows.get(family_id, {}))
        ledger_row = ledger_by_family.get(family_id, {})
        rolling_row = rolling_by_family.get(family_id, {})
        top_row = top_replay_by_family.get(family_id, {})
        score, evidence, blockers = score_family(family, asset_row, ledger_row, rolling_row, top_row, system_rows)
        lane = str(family.get("lane", ""))
        rows.append(
            {
                "family_id": family_id,
                "label": family.get("label", family_id),
                "lane": lane,
                "status": family.get("status", ""),
                "frontier_score": score,
                "evidence_tags": sorted(set(evidence)),
                "best_baseline": ledger_row.get("best_baseline") or top_row.get("best_baseline_family_id") or "",
                "action_replay_delta": ledger_row.get("score_delta_vs_best_baseline"),
                "live_context_delta": top_row.get("candidate_score_delta_vs_named_baseline"),
                "rolling_status": rolling_row.get("status", ""),
                "rolling_source_count": rolling_row.get("source_count", 0),
                "paid_pilot_ready": bool(asset_row.get("paid_pilot_ready", False)),
                "robust_repeat_uncertainty_gate_passed": bool(
                    asset_row.get("robust_repeat_uncertainty_gate_passed", False)
                ),
                "candidate_live_systems": [
                    row["system"] for row in system_rows if lane in row.get("candidate_lanes", [])
                ][:8],
                "safe_local_command": RUNNER_BY_LANE.get(lane, ""),
                "claim_boundary": "Proof-building only; not field validation, real-dollar savings, clinical validation, or live trading permission.",
                "blockers": blockers,
            }
        )
    rows.sort(key=lambda item: (-float(item["frontier_score"]), item["family_id"]))
    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx
    return rows


def next_10_actions(ranked: list[dict[str, Any]], system_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_family = {row["family_id"]: row for row in ranked}
    top_system_names = [row["system"] for row in system_rows[:5]]
    templates = [
        (
            "brachistochrone_descent",
            "Wire the strongest optimal-curve champion to the biggest local energy/maritime path files and rerun identical baselines.",
        ),
        (
            "kuramoto_phase_coupling",
            "Run the harmonic phase-lock lane on EIA/FRED/Kraken/NOAA-style time windows and preserve phase-error baselines.",
        ),
        (
            "thermal_plume_convection",
            "Use EIA load, nuclear outage, NOAA/weather, and thermal proxy files to strengthen cooling and recovery evidence.",
        ),
        (
            "leaf_veins",
            "Promote or demote the branching winner by replaying it on grid/outage/water/AIS network constraints.",
        ),
        (
            "phase_locked_residual_corrector",
            "Keep the energy price pressure proxy separate from geometry winners and require buyer economics before money claims.",
        ),
    ]
    actions: list[dict[str, Any]] = []
    for family_id, action in templates:
        row = by_family.get(family_id, {})
        actions.append(
            {
                "priority": len(actions) + 1,
                "family_id": family_id,
                "lane": row.get("lane", "energy_price_pressure_proxy" if family_id.startswith("phase_") else ""),
                "action": action,
                "top_local_system_targets": top_system_names,
                "safe_local_command": row.get("safe_local_command", RUNNER_BY_LANE.get("energy_price_pressure_proxy", "")),
                "done_when": "A frozen replay artifact names the data source, baseline, candidate, run hash, and claim boundary.",
                "claim_boundary": "Do not call this field validation or realized savings without buyer-authorized operational data.",
            }
        )

    generic = [
        "Create a source manifest that maps each uploaded/live file to one lane, one baseline, and one candidate.",
        "Archive or demote unclassified local data files that cannot be mapped to a measurable lane.",
        "Push dashboard feeds for the frontier, replay ledger, and action board to the public domain only after redaction checks.",
        "Use the grant appendix language: repeat live-context candidate, not field validated, not guaranteed savings.",
        "Ask for paid pilot authorization around the top bounded claim instead of selling fixed-price frozen deltas.",
    ]
    for item in generic:
        actions.append(
            {
                "priority": len(actions) + 1,
                "family_id": "",
                "lane": "cross_stack",
                "action": item,
                "top_local_system_targets": top_system_names,
                "safe_local_command": "",
                "done_when": "The artifact is hashable, reproducible, and linked from the dashboard/grant packet.",
                "claim_boundary": "Keep field validation, real-dollar, medical, and trading claim gates closed until evidence satisfies the gate.",
            }
        )
    return actions[:10]


def build_payload() -> dict[str, Any]:
    registry = read_json(REGISTRY_JSON)
    champion = read_json(CHAMPION_JSON)
    asset_board = read_json(ASSET_BOARD_JSON)
    ledger = read_json(ACTION_LEDGER_JSON)
    field_money = read_json(FIELD_MONEY_JSON)
    live_source = read_json(LIVE_SOURCE_MAX_JSON)
    _live_bridge = read_json(LIVE_BREADTH_BRIDGE_JSON)
    top_replay = read_json(TOP_REPLAY_JSON)
    rolling = read_json(ROLLING_JSON)

    local_files = local_live_file_inventory()
    provider_files = provider_file_inventory(live_source)
    system_rows = summarize_systems(local_files, provider_files)
    ranked = ranked_families(registry, champion, asset_board, ledger, top_replay, rolling, system_rows)

    gates = as_dict(field_money.get("gates"))
    live_summary = as_dict(live_source.get("summary"))
    champion_summary = as_dict(champion.get("summary"))
    payload = {
        "schema": "geometry_live_systems_frontier_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "registry": rel(REGISTRY_JSON),
            "champion_of_champions": rel(CHAMPION_JSON),
            "asset_wiring_board": rel(ASSET_BOARD_JSON),
            "action_replay_ledger": rel(ACTION_LEDGER_JSON),
            "field_money_truth_sweep": rel(FIELD_MONEY_JSON),
            "live_source_measurement_maximizer": rel(LIVE_SOURCE_MAX_JSON),
            "live_breadth_bridge": rel(LIVE_BREADTH_BRIDGE_JSON),
            "top_geometry_live_replay_results": rel(TOP_REPLAY_JSON),
            "rolling_champion_gate": rel(ROLLING_JSON),
        },
        "outputs": {"json": rel(OUT_JSON), "dashboard_json": rel(DASHBOARD_JSON), "markdown": rel(OUT_MD)},
        "summary": {
            "registered_family_count": len(as_list(registry.get("families"))),
            "ranked_family_count": len(ranked),
            "lane_count": len(as_dict(registry.get("lanes"))),
            "local_file_inventory_count": len(local_files),
            "provider_snapshot_file_count": len(provider_files),
            "live_system_count": len(system_rows),
            "local_estimated_rows": sum(int(row.get("estimated_rows") or 0) for row in local_files),
            "provider_snapshot_estimated_rows": sum(int(row.get("estimated_rows") or 0) for row in provider_files),
            "canonical_measured_sources": live_summary.get("measured_sources")
            or champion_summary.get("live_measured_sources"),
            "canonical_measured_rows": live_summary.get("total_measured_rows")
            or champion_summary.get("live_total_measured_rows"),
            "top_family": ranked[0]["family_id"] if ranked else "",
            "top_family_score": ranked[0]["frontier_score"] if ranked else 0,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "medical_or_addiction_treatment_claim_allowed": False,
            "bounded_estimated_value_claim_allowed": bool(gates.get("bounded_estimated_value_claim_allowed", False)),
            "glyph_or_external_vault_routed": bool(gates.get("glyph_or_external_vault_routed", False)),
            "frontier_sha256": stable_sha256(
                {
                    "ranked_top10": ranked[:10],
                    "system_rows": system_rows,
                    "local_count": len(local_files),
                    "provider_count": len(provider_files),
                }
            ),
        },
        "top_10_next_actions": next_10_actions(ranked, system_rows),
        "top_live_systems": system_rows[:20],
        "top_ranked_families": ranked[:40],
        "all_family_rankings": ranked,
        "local_live_file_inventory_sample": representative_file_sample(local_files, limit=120),
        "provider_snapshot_files": provider_files,
        "claim_gates": {
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "medical_or_addiction_treatment_claim_allowed": False,
            "mass_email_allowed": False,
        },
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Live Systems Frontier",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Registered families ranked: `{summary['ranked_family_count']}` / `{summary['registered_family_count']}`",
        f"- Lanes: `{summary['lane_count']}`",
        f"- Local uploaded/live files inventoried: `{summary['local_file_inventory_count']}`",
        f"- Local estimated data rows: `{summary['local_estimated_rows']}`",
        f"- Provider snapshot files: `{summary['provider_snapshot_file_count']}`",
        f"- Canonical measured sources: `{summary['canonical_measured_sources']}`",
        f"- Canonical measured rows: `{summary['canonical_measured_rows']}`",
        f"- Top family: `{summary['top_family']}`",
        f"- Top family score: `{summary['top_family_score']}`",
        f"- Field validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary['real_dollar_savings_claim_allowed']).lower()}`",
        f"- Live trading/autonomous execution allowed: `{str(summary['live_trading_or_autonomous_execution_allowed']).lower()}`",
        f"- Medical/addiction-treatment claim allowed: `{str(summary['medical_or_addiction_treatment_claim_allowed']).lower()}`",
        f"- Frontier SHA-256: `{summary['frontier_sha256']}`",
        "",
        "## Next 10 Actions",
        "",
        "| # | Family | Lane | Action |",
        "| --- | --- | --- | --- |",
    ]
    for action in payload["top_10_next_actions"]:
        lines.append(
            f"| `{action['priority']}` | `{action['family_id']}` | `{action['lane']}` | {action['action']} |"
        )

    lines.extend(["", "## Top Live Systems", "", "| System | Files | Estimated Rows | Candidate Lanes |", "| --- | --- | --- | --- |"])
    for row in payload["top_live_systems"][:12]:
        lanes = ", ".join(row.get("candidate_lanes") or [])
        lines.append(f"| `{row['system']}` | `{row['file_count']}` | `{row['estimated_rows']}` | {lanes} |")

    lines.extend(["", "## Top Geometry Families", "", "| Rank | Family | Lane | Score | Evidence |", "| --- | --- | --- | --- | --- |"])
    for row in payload["top_ranked_families"][:15]:
        evidence = ", ".join(row.get("evidence_tags") or [])
        lines.append(f"| `{row['rank']}` | `{row['family_id']}` | `{row['lane']}` | `{row['frontier_score']}` | {evidence} |")

    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- The file inventory can show available measured material, not that every row is valid for every lane.",
            "- Geometry winners need lane-specific adapters before stronger claims.",
            "- A full-body haptic or crown concept must stay in wellness/research territory unless a clinician-led regulated study proves safety and efficacy.",
            "- No drug-like effect, addiction-treatment, brain-modulation, live-trading, fixed-dollar, or realized-savings claim is permitted by this artifact.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


if __name__ == "__main__":
    main()
