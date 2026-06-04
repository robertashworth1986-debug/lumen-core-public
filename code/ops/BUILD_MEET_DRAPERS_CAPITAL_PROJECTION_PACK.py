from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "out" / "ops" / "meet_drapers_capital_projection"

TARGET_USD = 1_000_000.0
START_CAPITALS = [10_000.0, 50_000.0]
MONTHLY_SCENARIOS = [0.03, 0.05, 0.08, 0.10, 0.12, 0.15]
HORIZONS_MONTHS = [24, 36, 48, 60, 84, 120]
CURVE_MONTHS = 84
CURVE_Y_CAP = 1_500_000.0


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\n") + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def months_to_target(start_usd: float, target_usd: float, monthly_return: float) -> float | None:
    if start_usd <= 0 or target_usd <= start_usd:
        return 0.0
    if monthly_return <= 0:
        return None
    multiple = target_usd / start_usd
    return math.log(multiple) / math.log(1.0 + monthly_return)


def required_monthly_return(start_usd: float, target_usd: float, months: int) -> float | None:
    if start_usd <= 0 or target_usd <= start_usd or months <= 0:
        return None
    return (target_usd / start_usd) ** (1.0 / float(months)) - 1.0


def annualized_from_monthly(monthly_return: float) -> float:
    return (1.0 + monthly_return) ** 12 - 1.0


def fmt_money(value: float) -> str:
    return f"${value:,.0f}"


def fmt_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def build_projection_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for start_usd in START_CAPITALS:
        for monthly_return in MONTHLY_SCENARIOS:
            months = months_to_target(start_usd, TARGET_USD, monthly_return)
            years = (months / 12.0) if months is not None else None
            rows.append(
                {
                    "start_usd": start_usd,
                    "target_usd": TARGET_USD,
                    "monthly_return": monthly_return,
                    "annualized_return": annualized_from_monthly(monthly_return),
                    "months_to_target": months,
                    "years_to_target": years,
                }
            )
    return rows


def build_required_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for start_usd in START_CAPITALS:
        for months in HORIZONS_MONTHS:
            monthly = required_monthly_return(start_usd, TARGET_USD, months)
            if monthly is None:
                continue
            rows.append(
                {
                    "start_usd": start_usd,
                    "target_usd": TARGET_USD,
                    "horizon_months": months,
                    "required_monthly_return": monthly,
                    "required_annualized_return": annualized_from_monthly(monthly),
                }
            )
    return rows


def build_curve_points(start_usd: float, monthly_return: float, months: int, y_cap: float) -> list[tuple[int, float, float]]:
    points: list[tuple[int, float, float]] = []
    for m in range(0, months + 1):
        raw = start_usd * ((1.0 + monthly_return) ** m)
        clipped = min(raw, y_cap)
        points.append((m, raw, clipped))
    return points


