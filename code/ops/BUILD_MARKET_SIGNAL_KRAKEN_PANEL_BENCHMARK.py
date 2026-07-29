from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = (
    ROOT
    / "config"
    / "market_signal_kraken_panel_benchmark_protocol_v1.json"
)
OUT_JSON = (
    ROOT
    / "out"
    / "ops"
    / "market_signal_kraken_panel_benchmark_latest.json"
)
DASHBOARD_JSON = (
    ROOT
    / "dashboard"
    / "data"
    / "market_signal_kraken_panel_benchmark.json"
)
MANIFEST_JSON = (
    ROOT
    / "out"
    / "ops"
    / "market_signal_kraken_panel_benchmark_manifest_latest.json"
)
DOC_PATH = (
    ROOT
    / "docs"
    / "MARKET_SIGNAL_KRAKEN_PANEL_BENCHMARK_2026-07-29.md"
)

BOUNDARY = (
    "Exploratory retrospective paper/replay only. The turnover-ranked panel "
    "was frozen before candidate scoring, but it was not prospectively "
    "protected and the pairs share a common exchange and market regime. "
    "No alpha, edge, profit, value, field-performance, independence, "
    "execution-quality, or live-trading claim is allowed."
)


def load_base_module():
    path = (
        ROOT
        / "code"
        / "ops"
        / "BUILD_MARKET_SIGNAL_SOURCE_NATIVE_BENCHMARK.py"
    )
    spec = importlib.util.spec_from_file_location(
        "market_signal_source_native_benchmark_base",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load base benchmark: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_base_module()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
        + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def relative_path(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def expected_panel_from_receipt(
    protocol: dict[str, Any],
    receipt: dict[str, Any],
) -> list[str]:
    selection = protocol["selection"]
    eligible_quote = str(selection["eligible_quote"]).upper()
    excluded_bases = {
        str(value).upper() for value in selection["excluded_base_assets"]
    }
    expected: list[str] = []
    seen_bases: set[str] = set()
    for row in receipt.get("results", []):
        pair = str(row.get("pair", "")).upper()
        if "/" not in pair:
            continue
        base, quote = pair.split("/", 1)
        if quote != eligible_quote or base in excluded_bases:
            continue
        if base in seen_bases:
            continue
        expected.append(pair)
        seen_bases.add(base)
    return expected


def validate_protocol(
    protocol: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        protocol.get("schema")
        != "market_signal_kraken_panel_benchmark_protocol_v1"
    ):
        raise ValueError("Unexpected Kraken-panel protocol schema")
    if any(bool(value) for value in protocol["claim_controls"].values()):
        raise ValueError("Every Kraken-panel claim control must remain false")
    if protocol["inference"]["confirmatory_inference_allowed"] is not False:
        raise ValueError("Confirmatory inference must remain disabled")
    if protocol["inference"]["promotion_eligible"] is not False:
        raise ValueError("Retrospective panel must remain promotion-ineligible")

    implementation = protocol["base_implementation"]
    for path_key, hash_key in (
        ("strategy_protocol_path", "strategy_protocol_file_sha256"),
        ("strategy_builder_path", "strategy_builder_file_sha256"),
        ("collector_path", "collector_file_sha256"),
    ):
        path = ROOT / str(implementation[path_key])
        observed = BASE.file_sha256(path)
        if observed != str(implementation[hash_key]):
            raise ValueError(f"Base implementation hash drift: {path_key}")

    base_protocol = read_json(
        ROOT / str(implementation["strategy_protocol_path"])
    )
    candidate_ids = tuple(
        row["family_id"] for row in base_protocol["candidates"]
    )
    baseline_ids = tuple(
        row["baseline_id"] for row in base_protocol["baselines"]
    )
    if candidate_ids != BASE.EXPECTED_CANDIDATE_IDS:
        raise ValueError("Base candidate roster drift")
    if baseline_ids != BASE.EXPECTED_BASELINE_IDS:
        raise ValueError("Base baseline roster drift")
    if not base_protocol["evaluation"]["no_parameter_tuning_on_evaluation"]:
        raise ValueError("Base chronology/tuning control drift")

    receipt_control = protocol["collector_receipt"]
    receipt_path = ROOT / str(receipt_control["path"])
    if BASE.file_sha256(receipt_path) != str(
        receipt_control["file_sha256"]
    ):
        raise ValueError("Collector receipt hash drift")
    receipt = read_json(receipt_path)
    for key in (
        "generated_utc",
        "scope",
        "execution_authorized",
        "interval_min",
        "pairs_discovered",
        "pairs_selected",
        "pairs_updated",
        "pair_errors",
    ):
        if receipt.get(key) != receipt_control.get(key):
            raise ValueError(f"Collector receipt field drift: {key}")
    if receipt.get("execution_authorized") is not False:
        raise ValueError("Collector must remain read-only")
    if int(receipt.get("pair_errors", -1)) != 0:
        raise ValueError("Collector receipt contains pair errors")

    receipt_pairs = [
        str(row.get("pair", "")).upper()
        for row in receipt.get("results", [])
    ]
    if receipt_pairs != [
        str(value).upper()
        for value in protocol["selection"]["selected_pair_order"]
    ]:
        raise ValueError("Collector selected-pair order drift")

    panel = protocol["selection"]["panel"]
    panel_pairs = [str(row["pair"]).upper() for row in panel]
    expected_pairs = expected_panel_from_receipt(protocol, receipt)
    if panel_pairs != expected_pairs:
        raise ValueError("Panel no longer matches the pre-scoring rule")
    if len(panel_pairs) != len(set(panel_pairs)):
        raise ValueError("Panel contains duplicate pairs")
    if len(panel_pairs) < int(
        protocol["inference"]["minimum_pair_count_for_exploratory_test"]
    ):
        raise ValueError("Panel is below the exploratory pair-count floor")

    result_by_pair = {
        str(row["pair"]).upper(): row
        for row in receipt.get("results", [])
    }
    for row in panel:
        pair = str(row["pair"]).upper()
        receipt_row = result_by_pair[pair]
        path = ROOT / str(row["path"])
        if path.resolve() != Path(str(receipt_row["path"])).resolve():
            raise ValueError(f"Panel path differs from receipt: {pair}")
        if int(row["row_count"]) != int(receipt_row["rows_total"]):
            raise ValueError(f"Panel row count differs from receipt: {pair}")
        if BASE.rounded(BASE.as_float(row["turnover_24h_usd"]), 2) != (
            BASE.rounded(
                BASE.as_float(receipt_row["turnover_24h_usd"]),
                2,
            )
        ):
            raise ValueError(f"Panel turnover differs from receipt: {pair}")
        if BASE.file_sha256(path) != str(row["file_sha256"]):
            raise ValueError(f"Panel file hash drift: {pair}")
    return base_protocol, receipt


def read_panel_series(entry: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / str(entry["path"])
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected_columns = {
            "time",
            "open",
            "high",
            "low",
            "close",
            "vwap",
            "volume",
            "count",
        }
        if set(reader.fieldnames or []) != expected_columns:
            raise ValueError(
                f"Unexpected Kraken history columns: {entry['pair']}"
            )
        rows = list(reader)
    if len(rows) != int(entry["row_count"]):
        raise ValueError(f"Panel CSV row-count drift: {entry['pair']}")

    timestamps: list[str] = []
    closes: list[float] = []
    for row in rows:
        timestamp = str(row["time"]).strip()
        close = BASE.as_float(row["close"])
        if not timestamp or close <= 0.0:
            raise ValueError(f"Invalid panel row: {entry['pair']}")
        timestamps.append(timestamp)
        closes.append(close)
    if timestamps != sorted(timestamps):
        raise ValueError(f"Panel timestamps are not ordered: {entry['pair']}")
    if len(timestamps) != len(set(timestamps)):
        raise ValueError(f"Panel timestamps are duplicated: {entry['pair']}")
    return {
        "series_id": str(entry["pair"]),
        "input_row_count": len(rows),
        "timestamps": timestamps,
        "closes": closes,
    }


def source_definition(
    base_protocol: dict[str, Any],
) -> dict[str, Any]:
    source = next(
        row
        for row in base_protocol["sources"]
        if row["source"] == "KRAKEN_PUBLIC"
    )
    return {
        **source,
        "source": "KRAKEN_PUBLIC_PANEL",
        "snapshot_path": "",
        "snapshot_embedded_sha256": "",
    }


def build_comparisons(
    series_results: list[dict[str, Any]],
    base_protocol: dict[str, Any],
    panel_protocol: dict[str, Any],
) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    minimum_pairs = int(
        panel_protocol["inference"][
            "minimum_pair_count_for_exploratory_test"
        ]
    )
    for candidate_id in BASE.EXPECTED_CANDIDATE_IDS:
        for baseline_id in BASE.EXPECTED_BASELINE_IDS:
            cluster_rows: list[dict[str, Any]] = []
            for series_row in series_results:
                strategies = {
                    row["strategy_id"]: row
                    for row in series_row["strategy_results"]
                }
                candidate_score = BASE.as_float(
                    strategies[candidate_id]["metrics"][
                        "risk_adjusted_score"
                    ]
                )
                baseline_score = BASE.as_float(
                    strategies[baseline_id]["metrics"][
                        "risk_adjusted_score"
                    ]
                )
                cluster_rows.append(
                    {
                        "cluster_id": (
                            "KRAKEN_PUBLIC_PANEL::"
                            f"{series_row['series_id']}"
                        ),
                        "candidate_risk_adjusted_score": candidate_score,
                        "baseline_risk_adjusted_score": baseline_score,
                        "risk_adjusted_score_delta": BASE.rounded(
                            candidate_score - baseline_score
                        ),
                        "shared_future_return_sha256": series_row[
                            "future_return_sha256"
                        ],
                        "observation_count": series_row[
                            "evaluation_observation_count"
                        ],
                    }
                )
            deltas = [
                BASE.as_float(row["risk_adjusted_score_delta"])
                for row in cluster_rows
            ]
            pair_count = len(cluster_rows)
            count_floor_met = pair_count >= minimum_pairs
            raw_p_value = (
                BASE.exact_two_sided_sign_test(deltas)
                if count_floor_met
                else 1.0
            )
            comparisons.append(
                {
                    "candidate_family_id": candidate_id,
                    "source": "KRAKEN_PUBLIC_PANEL",
                    "baseline_id": baseline_id,
                    "paired_unit": "source_series",
                    "source_series_cluster_count": pair_count,
                    "minimum_pair_count_for_exploratory_test": (
                        minimum_pairs
                    ),
                    "pair_count_floor_met": count_floor_met,
                    "independence_assumption_confirmed": False,
                    "confirmatory_inference_allowed": False,
                    "cluster_rows": cluster_rows,
                    "mean_risk_adjusted_score_delta": BASE.rounded(
                        mean(deltas) if deltas else 0.0
                    ),
                    "candidate_beats_baseline_mean": bool(
                        deltas and mean(deltas) > 0.0
                    ),
                    "raw_cluster_sign_test_p_value": BASE.rounded(
                        raw_p_value
                    ),
                    "global_holm_adjusted_p_value": None,
                    "statistically_positive_after_global_holm": False,
                    "promotion_eligible": False,
                }
            )
    BASE.apply_global_holm(
        comparisons,
        BASE.as_float(
            panel_protocol["inference"]["familywise_alpha"]
        ),
    )
    for row in comparisons:
        row["promotion_eligible"] = False
    return comparisons


def candidate_diagnostics(
    comparisons: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in comparisons:
        grouped[str(row["candidate_family_id"])].append(row)
    diagnostics: list[dict[str, Any]] = []
    for candidate_id in BASE.EXPECTED_CANDIDATE_IDS:
        rows = grouped[candidate_id]
        diagnostics.append(
            {
                "candidate_family_id": candidate_id,
                "registered_baseline_count": len(
                    BASE.EXPECTED_BASELINE_IDS
                ),
                "baseline_mean_win_count": sum(
                    1
                    for row in rows
                    if row["candidate_beats_baseline_mean"]
                ),
                "global_holm_positive_count": sum(
                    1
                    for row in rows
                    if row[
                        "statistically_positive_after_global_holm"
                    ]
                ),
                "beats_every_baseline_on_mean": all(
                    row["candidate_beats_baseline_mean"]
                    for row in rows
                ),
                "beats_every_baseline_after_global_holm": all(
                    row[
                        "statistically_positive_after_global_holm"
                    ]
                    for row in rows
                ),
                "promotion_eligible": False,
                "promotion_status": (
                    "BLOCKED_RETROSPECTIVE_COMMON_MARKET_FACTOR"
                ),
            }
        )
    return diagnostics


def build_payload(
    generated_utc: str | None = None,
) -> dict[str, Any]:
    protocol = read_json(PROTOCOL_PATH)
    base_protocol, receipt = validate_protocol(protocol)
    source = source_definition(base_protocol)
    panel = protocol["selection"]["panel"]
    series_results = [
        BASE.evaluate_series(
            source,
            read_panel_series(entry),
            base_protocol,
        )
        for entry in panel
    ]
    comparisons = build_comparisons(
        series_results,
        base_protocol,
        protocol,
    )
    diagnostics = candidate_diagnostics(comparisons)
    global_positive_count = sum(
        1
        for row in comparisons
        if row["statistically_positive_after_global_holm"]
    )
    payload = {
        "schema": "market_signal_kraken_panel_benchmark_v1",
        "protocol_id": str(protocol["protocol_id"]),
        "generated_utc": generated_utc or now_utc(),
        "status": "RETROSPECTIVE_PANEL_SCREEN_NO_PROMOTION",
        "mode": str(protocol["mode"]),
        "boundary": BOUNDARY,
        "claim_controls": protocol["claim_controls"],
        "inputs": {
            "protocol": {
                "path": relative_path(PROTOCOL_PATH),
                "file_sha256": BASE.file_sha256(PROTOCOL_PATH),
                "canonical_sha256": BASE.stable_sha256(protocol),
            },
            "base_strategy_protocol": {
                "path": str(
                    protocol["base_implementation"][
                        "strategy_protocol_path"
                    ]
                ),
                "file_sha256": BASE.file_sha256(
                    ROOT
                    / str(
                        protocol["base_implementation"][
                            "strategy_protocol_path"
                        ]
                    )
                ),
                "canonical_sha256": BASE.stable_sha256(
                    base_protocol
                ),
            },
            "base_strategy_builder": {
                "path": str(
                    protocol["base_implementation"][
                        "strategy_builder_path"
                    ]
                ),
                "file_sha256": BASE.file_sha256(
                    ROOT
                    / str(
                        protocol["base_implementation"][
                            "strategy_builder_path"
                        ]
                    )
                ),
            },
            "collector_receipt": {
                "path": str(protocol["collector_receipt"]["path"]),
                "file_sha256": BASE.file_sha256(
                    ROOT
                    / str(protocol["collector_receipt"]["path"])
                ),
                "generated_utc": str(receipt["generated_utc"]),
                "execution_authorized": False,
                "pairs_discovered": int(receipt["pairs_discovered"]),
                "pairs_selected": int(receipt["pairs_selected"]),
                "pairs_updated": int(receipt["pairs_updated"]),
                "pair_errors": int(receipt["pair_errors"]),
            },
            "panel_files": [
                {
                    "pair": str(entry["pair"]),
                    "path": str(entry["path"]),
                    "row_count": int(entry["row_count"]),
                    "turnover_24h_usd": BASE.rounded(
                        BASE.as_float(entry["turnover_24h_usd"]),
                        2,
                    ),
                    "file_sha256": BASE.file_sha256(
                        ROOT / str(entry["path"])
                    ),
                    "hash_verified": True,
                }
                for entry in panel
            ],
        },
        "protocol_summary": {
            "selection": {
                "pre_scoring_rule": protocol["selection"][
                    "pre_scoring_rule"
                ],
                "candidate_or_baseline_scores_used_in_selection": (
                    False
                ),
                "legacy_alpha_priority_enabled": False,
                "panel_pair_count": len(panel),
                "panel_pairs": [
                    str(entry["pair"]) for entry in panel
                ],
            },
            "evaluation": base_protocol["evaluation"],
            "source_cost": {
                "cost_bps_per_unit_turnover": source[
                    "cost_bps_per_unit_turnover"
                ],
                "cost_note": source["cost_note"],
            },
            "inference": protocol["inference"],
        },
        "implementation_summary": {
            "registered_candidate_count": len(
                BASE.EXPECTED_CANDIDATE_IDS
            ),
            "implemented_candidate_count": len(
                BASE.EXPECTED_CANDIDATE_IDS
            ),
            "registered_baseline_count": len(
                BASE.EXPECTED_BASELINE_IDS
            ),
            "implemented_baseline_count": len(
                BASE.EXPECTED_BASELINE_IDS
            ),
            "candidate_ids": list(BASE.EXPECTED_CANDIDATE_IDS),
            "baseline_ids": list(BASE.EXPECTED_BASELINE_IDS),
            "source_count": 1,
            "source_series_count": len(series_results),
            "strategy_source_series_result_count": sum(
                len(row["strategy_results"])
                for row in series_results
            ),
            "evaluation_observation_count_per_series": sorted(
                {
                    int(row["evaluation_observation_count"])
                    for row in series_results
                }
            ),
        },
        "series_results": series_results,
        "comparisons": comparisons,
        "candidate_diagnostics": diagnostics,
        "result_summary": {
            "candidate_source_baseline_comparison_count": len(
                comparisons
            ),
            "comparison_mean_win_count": sum(
                1
                for row in comparisons
                if row["candidate_beats_baseline_mean"]
            ),
            "exploratory_global_holm_positive_count": (
                global_positive_count
            ),
            "candidate_beats_every_baseline_on_mean_count": sum(
                1
                for row in diagnostics
                if row["beats_every_baseline_on_mean"]
            ),
            "candidate_beats_every_baseline_after_global_holm_count": (
                sum(
                    1
                    for row in diagnostics
                    if row[
                        "beats_every_baseline_after_global_holm"
                    ]
                )
            ),
            "promotion_count": 0,
            "confirmatory_inference_allowed": False,
            "conclusion": (
                "The single-series bookkeeping bottleneck is repaired for "
                "retrospective development screening: all 12 pre-scoring "
                "pairs ran through identical candidate, baseline, timing, "
                "and cost rules. Promotion remains blocked because the "
                "window is retrospective and pair-level signs share a "
                "common exchange and market factor."
            ),
        },
        "external_actions": [],
    }
    payload["payload_sha256"] = BASE.stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["result_summary"]
    implementation = payload["implementation_summary"]
    lines = [
        "# Market-Signal Kraken Panel Benchmark",
        "",
        f"Protocol: `{payload['protocol_id']}`",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Status: `{payload['status']}`",
        f"Payload SHA-256: `{payload['payload_sha256']}`",
        "",
        "## Decision",
        "",
        "**No candidate is promoted.**",
        "",
        payload["boundary"],
        "",
        "## What Changed",
        "",
        (
            "- The earlier source-native sidecar had one series per source. "
            "This panel applies the same four candidates and four baselines "
            "to 12 pre-scoring Kraken pairs."
        ),
        (
            "- Pair selection used public 24-hour turnover with legacy "
            "alpha priority disabled, then removed stablecoin/fiat bases "
            "and duplicate quote variants."
        ),
        (
            "- Every pair has 720 hourly prices and "
            f"{implementation['evaluation_observation_count_per_series']} "
            "post-warmup scoring observations."
        ),
        "",
        "## Exact Scope",
        "",
        f"- Registered candidates: `{implementation['registered_candidate_count']}`",
        f"- Registered baselines: `{implementation['registered_baseline_count']}`",
        f"- Panel pairs: `{implementation['source_series_count']}`",
        (
            "- Strategy/pair results: "
            f"`{implementation['strategy_source_series_result_count']}`"
        ),
        (
            "- Candidate-baseline comparisons: "
            f"`{summary['candidate_source_baseline_comparison_count']}`"
        ),
        (
            "- Mean-positive comparisons: "
            f"`{summary['comparison_mean_win_count']}`"
        ),
        (
            "- Exploratory global-Holm positives: "
            f"`{summary['exploratory_global_holm_positive_count']}`"
        ),
        "- Promotions: `0`",
        "",
        "## Candidate Diagnostics",
        "",
        (
            "| Candidate | Mean wins / 4 | Holm positives / 4 | "
            "All-baseline mean win | All-baseline Holm win | Promotion |"
        ),
        "|---|---:|---:|---|---|---|",
    ]
    for row in payload["candidate_diagnostics"]:
        lines.append(
            "| `{candidate_family_id}` | {baseline_mean_win_count} | "
            "{global_holm_positive_count} | {mean_all} | {holm_all} | "
            "`BLOCKED` |".format(
                **row,
                mean_all=(
                    "yes"
                    if row["beats_every_baseline_on_mean"]
                    else "no"
                ),
                holm_all=(
                    "yes"
                    if row[
                        "beats_every_baseline_after_global_holm"
                    ]
                    else "no"
                ),
            )
        )
    lines.extend(
        [
            "",
            "## Panel Custody",
            "",
            "| Pair | Rows | 24h turnover at selection | SHA-256 |",
            "|---|---:|---:|---|",
        ]
    )
    for row in payload["inputs"]["panel_files"]:
        lines.append(
            f"| `{row['pair']}` | {row['row_count']} | "
            f"${row['turnover_24h_usd']:,.2f} | `{row['file_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- This is retrospective development evidence, not a prospective test.",
            "- Pairs share an exchange, timestamps, and a broad crypto market factor.",
            "- The fixed 10 bps turnover cost proxy excludes funding, borrow, latency, queue position, and market impact.",
            "- The panel-selection rule did not use these candidate or baseline scores, but turnover selection can still create universe-selection effects.",
            "- Any future challenger must be frozen before untouched or prospective scoring.",
            "",
            "## Safest Next Action",
            "",
            (
                "Use this panel only to choose a small challenger set and "
                "freeze it before collecting future bars. Keep the existing "
                "prospective time-series protocol unchanged."
            ),
        ]
    )
    return "\n".join(lines)


def write_outputs(
    payload: dict[str, Any],
    *,
    out_json: Path = OUT_JSON,
    dashboard_json: Path = DASHBOARD_JSON,
    manifest_json: Path = MANIFEST_JSON,
    doc_path: Path = DOC_PATH,
) -> dict[str, Any]:
    write_json(out_json, payload)
    write_json(dashboard_json, payload)
    write_text(doc_path, render_markdown(payload))
    manifest = {
        "schema": "market_signal_kraken_panel_benchmark_manifest_v1",
        "protocol_id": payload["protocol_id"],
        "payload_sha256": payload["payload_sha256"],
        "output": {
            "path": relative_path(out_json)
            if out_json.is_relative_to(ROOT)
            else str(out_json),
            "file_sha256": BASE.file_sha256(out_json),
        },
        "documentation": {
            "path": relative_path(doc_path)
            if doc_path.is_relative_to(ROOT)
            else str(doc_path),
            "file_sha256": BASE.file_sha256(doc_path),
        },
        "public_feed": {
            "path": relative_path(dashboard_json)
            if dashboard_json.is_relative_to(ROOT)
            else str(dashboard_json),
            "file_sha256": BASE.file_sha256(dashboard_json),
            "public_performance_claim_allowed": False,
        },
        "external_actions": [],
    }
    manifest["manifest_sha256"] = BASE.stable_sha256(manifest)
    write_json(manifest_json, manifest)
    return manifest


def check_current() -> dict[str, Any]:
    if not OUT_JSON.exists():
        raise FileNotFoundError(f"Missing current output: {OUT_JSON}")
    current = read_json(OUT_JSON)
    expected = build_payload(str(current["generated_utc"]))
    if current != expected:
        raise ValueError("Current Kraken-panel benchmark output is stale")
    if read_json(DASHBOARD_JSON) != current:
        raise ValueError("Kraken-panel dashboard payload is stale")
    if DOC_PATH.read_text(encoding="utf-8").rstrip() != (
        render_markdown(current).rstrip()
    ):
        raise ValueError("Kraken-panel documentation is stale")
    manifest = read_json(MANIFEST_JSON)
    if manifest["output"]["file_sha256"] != BASE.file_sha256(OUT_JSON):
        raise ValueError("Kraken-panel output manifest hash mismatch")
    if manifest["documentation"]["file_sha256"] != BASE.file_sha256(
        DOC_PATH
    ):
        raise ValueError("Kraken-panel documentation manifest hash mismatch")
    return {
        "status": "CURRENT",
        "payload_sha256": current["payload_sha256"],
        "panel_pair_count": current["implementation_summary"][
            "source_series_count"
        ],
        "promotion_count": current["result_summary"][
            "promotion_count"
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the hash-bound, retrospective multi-pair Kraken "
            "market-signal benchmark."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the current output, documentation, or manifest is stale.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check:
        result = check_current()
    else:
        payload = build_payload()
        write_outputs(payload)
        result = {
            "status": payload["status"],
            "payload_sha256": payload["payload_sha256"],
            "panel_pair_count": payload["implementation_summary"][
                "source_series_count"
            ],
            "comparison_count": payload["result_summary"][
                "candidate_source_baseline_comparison_count"
            ],
            "exploratory_global_holm_positive_count": payload[
                "result_summary"
            ]["exploratory_global_holm_positive_count"],
            "promotion_count": payload["result_summary"][
                "promotion_count"
            ],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
