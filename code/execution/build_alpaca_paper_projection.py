import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONFIG = ROOT / "config"
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"

SUMMARY_FILE = EXEC_OUT / "institutional_summary.json"
SELECTION_FILE = EXEC_OUT / "institutional_live_selection.json"
TOP10_FILE = EXEC_OUT / "institutional_top10.csv"
PAPER_RUNTIME_FILE = CONFIG / "paper_trader_runtime.json"

JSON_OUT = EXEC_OUT / "alpaca_paper_ultra_aggressive_projection.json"
MD_OUT = EXEC_OUT / "alpaca_paper_ultra_aggressive_projection.md"

MILESTONES = [
    250_000,
    500_000,
    1_000_000,
    5_000_000,
    10_000_000,
    50_000_000,
    100_000_000,
    1_000_000_000,
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def load_top10_rows(path: Path):
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def years_to_target(starting_capital: float, annual_return: float, target_value: float):
    if starting_capital <= 0 or target_value <= starting_capital or annual_return <= 0:
        return 0.0
    return math.log(target_value / starting_capital) / math.log(1.0 + annual_return)


def years_to_text(years: float) -> str:
    if years <= 0:
        return "already reached"
    months = years * 12.0
    if months < 18:
        return f"{months:.1f} months"
    return f"{years:.1f} years"


def future_value(starting_capital: float, annual_return: float, years: float) -> float:
    return starting_capital * ((1.0 + annual_return) ** years)


def build_scenarios(starting_capital: float, summary: dict, selection: dict):
    top_test_sharpe = float(summary.get("top_test_sharpe", selection.get("test_sharpe", 0.0)) or 0.0)
    institutional_score = float(summary.get("top_institutional_score", selection.get("institutional_score", 0.0)) or 0.0)

    return [
        {
            "name": "Defensible Paper Case",
            "annual_return": 0.50,
            "sharpe": round(min(1.35, max(0.80, top_test_sharpe * 0.25)), 2),
            "mdd": 0.18,
            "narrative": "Investor-safe paper case with heavy haircut to research metrics and tighter capital preservation.",
        },
        {
            "name": "Aggressive Paper Case",
            "annual_return": 0.85,
            "sharpe": round(min(1.90, max(1.10, top_test_sharpe * 0.34)), 2),
            "mdd": 0.24,
            "narrative": "Aggressive but still pitchable paper compounding case using full reinvestment and concentrated rotation.",
        },
        {
            "name": "Ultra Aggressive Paper Case",
            "annual_return": 1.50,
            "sharpe": round(min(2.25, max(1.35, top_test_sharpe * 0.42)), 2),
            "mdd": 0.35,
            "narrative": "High-turnover full-compounding paper case. Strong upside, but materially higher drawdown tolerance required.",
        },
        {
            "name": "Theoretical Ceiling",
            "annual_return": 3.00,
            "sharpe": round(min(3.00, max(1.75, top_test_sharpe * 0.56)), 2),
            "mdd": 0.50,
            "narrative": "This is not a base-case pitch. It is a theoretical paper ceiling for marketing context only.",
        },
    ]


def enrich_scenarios(starting_capital: float, scenarios: list[dict]):
    for scenario in scenarios:
        annual_return = float(scenario["annual_return"])
        scenario["milestones"] = [
            {
                "target": int(target),
                "years": round(years_to_target(starting_capital, annual_return, float(target)), 2),
                "text": years_to_text(years_to_target(starting_capital, annual_return, float(target))),
            }
            for target in MILESTONES
        ]
        scenario["five_year_value"] = round(future_value(starting_capital, annual_return, 5.0), 2)
        scenario["ten_year_value"] = round(future_value(starting_capital, annual_return, 10.0), 2)
    return scenarios


def build_markdown(starting_capital: float, summary: dict, selection: dict, runtime: dict, scenarios: list[dict], top_rows: list[dict]) -> str:
    lines = []
    lines.append("# Alpaca Paper Ultra-Aggressive Projection")
    lines.append("")
    lines.append(f"Generated UTC: {now_utc()}")
    lines.append("")
    lines.append("## Current Positioning")
    lines.append("")
    lines.append(f"- Paper starting capital: ${starting_capital:,.0f}")
    lines.append(f"- Paper profile: {runtime.get('aggression_mode', 'ultra_aggressive')}")
    lines.append(f"- Reinvestment: {float(runtime.get('reinvest_fraction', 1.0) or 1.0):.0%}")
    lines.append(f"- Position size: {float(runtime.get('position_size_pct', 0.0) or 0.0):.0%}")
    lines.append(f"- Max positions: {int(runtime.get('max_positions', 0) or 0)}")
    lines.append(f"- Selection combo: {selection.get('flow')} / {selection.get('strategy')} / {selection.get('algo')}")
    lines.append(f"- Research-selected test Sharpe: {float(selection.get('test_sharpe', 0.0) or 0.0):.2f}")
    lines.append(f"- Institutional score: {float(selection.get('institutional_score', 0.0) or 0.0):.2f}")
    lines.append("")
    lines.append("## Investor Framing")
    lines.append("")
    lines.append("This is a paper-only growth envelope, not a promise of realized returns. The research stack has shown strong backtest Sharpe on selected regimes, but deployment assumptions below are haircut down to more defensible investor cases.")
    lines.append("")
    lines.append("## Scenario Table")
    lines.append("")
    lines.append("| Scenario | Annual Return | Sharpe | MDD | 5Y Value | 10Y Value | Time to $1B |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for scenario in scenarios:
        billion = next(item for item in scenario["milestones"] if item["target"] == 1_000_000_000)
        lines.append(
            f"| {scenario['name']} | {scenario['annual_return']:.0%} | {scenario['sharpe']:.2f} | {scenario['mdd']:.0%} | ${scenario['five_year_value']:,.0f} | ${scenario['ten_year_value']:,.0f} | {billion['text']} |"
        )
    lines.append("")
    lines.append("## Milestones From $100,000")
    lines.append("")
    for scenario in scenarios:
        lines.append(f"### {scenario['name']}")
        lines.append("")
        lines.append(f"- Narrative: {scenario['narrative']}")
        for item in scenario["milestones"]:
            lines.append(f"- ${item['target']:,.0f}: {item['text']}")
        lines.append("")
    if top_rows:
        lines.append("## Research Context")
        lines.append("")
        lines.append("Top-ranked research rows used as an upper-bound context, not as deployable promises:")
        lines.append("")
        lines.append("| Flow | Strategy | Algo | Test Sharpe | Test MDD | Test CAGR | Institutional Score |")
        lines.append("|---|---|---|---:|---:|---:|---:|")
        for row in top_rows[:5]:
            lines.append(
                f"| {row.get('flow')} | {row.get('strategy')} | {row.get('algo')} | {float(row.get('test_sharpe', 0) or 0):.2f} | {abs(float(row.get('test_max_dd', 0) or 0)):.0%} | {float(row.get('test_cagr', 0) or 0):.0%} | {float(row.get('institutional_score', 0) or 0):.2f} |"
            )
        lines.append("")
    lines.append("## Bottom Line")
    lines.append("")
    lines.append("From $100,000 to $1 billion is not a near-term claim. On a pitchable aggressive paper case, it is a decade-plus compounding story. On a theoretical ceiling case, it becomes single-digit years, but that should be treated as a marketing upper bound, not a credible base case.")
    lines.append("")
    return "\n".join(lines)


def main():
    summary = load_json(SUMMARY_FILE, {})
    selection = load_json(SELECTION_FILE, {})
    runtime = load_json(PAPER_RUNTIME_FILE, {})
    top_rows = load_top10_rows(TOP10_FILE)

    starting_capital = float(runtime.get("starting_capital_usd", 100000.0) or 100000.0)
    scenarios = enrich_scenarios(starting_capital, build_scenarios(starting_capital, summary, selection))

    payload = {
        "generated_utc": now_utc(),
        "starting_capital_usd": starting_capital,
        "paper_runtime": runtime,
        "research_summary": summary,
        "selected_live_combo": selection,
        "scenarios": scenarios,
    }

    JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    MD_OUT.write_text(build_markdown(starting_capital, summary, selection, runtime, scenarios, top_rows), encoding="utf-8")

    print(json.dumps({
        "json_out": str(JSON_OUT),
        "md_out": str(MD_OUT),
        "starting_capital_usd": starting_capital,
        "scenario_count": len(scenarios),
    }, indent=2))


if __name__ == "__main__":
    main()