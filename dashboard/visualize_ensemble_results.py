"""Render one verified offline ensemble run; no trading or performance claims.

Requires Plotly for HTML rendering (pip install plotly==6.3.0).
Run files are read-only, and the HTML destination must not already exist.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import math
from pathlib import Path
import re
import sys

SCHEMA = "lumencore.ensemble_past_only_research.v2"
ARTIFACTS = ("ensemble_evaluation_rows.csv", "ensemble_walkforward_results.csv")
MAX_BYTES = 32 * 1024 * 1024
ROW_COLUMNS = (
    "target_position", "decision_row", "target_row", "previous_price", "target_price",
    "raw_signal", "weight", "turnover", "price_return", "gross_score", "fee_cost",
    "slippage_cost", "net_score", "buy_hold_score", "cash_score",
)
BLOCK_COLUMNS = ("start", "end", "result", "bars", "gross_result", "estimated_cost", "buy_hold_result", "cash_result")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member in run receipt")
        result[key] = value
    return result


def _read(path, limit=MAX_BYTES):
    with Path(path).open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError("Run artifact exceeds the bounded reader limit")
    return content


def _number(value):
    if isinstance(value, bool):
        raise ValueError("Boolean cannot be a numeric score")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("All numeric fields must be finite")
    return number


def _integer(value, minimum=1, maximum=10000):
    number = _number(value)
    if not number.is_integer() or not minimum <= number <= maximum:
        raise ValueError("Invalid bounded integer")
    return int(number)


def _equal(actual, expected, field):
    if not math.isclose(_number(actual), expected, rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError(f"Run arithmetic does not reconcile: {field}")


def _csv(content, columns):
    text = content.decode("utf-8")
    if "\x00" in text:
        raise ValueError("CSV cannot contain NUL bytes")
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        if next(reader, []) != list(columns):
            raise ValueError("Unexpected run CSV columns")
        rows = []
        for record in reader:
            if len(record) != len(columns):
                raise ValueError("Malformed run CSV record")
            rows.append(dict(zip(columns, record)))
            if len(rows) > 10000:
                raise ValueError("Run CSV exceeds the row limit")
    except csv.Error as exc:
        raise ValueError("Malformed run CSV quoting") from exc
    if not rows:
        raise ValueError("Run CSV cannot be empty")
    return rows


def _reconcile(receipt, rows, blocks):
    config = receipt["configuration"]
    window = _integer(config["window"])
    step = _integer(config["reporting_step"])
    fee_bps, slippage_bps = (_number(config[key]) for key in ("fee_bps", "slippage_bps"))
    if not 0 <= fee_bps <= 10000 or not 0 <= slippage_bps <= 10000:
        raise ValueError("Invalid cost assumptions")
    if _integer(receipt["evaluated_transitions"]) != len(rows) or _integer(receipt["reporting_blocks"]) != len(blocks):
        raise ValueError("Run row counts do not reconcile")
    if _integer(receipt["input"]["rows"]) != window + len(rows):
        raise ValueError("Input and transition counts do not reconcile")
    prior_weight = 0.0
    for offset, row in enumerate(rows):
        for key in ROW_COLUMNS:
            if key not in ("decision_row", "target_row"):
                row[key] = _number(row[key])
        if row["target_position"] != window + offset:
            raise ValueError("Target transitions must be consecutive")
        if offset and row["decision_row"] != rows[offset - 1]["target_row"]:
            raise ValueError("Decision rows do not link consecutive transitions")
        old_price, new_price = row["previous_price"], row["target_price"]
        if min(old_price, new_price) <= 0:
            raise ValueError("Run prices must be positive")
        if offset:
            _equal(old_price, rows[offset - 1]["target_price"], "price continuity")
        weight = max(-1.0, min(1.0, row["raw_signal"]))
        turnover = abs(weight - prior_weight)
        price_return = new_price / old_price - 1.0
        fee, slippage = turnover * fee_bps / 10000.0, turnover * slippage_bps / 10000.0
        gross = weight * price_return
        buy_hold = price_return - ((fee_bps + slippage_bps) / 10000.0 if offset == 0 else 0.0)
        expected = {"weight": weight, "turnover": turnover, "price_return": price_return,
                    "fee_cost": fee, "slippage_cost": slippage, "gross_score": gross,
                    "net_score": gross - fee - slippage, "buy_hold_score": buy_hold, "cash_score": 0.0}
        for key, value in expected.items():
            _equal(row[key], value, key)
        prior_weight = weight
    if len(blocks) != math.ceil(len(rows) / step):
        raise ValueError("Reporting block count does not match reporting step")
    for index, block in enumerate(blocks):
        part = rows[index * step:(index + 1) * step]
        if block["start"] != part[0]["target_row"] or block["end"] != part[-1]["target_row"]:
            raise ValueError("Reporting block boundaries do not reconcile")
        expected = {
            "result": math.fsum(row["net_score"] for row in part),
            "bars": len(part), "gross_result": math.fsum(row["gross_score"] for row in part),
            "estimated_cost": math.fsum(row["fee_cost"] + row["slippage_cost"] for row in part),
            "buy_hold_result": math.fsum(row["buy_hold_score"] for row in part), "cash_result": 0.0,
        }
        for key, value in expected.items():
            _equal(block[key], value, key)
            block[key] = _number(block[key])
    _equal(receipt["net_score_sum"], math.fsum(row["net_score"] for row in rows), "receipt net total")
    _equal(receipt["buy_hold_score_sum"], math.fsum(row["buy_hold_score"] for row in rows), "receipt baseline total")


def read_verified_run(run_dir):
    """Verify internal custody and arithmetic, not origin or scientific validity."""
    root = Path(run_dir)
    receipt = json.loads(_read(root / "ensemble_run_receipt.json", 1024 * 1024).decode("utf-8"),
                         object_pairs_hook=_unique_object)
    if not isinstance(receipt, dict):
        raise ValueError("Run receipt must be an object")
    recorded = receipt.pop("receipt_sha256", None)
    if recorded != digest(canonical_json(receipt).encode()):
        raise ValueError("Run receipt hash mismatch")
    if receipt.get("schema") != SCHEMA or receipt.get("evidence_class") != "OFFLINE_RESEARCH_DIAGNOSTIC":
        raise ValueError("Unsupported run schema or evidence class")
    for key in ("execution_authorized", "scientific_performance_claim_supported",
                "independent_source_timing_verified", "parameter_selection_verified"):
        if receipt.get(key) is not False:
            raise ValueError("Run contains unsupported authority or evidence claims")
    if receipt.get("metric") != "additive_unitless_weighted_return_minus_assumed_turnover_cost":
        raise ValueError("Unsupported metric")
    chronology = "parsed_timestamp_order_only" if receipt["configuration"]["timestamp_column"] else "supplied_row_order_only"
    if receipt.get("chronology") != chronology:
        raise ValueError("Chronology disclosure does not match configuration")
    if not re.fullmatch("[0-9a-f]{64}", receipt["input"]["sha256"]):
        raise ValueError("Invalid input identity")
    if receipt["input"].get("kind") not in ("synthetic", "unverified_source"):
        raise ValueError("Unsupported input classification")
    code = receipt["code_sha256"]
    expected_code = {"dashboard/run_ensemble_meta_strategy.py",
                     "code/hybrid_harmonic_strategies.py", "code/hybrid_harmonic_algorithms.py",
                     "code/novel_harmonic_layers.py"}
    if set(code) != expected_code or any(not re.fullmatch("[0-9a-f]{64}", value) for value in code.values()):
        raise ValueError("Incomplete evaluator source identities")
    if set(receipt["artifacts"]) != set(ARTIFACTS):
        raise ValueError("Unexpected artifact set")
    verified = {}
    for name in ARTIFACTS:
        content = _read(root / name)
        if receipt["artifacts"][name] != {"bytes": len(content), "sha256": digest(content)}:
            raise ValueError("Run artifact hash or byte count mismatch")
        verified[name] = content
    rows = _csv(verified[ARTIFACTS[0]], ROW_COLUMNS)
    blocks = _csv(verified[ARTIFACTS[1]], BLOCK_COLUMNS)
    _reconcile(receipt, rows, blocks)
    receipt["receipt_sha256"] = recorded
    return receipt, rows, blocks


def render_html(receipt, rows, blocks):
    # Optional chart dependency stays out of validation and import side effects.
    import plotly.graph_objects as go
    from plotly.offline import get_plotlyjs

    fig = go.Figure()
    targets = [row["target_position"] for row in rows]
    for key, label, color, dash in (
        ("net_score", "Ensemble, after assumed costs", "#086f6f", "solid"),
        ("gross_score", "Ensemble, before assumed costs", "#74a4a4", "dot"),
        ("buy_hold_score", "Buy and hold, after assumed costs", "#a84f19", "solid"),
        ("cash_score", "Cash baseline", "#6b7280", "dash"),
    ):
        cumulative, total = [], 0.0
        for row in rows:
            total += row[key]
            cumulative.append(total)
        fig.add_trace(go.Scatter(x=targets, y=cumulative, name=label, mode="lines",
                                line={"color": color, "dash": dash}))
    fig.update_layout(template="plotly_white", title=None,
                      xaxis_title="Target row position in supplied input",
                      yaxis_title="Cumulative additive score (unitless)",
                      legend={"orientation": "h", "y": -0.25}, margin={"l": 65, "r": 25, "t": 20, "b": 130},
                      height=530, font={"family": "Arial", "size": 14})
    # Escape serialized values before embedding in an executable HTML context.
    figure_json = fig.to_json().replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    esc = lambda value: html.escape(str(value), quote=True)
    config = receipt["configuration"]
    input_label = "Synthetic software check" if receipt["input"]["kind"] == "synthetic" else "Unverified-source research"
    body_rows = "".join("<tr>" + "".join(f"<td>{esc(block[key])}</td>" for key in BLOCK_COLUMNS) + "</tr>" for block in blocks)
    source_rows = "".join(f"<li>{esc(name)}<br><code>{esc(value)}</code></li>" for name, value in receipt["code_sha256"].items())
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:,">
<title>LumenCore | Offline ensemble research diagnostic</title>
<style>
*{{box-sizing:border-box}}body{{font:16px/1.6 Arial,sans-serif;color:#172b35;background:#f3f6f7;margin:0}}
main{{max-width:1100px;margin:auto;padding:36px 24px}}h1{{font-size:32px;line-height:1.2}}
.kicker{{letter-spacing:.12em;font-size:12px;font-weight:bold;color:#086f6f}}
.card{{background:white;border:1px solid #dce5e8;border-radius:10px;padding:22px;margin:18px 0;min-width:0;overflow-wrap:anywhere}}
.notice{{border-left:5px solid #a84f19}}code{{overflow-wrap:anywhere;font-size:12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px}}
.metric{{font-size:24px;font-weight:bold}}.label{{font-size:13px;color:#536871}}
.scroll{{overflow:auto}}table{{border-collapse:collapse;min-width:860px;width:100%;font-size:12px}}
td,th{{border-bottom:1px solid #dce5e8;padding:9px;text-align:right}}th{{text-align:right}}
details summary{{cursor:pointer;font-weight:bold}}li{{margin:10px 0}}
@media(max-width:600px){{main{{padding:20px 12px}}h1{{font-size:26px}}.card{{padding:14px}}}}
</style></head><body><main>
<div class="kicker">LUMENCORE / RESEARCH EVIDENCE</div>
<h1>Offline ensemble research diagnostic</h1>
<p>Every decision uses the preceding {esc(config["window"])} input rows. Reporting blocks contain up to
{esc(config["reporting_step"])} transitions each.</p>
<div class="card notice"><strong>{input_label}. Exploratory research only.</strong> Scores are additive, unitless weighted returns.
They are not compounded returns or realized PnL. Source timestamps and parameter selection have not been independently
verified. Input classification is an operator declaration. These results do not establish alpha, investment value, independent validation, or execution authority.</div>
<div class="card grid">
<div><div class="label">Scored transitions</div><div class="metric">{len(rows)}</div></div>
<div><div class="label">Ensemble net score</div><div class="metric">{float(receipt["net_score_sum"]):.6f}</div></div>
<div><div class="label">Buy-and-hold score</div><div class="metric">{float(receipt["buy_hold_score_sum"]):.6f}</div></div>
<div><div class="label">One-way fee / slippage assumptions</div><div class="metric">{esc(config["fee_bps"])} / {esc(config["slippage_bps"])} bps</div></div>
</div><div class="card"><div id="score-chart" role="img" aria-label="Cumulative additive unitless scores for ensemble and baselines"></div></div>
<div class="card"><h2>What this run measures</h2>
<p>Each prior-window signal is clipped to a diagnostic weight between -1 and +1 and applied to the next observed price
transition. Costs equal absolute weight change times the explicit one-way fee and slippage assumptions. Initial weight is
flat; the final weight is not liquidated. Buy and hold uses the same transitions and one initial entry cost; cash scores zero.</p>
<p>This simplified close-to-close model does not measure achievable fills, financing, borrow, market impact, taxes, or
realized account performance. Strategy components retain their existing historical formulas and warm-up behavior.
The viewer checked file integrity and calculation consistency; a self-hash does not authenticate the author or input source.</p></div>
<div class="card"><details><summary>Verified reporting blocks ({len(blocks)})</summary><div class="scroll"><table>
<thead><tr>{''.join(f'<th>{esc(key)}</th>' for key in BLOCK_COLUMNS)}</tr></thead><tbody>{body_rows}</tbody></table></div></details></div>
<div class="card"><h2>Run identity</h2><p>Input: <strong>{esc(receipt["input"]["name"])}</strong><br>
Input SHA-256: <code>{esc(receipt["input"]["sha256"])}</code><br>
Receipt SHA-256: <code>{esc(receipt["receipt_sha256"])}</code><br>
Chronology: {esc(receipt["chronology"])}<br>Recorded runtime: {esc(canonical_json(receipt["runtime"]))}</p>
<details><summary>Recorded evaluator source hashes</summary><ul>{source_rows}</ul></details></div>
</main><script>{get_plotlyjs()}</script><script>
const figure={figure_json};
Plotly.newPlot("score-chart",figure.data,figure.layout,{{responsive:true,displaylogo:false}});
</script></body></html>"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New standalone HTML file")
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError("HTML destination already exists; overwrite is prohibited")
        receipt, rows, blocks = read_verified_run(args.run_dir)
        document = render_html(receipt, rows, blocks)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(document)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, OverflowError, ImportError) as exc:
        print(f"Visualization rejected: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote verified offline diagnostic chart to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
