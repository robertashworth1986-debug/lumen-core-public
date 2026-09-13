#!/usr/bin/env python3
"""Build connected, dated public research views. Reads files; never calls an API.

Replaces the eight legacy redirect stubs with reviewer views. The archived full
operator interfaces remain in Git history; no private operator route is restored.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "c3bddd48768a23acdce727246291d48a62984ed8"
ARCHIVE_COMMIT = "987e37ea47858c9c7dcc03f179f859f78fc9e995"
REPO = "https://github.com/robertashworth1986-debug/lumen-core-public"
REVIEW_DATE = "2026-09-13"
INPUT_DIGESTS = {
    'config/live_source_registry.json': '29710b87b16c1d44150247175dcd2b46be4e304431fcd2d366358321369c32f9',
    'dashboard/level4_live_summary.json': '86d0b5340fb773addab3e14545d163cb0eea520a1fd452be81244c6a85186613',
    'dashboard/level6_paper_guardrail.json': 'd93edbd9d309ae7bcb7fcd6b23cbc1748a151daf087e5c0949e082d65f126442',
    'investor_txids/trade_log.json': '2649f3c279a422e19585dc1e4440640603fc08d7e3be1e7ed732daff45dce8b0',
    'gen4_validate_scale/validated_champion.json': '46e84c677be8df231c3a9709ad56912c1c5fb3f3844b70bc21d2f61b5123358f',
}
PAGES = {
    "mission_control.html": ("Mission Control", "One connected view of the build.", "Evidence breadth, research, funding workflows and the next review decision."),
    "quant_lab.html": ("Quant Lab", "Follow the research through every gate.", "Candidate selection, historical tests, later guardrails and source lineage in one workspace."),
    "kraken_execution_dashboard.html": ("Kraken Research & Execution Evidence", "Real order records. Traceable research.", "Historical TXIDs sit alongside candidate results and follow-on outcomes."),
    "grants.html": ("Grant Factory", "Turn evidence into reviewable applications.", "Discovery, qualification, drafting, budgets, proof bundles and submission tracking."),
    "forecast.html": ("Forecast Research", "A forecast needs a fair comparison.", "Trace data windows, incumbent baselines, holdouts and cost assumptions before judging an improvement."),
    "anomalies.html": ("Anomaly & Source Review", "Keep data health beside the result.", "Stored source breadth and runtime availability answer different questions."),
    "explain.html": ("Evidence Explainer", "Understand what each result establishes.", "Inspect the source, its date, its evidence class and the decision it supports."),
    "lab.html": ("Research & Proof Lab", "Carry the build into a bounded review.", "Connect model experiments, implementation evidence and reviewer-readable Proof Capsules."),
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def source(path: str, label: str, ref: str = SOURCE_COMMIT) -> str:
    return f'<a href="{REPO}/blob/{ref}/{esc(path)}">{esc(label)}</a>'


def read(root: Path, path: str):
    data = json.loads((root / path).read_text(encoding="utf-8"))
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if digest != INPUT_DIGESTS[path]:
        raise ValueError(f"Evidence changed: {path}; review source commit, dates and interpretation before rebuilding")
    return data


def table(headers: list[str], rows: list[list[str]], caption: str) -> str:
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    body = "".join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
    return f'<div class="table-scroll" tabindex="0" role="region" aria-label="{esc(caption)}"><table><caption>{esc(caption)}</caption><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def section(title: str, body: str, anchor: str = "") -> str:
    return f'<section class="panel" id="{esc(anchor or title.lower().replace(" ", "-"))}"><h2>{esc(title)}</h2>{body}</section>'


def research(root: Path) -> str:
    selected = read(root, "dashboard/level4_live_summary.json")["capital_weights"]
    guard = read(root, "dashboard/level6_paper_guardrail.json")
    later = {(r["pair"], r["strategy"]): r for r in guard["top_candidates"]}
    rows = []
    for item in selected:
        follow = later.get((item["pair"], item["strategy"]))
        rows.append([esc(item["pair"]), esc(item["strategy"]), f'{item["test_mc_sharpe"]:.3f}',
                     f'{item["test_max_dd"]:.3f}',
                     f'{follow["live_sharpe_now"]:.3f}' if follow else 'Unknown',
                     'HELD' if follow and follow["approved"] is False else 'Review required'])
    body = '<p>Positive historical candidate results are part of the research record. The subsequent paper guardrail approved zero of these five candidates and observed zero paper-trade events. The two stages must be read together.</p>'
    body += table(["Pair", "Strategy", "Test MC Sharpe", "Test max DD (fraction)", "Follow-on Sharpe", "Guardrail"], rows, "Historical selection and March 26, 2026 paper guardrail")
    body += '<p class="note">The follow-on source calls its metric “live_sharpe_now”; this paper guardrail is not a verified live-account return. Test windows, annualization, costs and original market inputs are not fully specified in these summary files. LIVE_ALLOCATION_READY is an archived label, not current approval.</p>'
    body += '<p>' + source('dashboard/level4_live_summary.json', 'Candidate summary') + ' · ' + source('dashboard/level6_paper_guardrail.json', 'Follow-on guardrail') + '</p>'
    zec = read(root, 'gen4_validate_scale/validated_champion.json')
    body += '<p><strong>ZEC/USD trend:</strong> the validated-champion file reports Sharpe ' + esc(round(zec['sharpe'], 3)) + '. Gen5 stress results vary by half-window; this candidate needs the same cost and holdout review. ' + source('gen5_output/gen5_champion.json', 'Gen5 stress source') + '</p>'
    return section('Candidate research and later outcomes', body, 'research')


def execution(root: Path) -> str:
    rows = read(root, 'investor_txids/trade_log.json')
    unique = {row['txid']: row for row in rows}
    body = '<p><strong>' + str(len(unique)) + ' distinct order IDs</strong> are recorded on April 5, 2026 across SOLUSD, ADAUSD and SPXUSD. The log labels them LIVE and CLOSED. These are first-party records; order-to-fill and fee reconciliation remains open.</p>'
    body += table(['UTC timestamp', 'Pair', 'Side', 'Recorded TXID'], [[esc(r['timestamp']), esc(r['pair']), esc(r['side']), '<code>'+esc(r['txid'])+'</code>'] for r in unique.values()], 'Historical order records')
    body += '<p class="note">Each row repeats its entry price as its exit price and reports zero PnL. That is insufficient to conclude the trades broke even. No strategy-level net profit is asserted from this log.</p>'
    body += '<p>' + source('investor_txids/trade_log.json', 'Original order log') + ' · <a href="https://docs.kraken.com/api-reference/account-data/get-trades-history">Kraken fill and fee fields</a></p>'
    body += '<p><strong>Next accounting step:</strong> join order IDs to venue fills and closing trades, retain fees and currency, and associate each order with the strategy decision that caused it.</p>'
    return section('Historical Kraken execution evidence', body, 'execution')


def breadth(root: Path) -> str:
    registry = read(root, 'config/live_source_registry.json')
    rows = registry['rows']
    total = sum(r['rows'] for r in rows if r['evidence_basis'] == 'MEASURED_FILE_MATCH')
    body = f'<p><strong>{total:,} stored row references</strong> across 12 measured-file-match entries in the June 10, 2026 registry. Five additional entries are credential-only with zero measured rows. Counts are not deduplicated and do not establish current feed health.</p>'
    body += table(['Source', 'Sector', 'Stored rows', 'Evidence basis'], [[esc(r['source']), esc(r['sector']), f"{r['rows']:,}", esc(r['evidence_basis'])] for r in rows], 'Dated source registry — 2026-06-10')
    body += '<p>' + source('config/live_source_registry.json', 'Original registry') + '</p>'
    return section('Measured source breadth', body, 'breadth')


def connections() -> str:
    cards = ''.join(f'<a class="module" href="/{route}"><strong>{esc(info[0])}</strong><span>{esc(info[2])}</span></a>' for route, info in PAGES.items())
    return section('Connected workspaces', '<div class="modules">'+cards+'</div><p><a href="/cohort/">Cohort tools: Grant Factory, LumaScout and PaperLab</a> · <a href="/build_week/prooflock_console/">ProofLock Console</a> · <a href="/external_review.html">External review</a> · <a href="/evidence/">Public evidence</a></p>', 'connections')


def grants() -> str:
    stages = [
        ['Discover', 'Search official funding sources and retain opportunity identifiers.'],
        ['Qualify', 'Check applicant eligibility, scope, deadlines and required partners.'],
        ['Draft', 'Reuse technical volume, commercialization, cover letter and budget work.'],
        ['Package', 'Attach measured evidence, manifests and version comparisons.'],
        ['Review', 'Show missing facts, approvals and submission requirements.'],
        ['Track', 'Record actual portal receipts separately from drafts and outreach.'],
    ]
    return section('Grant Factory workflow', '<p>Grant Factory is an implemented software and workflow asset. Its value can be tested through application preparation time, missing-field rates, reuse and buyer willingness to pay.</p>'+table(['Stage','Implemented workflow purpose'],stages,'Evidence-to-application workflow')+'<p><a href="/cohort/#grants">Open cohort Grant Factory</a> · <a href="/opportunity_sprint.html">Funding workflow review</a> · '+source('dashboard/grants.html','Full historical Grant Lab',ARCHIVE_COMMIT)+'</p><p class="note">These views do not submit applications. Draft packages, submitted applications, awards and revenue have separate statuses. Private workspace contents are not published here.</p>', 'grants')


def methodology() -> str:
    return section('Research methods and evidence lineage', table(['Research family','Implemented scope','Review requirement'],[
        ['Generation 4–7 selection','Mean reversion, trend, validation, stress and shadow-state artifacts.','Keep positive and negative windows; recover raw inputs and fees.'],
        ['Multi-timeframe alpha map','Kraken pair screening, spread, trend and movement diagnostics.','A ranking score is not out-of-sample trading profit.'],
        ['Movement clusters','Time-of-day and weekday clustering of market moves.','Measure history coverage and selection effects.'],
        ['Symbol timing model','Chronological training/holdout analysis and round-trip cost assumptions.','Requires history and sample support; inspect held results.'],
        ['Edge truth guard','Checks baseline-relative results, sample size and implausible metrics.','Preserve fail/hold verdicts.'],
        ['Proof Capsule','Source identity, metric, threshold, holdout and prohibited claims.','Lock the review protocol before scoring.'],
    ], 'From exploratory research to a bounded claim')+'<p>'+source('UNIFIED_TRADING_QUICKSTART.md','Maintained trading research map','main')+' · '+source('code/ops/build_symbol_timing_edge_model.py','Timing model source')+' · '+source('code/edge_truth_guard.py','Edge truth guard')+'</p>', 'methods')


CSS = '''
:root{color-scheme:dark;--ink:#edf4ff;--muted:#b1c4da;--line:#304962;--panel:#0e2034;--accent:#78e1cf;--gold:#efc477}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 80% 0%,#173656,transparent 58%),#07121f;color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif;line-height:1.55}a{color:var(--accent);text-underline-offset:3px}a:focus-visible,[tabindex]:focus-visible{outline:3px solid var(--gold);outline-offset:4px}.skip{position:absolute;left:16px;top:-80px}.skip:focus{top:12px;z-index:9999}.review-wrap{max-width:1280px;margin:auto;padding:36px 28px 72px}.eyebrow{color:var(--accent);letter-spacing:.13em;text-transform:uppercase;font-size:12px;font-weight:700}.hero{border:1px solid var(--line);border-radius:24px;padding:32px;background:linear-gradient(120deg,#16354fdd,#0d1b2bee);position:relative;overflow:hidden}.hero h1{font-size:clamp(32px,5vw,58px);line-height:1.07;letter-spacing:-.04em;margin:16px 0;max-width:850px}.hero p{max-width:850px;color:var(--muted)}.badge{display:inline-block;border:1px solid #796445;color:var(--gold);border-radius:99px;padding:6px 12px;font-size:12px}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}.metric{padding:22px;border:1px solid var(--line);border-radius:16px;background:#0b1b2b}.metric strong{display:block;font-size:30px;color:var(--accent);font-variant-numeric:tabular-nums}.metric span{color:var(--muted);font-size:13px}.panel{border:1px solid var(--line);background:var(--panel);padding:24px;border-radius:20px;margin-top:20px}.panel h2{margin:0 0 16px;font-size:23px}.panel p{color:var(--muted)}.modules{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.module{display:block;border:1px solid var(--line);border-radius:12px;padding:18px;text-decoration:none;background:#102a3b}.module:hover{border-color:var(--accent)}.module strong,.module span{display:block}.module span{font-size:13px;color:var(--muted);margin-top:6px}.table-scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px}caption{text-align:left;color:var(--muted);padding:0 0 12px}th{text-align:left;color:var(--accent);background:#092033}th,td{padding:12px 10px;border-bottom:1px solid var(--line);vertical-align:top}td{overflow-wrap:anywhere}code{font-size:12px}.note{font-size:12px}.source-footer{margin-top:30px;color:var(--muted);font-size:12px;overflow-wrap:anywhere}.compact-nav{display:flex;gap:16px;flex-wrap:wrap;margin:20px 0}.archived{border-left:3px solid var(--gold);padding-left:16px}@media(max-width:700px){.review-wrap{padding:20px 14px 48px}.hero,.panel{padding:20px}.metrics,.modules{grid-template-columns:1fr}.metric strong{font-size:27px}td,th{padding:9px 8px}}@media print{body{background:white;color:#112c42}.lcf-rail,.lcf-topbar,.compact-nav{display:none!important}.review-wrap{padding:0}.hero,.panel,.metric,.module{background:white;border-color:#ccc;color:#112c42;break-inside:avoid}.hero p,.panel p,.module span,.metric span,caption,.source-footer{color:#43566a}a,.metric strong,th{color:#087f85}th{background:#eef4f6}}
'''


def render_page(root: Path, route: str) -> str:
    label, title, description = PAGES[route]
    registry = read(root, 'config/live_source_registry.json')['rows']
    total = sum(r['rows'] for r in registry if r['evidence_basis']=='MEASURED_FILE_MATCH')
    count = len({r['txid'] for r in read(root,'investor_txids/trade_log.json')})
    metrics = f'<div class="metrics"><div class="metric"><strong>{total:,}</strong><span>June 10 stored row references</span></div><div class="metric"><strong>{count}</strong><span>April 5 recorded order IDs</span></div><div class="metric"><strong>HOLD</strong><span>Field validation and production readiness unestablished</span></div></div>'
    selected = {
        'mission_control.html': [connections, lambda:breadth(root), lambda:research(root), grants],
        'quant_lab.html': [lambda:research(root),methodology,connections],
        'kraken_execution_dashboard.html': [lambda:execution(root),lambda:research(root),methodology,connections],
        'grants.html':[grants,connections],
        'forecast.html':[methodology,lambda:research(root),connections],
        'anomalies.html':[lambda:breadth(root),methodology,connections],
        'explain.html':[methodology,lambda:execution(root),connections],
        'lab.html':[methodology,connections],
    }[route]
    content=''.join(fn() for fn in selected)
    nav=''.join(f'<a href="/{r}"'+(' aria-current="page"' if r==route else '')+f'>{esc(i[0])}</a>' for r,i in PAGES.items())
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive"><meta name="luma-surface" content="research-review-v2">
<title>{esc(label)} | LumenCore</title><link rel="stylesheet" href="./assets/luma_command_fabric.css"><style>{CSS}</style></head>
<body><a class="skip" href="#main">Skip to evidence</a><main class="review-wrap" id="main">
<header class="hero"><div class="eyebrow">LumenCore / {esc(label)}</div><h1>{esc(title)}</h1><p>{esc(description)}</p><span class="badge">READ-ONLY REVIEW · DATED EVIDENCE</span><p class="note">Reviewed {REVIEW_DATE}. Current exchange balances, live data health and execution authority are not inferred from historical artifacts.</p></header>
{metrics}<nav class="compact-nav" aria-label="Research workspaces">{nav}</nav>{content}
<section class="panel archived"><h2>Full interface history</h2><p>{source('dashboard/'+route,'Open the archived full interface',ARCHIVE_COMMIT)}. This connected review view preserves the research story without exposing private operator APIs. The historical interface has not been reconnected to the current private runtime.</p></section>
<footer class="source-footer">Evidence source commit: {SOURCE_COMMIT}. Static review date: {REVIEW_DATE}.<br><a href="/proof_to_pilot.html">Scope a buyer-owned validation review</a> · <a href="/">LumenCore home</a><br>Research results do not establish field validation, production readiness, endorsement or guaranteed trading performance.</footer></main><script src="./assets/luma_command_fabric.js"></script></body></html>
'''


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Fail if the committed pages differ from their source-backed render.')
    args=parser.parse_args()
    different=[]
    for route in PAGES:
        path=ROOT/'dashboard'/route
        rendered=render_page(ROOT,route)
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != rendered:
                different.append(route)
        else:
            path.write_text(rendered,encoding='utf-8')
    if different:
        print('Review pages differ: '+', '.join(different));return 1
    print(f'Connected research pages: {len(PAGES)}; '+('verified' if args.check else 'written'))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