def render_line_chart_svg(
    *,
    title: str,
    subtitle: str,
    y_max: float,
    x_max: int,
    target_line: float,
    series: dict[str, list[tuple[int, float, float]]],
) -> str:
    width, height = 1200, 700
    ml, mr, mt, mb = 90, 40, 90, 90
    iw = width - ml - mr
    ih = height - mt - mb

    def x_scale(v: float) -> float:
        return ml + (v / x_max) * iw

    def y_scale(v: float) -> float:
        return mt + ih - (v / y_max) * ih

    palette = ["#00429d", "#2e73b8", "#5fa2c7", "#8fcfb9", "#c2e7a2", "#f0f26b"]
    y_ticks = [0, 250000, 500000, 750000, 1000000, 1250000, 1500000]
    x_ticks = [0, 12, 24, 36, 48, 60, 72, 84]

    out: list[str] = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    out.append('<rect width="100%" height="100%" fill="#f8fafc"/>')
    out.append(f'<text x="{ml}" y="44" font-size="30" font-family="Segoe UI, Arial" fill="#0f172a" font-weight="700">{title}</text>')
    out.append(f'<text x="{ml}" y="70" font-size="16" font-family="Segoe UI, Arial" fill="#334155">{subtitle}</text>')

    out.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt + ih}" stroke="#334155" stroke-width="1.3"/>')
    out.append(f'<line x1="{ml}" y1="{mt + ih}" x2="{ml + iw}" y2="{mt + ih}" stroke="#334155" stroke-width="1.3"/>')

    for yt in y_ticks:
        y = y_scale(float(yt))
        out.append(f'<line x1="{ml}" y1="{y:.2f}" x2="{ml + iw}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>')
        out.append(f'<text x="{ml - 12}" y="{y + 5:.2f}" font-size="13" text-anchor="end" font-family="Segoe UI, Arial" fill="#475569">{fmt_money(float(yt))}</text>')

    for xt in x_ticks:
        x = x_scale(float(xt))
        out.append(f'<line x1="{x:.2f}" y1="{mt}" x2="{x:.2f}" y2="{mt + ih}" stroke="#e2e8f0" stroke-width="1"/>')
        out.append(f'<text x="{x:.2f}" y="{mt + ih + 24}" font-size="13" text-anchor="middle" font-family="Segoe UI, Arial" fill="#475569">{xt}m</text>')

    target_y = y_scale(target_line)
    out.append(f'<line x1="{ml}" y1="{target_y:.2f}" x2="{ml + iw}" y2="{target_y:.2f}" stroke="#dc2626" stroke-width="2" stroke-dasharray="8 6"/>')
    out.append(f'<text x="{ml + iw - 8}" y="{target_y - 8:.2f}" font-size="12" text-anchor="end" font-family="Segoe UI, Arial" fill="#dc2626">Target {fmt_money(target_line)}</text>')

    for idx, pts in enumerate(series.values()):
        color = palette[idx % len(palette)]
        poly = " ".join(f"{x_scale(m):.2f},{y_scale(y):.2f}" for (m, _raw, y) in pts)
        out.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="3"/>')

    legend_x = ml + 10
    legend_y = mt + 10
    for idx, label in enumerate(series.keys()):
        y = legend_y + idx * 24
        color = palette[idx % len(palette)]
        out.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 24}" y2="{y}" stroke="{color}" stroke-width="4"/>')
        out.append(f'<text x="{legend_x + 32}" y="{y + 5}" font-size="13" font-family="Segoe UI, Arial" fill="#1e293b">{label}</text>')

    out.append(f'<text x="{ml}" y="{height - 24}" font-size="12" font-family="Segoe UI, Arial" fill="#64748b">Y-axis is capped at {fmt_money(y_max)} for readability.</text>')
    out.append('</svg>')
    return "\n".join(out)


def render_bar_chart_svg(rows: list[dict[str, Any]]) -> str:
    width, height = 1200, 700
    ml, mr, mt, mb = 90, 40, 90, 110
    iw = width - ml - mr
    ih = height - mt - mb

    starts = START_CAPITALS
    horizons = HORIZONS_MONTHS

    value_map: dict[tuple[int, int], float] = {}
    max_val = 0.0
    for row in rows:
        s = int(row["start_usd"])
        h = int(row["horizon_months"])
        val = float(row["required_monthly_return"]) * 100.0
        value_map[(s, h)] = val
        max_val = max(max_val, val)
    max_val = max(15.0, max_val * 1.15)

    def y_scale(v: float) -> float:
        return mt + ih - (v / max_val) * ih

    group_w = iw / len(horizons)
    bar_w = group_w * 0.26
    gap = group_w * 0.08

    out: list[str] = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    out.append('<rect width="100%" height="100%" fill="#f8fafc"/>')
    out.append('<text x="90" y="44" font-size="30" font-family="Segoe UI, Arial" fill="#0f172a" font-weight="700">Required Monthly Return to Reach $1M</text>')
    out.append('<text x="90" y="70" font-size="16" font-family="Segoe UI, Arial" fill="#334155">Grouped by time horizon and starting capital.</text>')

    out.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt + ih}" stroke="#334155" stroke-width="1.3"/>')
    out.append(f'<line x1="{ml}" y1="{mt + ih}" x2="{ml + iw}" y2="{mt + ih}" stroke="#334155" stroke-width="1.3"/>')

    y_ticks = [0, 2, 4, 6, 8, 10, 12, 14]
    for yt in y_ticks:
        y = y_scale(float(yt))
        out.append(f'<line x1="{ml}" y1="{y:.2f}" x2="{ml + iw}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>')
        out.append(f'<text x="{ml - 12}" y="{y + 5:.2f}" font-size="13" text-anchor="end" font-family="Segoe UI, Arial" fill="#475569">{yt:.0f}%</text>')

    colors = {int(START_CAPITALS[0]): "#0ea5e9", int(START_CAPITALS[1]): "#f97316"}

    for idx, h in enumerate(horizons):
        gx = ml + idx * group_w
        x10 = gx + gap
        x50 = gx + gap + bar_w + gap

        v10 = value_map.get((int(starts[0]), h), 0.0)
        v50 = value_map.get((int(starts[1]), h), 0.0)
        y10 = y_scale(v10)
        y50 = y_scale(v50)

        out.append(f'<rect x="{x10:.2f}" y="{y10:.2f}" width="{bar_w:.2f}" height="{(mt + ih - y10):.2f}" fill="{colors[int(starts[0])]}"/>')
        out.append(f'<rect x="{x50:.2f}" y="{y50:.2f}" width="{bar_w:.2f}" height="{(mt + ih - y50):.2f}" fill="{colors[int(starts[1])]}"/>')

        out.append(f'<text x="{x10 + bar_w / 2:.2f}" y="{y10 - 8:.2f}" font-size="11" text-anchor="middle" font-family="Segoe UI, Arial" fill="#0f172a">{v10:.2f}%</text>')
        out.append(f'<text x="{x50 + bar_w / 2:.2f}" y="{y50 - 8:.2f}" font-size="11" text-anchor="middle" font-family="Segoe UI, Arial" fill="#0f172a">{v50:.2f}%</text>')

        out.append(f'<text x="{gx + group_w / 2:.2f}" y="{mt + ih + 28}" font-size="13" text-anchor="middle" font-family="Segoe UI, Arial" fill="#334155">{h} months</text>')

    legend_y = mt + 16
    out.append(f'<rect x="{ml + iw - 260}" y="{legend_y}" width="16" height="16" fill="{colors[int(starts[0])]}"/>')
    out.append(f'<text x="{ml + iw - 238}" y="{legend_y + 13}" font-size="13" font-family="Segoe UI, Arial" fill="#1e293b">Start {fmt_money(starts[0])}</text>')
    out.append(f'<rect x="{ml + iw - 120}" y="{legend_y}" width="16" height="16" fill="{colors[int(starts[1])]}"/>')
    out.append(f'<text x="{ml + iw - 98}" y="{legend_y + 13}" font-size="13" font-family="Segoe UI, Arial" fill="#1e293b">Start {fmt_money(starts[1])}</text>')

    out.append('</svg>')
    return "\n".join(out)


def build_markdown(generated_utc: str, projection_rows: list[dict[str, Any]], required_rows: list[dict[str, Any]], chart_10k: Path, chart_50k: Path, chart_req: Path) -> str:
    lines: list[str] = []
    lines.append("# Meet The Drapers Capital Projection Pack")
    lines.append("")
    lines.append(f"Generated UTC: {generated_utc}")
    lines.append("")
    lines.append("## Key Frame")
    lines.append(f"- Target: {fmt_money(TARGET_USD)}")
    lines.append(f"- Case A: {fmt_money(START_CAPITALS[0])} to {fmt_money(TARGET_USD)} requires 100x capital multiple")
    lines.append(f"- Case B: {fmt_money(START_CAPITALS[1])} to {fmt_money(TARGET_USD)} requires 20x capital multiple")
    lines.append("")
    lines.append("## Scenario Timelines")
    lines.append("")
    lines.append("| Start | Monthly Return | Annualized Return | Months to $1M | Years to $1M |")
    lines.append("|---:|---:|---:|---:|---:|")
    for row in projection_rows:
        months = row["months_to_target"]
        years = row["years_to_target"]
        months_cell = f"{months:.1f}" if months is not None else "n/a"
        years_cell = f"{years:.2f}" if years is not None else "n/a"
        lines.append(f"| {fmt_money(row['start_usd'])} | {fmt_pct(row['monthly_return'])} | {fmt_pct(row['annualized_return'])} | {months_cell} | {years_cell} |")
    lines.append("")
    lines.append("## Required Return by Deadline")
    lines.append("")
    lines.append("| Start | Horizon | Required Monthly Return | Required Annualized Return |")
    lines.append("|---:|---:|---:|---:|")
    for row in required_rows:
        lines.append(f"| {fmt_money(row['start_usd'])} | {int(row['horizon_months'])} months | {fmt_pct(row['required_monthly_return'])} | {fmt_pct(row['required_annualized_return'])} |")
    lines.append("")
    lines.append("## Charts")
    lines.append(f"- [Growth Curves (Start {fmt_money(START_CAPITALS[0])})]({chart_10k.name})")
    lines.append(f"- [Growth Curves (Start {fmt_money(START_CAPITALS[1])})]({chart_50k.name})")
    lines.append(f"- [Required Monthly Return by Horizon]({chart_req.name})")
    lines.append("")
    lines.append("## Investor Readout")
    lines.append("- 10% monthly compounding projects roughly 48.3 months from $10k to $1M and 31.4 months from $50k to $1M.")
    lines.append("- 5% monthly compounding projects roughly 94.4 months from $10k to $1M and 61.4 months from $50k to $1M.")
    lines.append("- This is deterministic compounding math. Real results depend on risk controls, slippage, liquidity, and execution quality.")
    lines.append("")
    return "\n".join(lines)


def build_html_index(generated_utc: str, md_path: Path, json_path: Path, charts: list[Path]) -> str:
    links = "\n".join(f'<li><a href="{p.name}">{p.name}</a></li>' for p in charts)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Meet The Drapers Projection Pack</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 2rem; background: #f8fafc; color: #0f172a; }}
    .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 1rem 1.2rem; margin-bottom: 1rem; max-width: 820px; }}
    a {{ color: #0f766e; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>Meet The Drapers Projection Pack</h1>
    <p>Generated UTC: {generated_utc}</p>
    <ul>
      <li><a href=\"{md_path.name}\">{md_path.name}</a></li>
      <li><a href=\"{json_path.name}\">{json_path.name}</a></li>
    </ul>
  </div>
  <div class=\"card\">
    <h2>Charts</h2>
    <ul>
      {links}
    </ul>
  </div>
</body>
</html>
"""


def main() -> int:
    generated_utc = now_iso()
    run_tag = now_tag()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    projection_rows = build_projection_rows()
    required_rows = build_required_rows()

    series_10k: dict[str, list[tuple[int, float, float]]] = {}
    series_50k: dict[str, list[tuple[int, float, float]]] = {}
    for scenario in MONTHLY_SCENARIOS:
        label = f"{scenario * 100:.0f}% monthly"
        series_10k[label] = build_curve_points(START_CAPITALS[0], scenario, CURVE_MONTHS, CURVE_Y_CAP)
        series_50k[label] = build_curve_points(START_CAPITALS[1], scenario, CURVE_MONTHS, CURVE_Y_CAP)

    chart_10k_name = f"growth_curve_10k_to_1m_{run_tag}.svg"
    chart_50k_name = f"growth_curve_50k_to_1m_{run_tag}.svg"
    chart_req_name = f"required_monthly_return_{run_tag}.svg"

    chart_10k_path = OUT_DIR / chart_10k_name
    chart_50k_path = OUT_DIR / chart_50k_name
    chart_req_path = OUT_DIR / chart_req_name

    write_text(chart_10k_path, render_line_chart_svg(title="Compounding Curves: $10k to $1M", subtitle="Monthly compounding scenarios over 84 months. Curves are clipped at $1.5M for readability.", y_max=CURVE_Y_CAP, x_max=CURVE_MONTHS, target_line=TARGET_USD, series=series_10k))
    write_text(chart_50k_path, render_line_chart_svg(title="Compounding Curves: $50k to $1M", subtitle="Monthly compounding scenarios over 84 months. Curves are clipped at $1.5M for readability.", y_max=CURVE_Y_CAP, x_max=CURVE_MONTHS, target_line=TARGET_USD, series=series_50k))
    write_text(chart_req_path, render_bar_chart_svg(required_rows))

    projection_csv_tagged = OUT_DIR / f"scenario_projection_{run_tag}.csv"
    projection_csv_latest = OUT_DIR / "scenario_projection_latest.csv"
    required_csv_tagged = OUT_DIR / f"required_return_{run_tag}.csv"
    required_csv_latest = OUT_DIR / "required_return_latest.csv"

    write_csv(projection_csv_tagged, projection_rows, ["start_usd", "target_usd", "monthly_return", "annualized_return", "months_to_target", "years_to_target"])
    write_csv(projection_csv_latest, projection_rows, ["start_usd", "target_usd", "monthly_return", "annualized_return", "months_to_target", "years_to_target"])
    write_csv(required_csv_tagged, required_rows, ["start_usd", "target_usd", "horizon_months", "required_monthly_return", "required_annualized_return"])
    write_csv(required_csv_latest, required_rows, ["start_usd", "target_usd", "horizon_months", "required_monthly_return", "required_annualized_return"])

    payload = {
        "generated_utc": generated_utc,
        "run_tag": run_tag,
        "scope": "meet_drapers_capital_projection_pack",
        "target_usd": TARGET_USD,
        "start_capitals_usd": START_CAPITALS,
        "monthly_scenarios": MONTHLY_SCENARIOS,
        "curve_horizon_months": CURVE_MONTHS,
        "required_return_horizons_months": HORIZONS_MONTHS,
        "scenario_projection": projection_rows,
        "required_returns": required_rows,
        "artifacts": {
            "chart_growth_10k": chart_10k_name,
            "chart_growth_50k": chart_50k_name,
            "chart_required_returns": chart_req_name,
            "scenario_projection_csv": projection_csv_tagged.name,
            "required_return_csv": required_csv_tagged.name,
        },
        "notes": [
            "Deterministic compounding model only.",
            "Does not include slippage, spread, execution impact, taxes, or downtime.",
            "Use as pitch-frame math, not a return guarantee.",
        ],
    }

    json_tagged = OUT_DIR / f"meet_drapers_capital_projection_{run_tag}.json"
    json_latest = OUT_DIR / "meet_drapers_capital_projection_latest.json"
    write_json(json_tagged, payload)
    write_json(json_latest, payload)

    md_tagged = OUT_DIR / f"meet_drapers_capital_projection_{run_tag}.md"
    md_latest = OUT_DIR / "meet_drapers_capital_projection_latest.md"
    md_text = build_markdown(generated_utc, projection_rows, required_rows, chart_10k_path, chart_50k_path, chart_req_path)
    write_text(md_tagged, md_text)
    write_text(md_latest, md_text)

    html_tagged = OUT_DIR / f"meet_drapers_capital_projection_{run_tag}.html"
    html_latest = OUT_DIR / "meet_drapers_capital_projection_latest.html"
    html_text = build_html_index(generated_utc, md_tagged, json_tagged, [chart_10k_path, chart_50k_path, chart_req_path])
    write_text(html_tagged, html_text)
    write_text(html_latest, html_text)

    print("BUILD_MEET_DRAPERS_CAPITAL_PROJECTION_PACK")
    print(f"json_latest={json_latest}")
    print(f"md_latest={md_latest}")
    print(f"html_latest={html_latest}")
    print(f"chart_growth_10k={chart_10k_path}")
    print(f"chart_growth_50k={chart_50k_path}")
    print(f"chart_required_returns={chart_req_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
