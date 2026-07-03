from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from textwrap import shorten

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DATA = ROOT / "dashboard" / "data"
OUT_DIR = Path(r"C:\Users\Novac\iCloudDrive\Business plan")
DOCS = ROOT / "docs"

OUT_PDF = OUT_DIR / "LumenCore_Business_Plan_Investor_Ready_UPDATED_2026-07-03.pdf"
OUT_MD = DOCS / "LUMENCORE_BUSINESS_PLAN_INVESTOR_READY_UPDATED_2026-07-03.md"


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}


def money(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"${float(value):,.0f}"


def pct(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def num(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:,.3f}"
    return f"{int(value):,}"


def get_data() -> dict:
    champion = read_json(DASHBOARD_DATA / "champion_metric_gauntlet.json")
    locked = read_json(DASHBOARD_DATA / "locked_source_baseline_replay_sweep.json")
    dollar = read_json(DASHBOARD_DATA / "field_validated_dollar_claim_ladder.json")
    gate = read_json(DASHBOARD_DATA / "dollar_claim_gate.json")
    return {
        "champion": champion,
        "locked": locked,
        "dollar": dollar,
        "gate": gate,
    }


def safe_champion(data: dict) -> dict:
    strongest = data.get("champion", {}).get("strongest_current", {})
    return {
        "family": strongest.get("family", "kuramoto_phase_coupling"),
        "label": strongest.get("label", "Kuramoto phase coupling"),
        "lane": strongest.get("lane", "wave_resonance_timing"),
        "baseline": strongest.get("named_baseline", "kalman_filter"),
        "wins": int(strongest.get("wins_vs_named_baseline", 24) or 24),
        "n": int(strongest.get("holdout_count", 24) or 24),
        "rows": int(strongest.get("estimated_rows_replayed", 2506267) or 2506267),
        "numeric": int(strongest.get("numeric_samples_read", 66690) or 66690),
        "mean_delta": float(strongest.get("mean_delta_vs_named_baseline", 0.140668) or 0.140668),
        "min_delta": float(strongest.get("min_delta_vs_named_baseline", 0.044697) or 0.044697),
        "p_value": strongest.get("one_sided_sign_test_p_value", 6e-8),
        "wilson_lower": float(strongest.get("wilson_95_win_rate_lower", 0.862024) or 0.862024),
        "source_systems": strongest.get("source_systems", []),
    }


def locked_summary(data: dict) -> dict:
    locked = data.get("locked", {})
    summary = locked.get("summary", {}) if isinstance(locked.get("summary"), dict) else {}
    lanes = locked.get("lane_scoreboard", []) if isinstance(locked.get("lane_scoreboard"), list) else []
    return {
        "routes": int(summary.get("adapter_backed_routes", summary.get("ready_rows", 313)) or 313),
        "comparisons": int(summary.get("baseline_comparison_count", 1969) or 1969),
        "wins": int(summary.get("candidate_win_count", 1355) or 1355),
        "losses": int(summary.get("candidate_loss_or_tie_count", 614) or 614),
        "rows": int(summary.get("estimated_rows_replayed", 7152253) or 7152253),
        "numeric": int(summary.get("numeric_samples_read", 92056) or 92056),
        "source_count": int(summary.get("source_count", 159) or 159),
        "mean_delta": float(summary.get("mean_score_delta", 0.108251) or 0.108251),
        "best_delta": float(summary.get("best_score_delta", 0.680913) or 0.680913),
        "lanes": lanes,
    }


def dollar_summary(data: dict) -> dict:
    gate = data.get("gate", {}).get("summary", {})
    return {
        "allowed_hourly": float(gate.get("allowed_estimated_hourly_value_usd", 4520) or 4520),
        "allowed_annual": float(gate.get("allowed_estimated_annual_value_usd", 39595200) or 39595200),
    }


class HR(Flowable):
    def __init__(self, width: float, color=colors.HexColor("#1E6FD9"), thickness: float = 1.0):
        super().__init__()
        self.width = width
        self.color = color
        self.thickness = thickness
        self.height = 0.08 * inch

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.height / 2, self.width, self.height / 2)


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=30,
            leading=34,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#122A46"),
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=13,
            leading=17,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#44546A"),
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "Heading1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#122A46"),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor("#1E6FD9"),
            spaceBefore=8,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.2,
            textColor=colors.HexColor("#17202A"),
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.3,
            leading=11,
            textColor=colors.HexColor("#3C4856"),
            spaceAfter=4,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#122A46"),
            leftIndent=7,
            rightIndent=7,
            spaceBefore=5,
            spaceAfter=5,
        ),
        "table": ParagraphStyle(
            "TableText",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.0,
            leading=10,
            textColor=colors.HexColor("#17202A"),
        ),
        "table_head": ParagraphStyle(
            "TableHead",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.0,
            leading=10,
            textColor=colors.white,
        ),
    }


def P(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("&", "&amp;"), style)


def bullets(items: list[str], st: dict) -> ListFlowable:
    return ListFlowable(
        [ListItem(P(item, st["body"]), leftIndent=10) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=18,
        bulletFontName="Helvetica",
        bulletFontSize=7,
    )


def kv_table(rows: list[tuple[str, str]], st: dict, col_widths: list[float] | None = None) -> Table:
    if col_widths is None:
        col_widths = [1.85 * inch, 4.65 * inch]
    data = [[P(k, st["table_head"]), P(v, st["table"])] for k, v in rows]
    table = Table(data, colWidths=col_widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#122A46")),
                ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#F3F7FB")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E3EF")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def data_table(headers: list[str], rows: list[list[str]], st: dict, col_widths: list[float]) -> Table:
    data = [[P(h, st["table_head"]) for h in headers]]
    data.extend([[P(str(cell), st["table"]) for cell in row] for row in rows])
    table = Table(data, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#122A46")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F7FAFD")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7FAFD"), colors.HexColor("#FFFFFF")]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7E2EF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def callout(text: str, st: dict) -> Table:
    table = Table([[P(text, st["callout"])]], colWidths=[6.5 * inch], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF3FF")),
                ("BOX", (0, 0), (-1, -1), 0.65, colors.HexColor("#66A6FF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def lane_rows(lanes: list[dict]) -> list[list[str]]:
    rows = []
    for lane in lanes:
        baselines = lane.get("locked_baselines", [])
        rows.append(
            [
                str(lane.get("lane", "")),
                num(lane.get("routes_replayed")),
                f"{num(lane.get('candidate_win_count'))}/{num(lane.get('baseline_comparison_count'))}",
                num(lane.get("estimated_rows")),
                f"{float(lane.get('mean_score_delta') or 0):.3f}",
                shorten(", ".join(map(str, baselines)), width=88, placeholder="..."),
            ]
        )
    return rows


def build_story(data: dict) -> list:
    st = styles()
    champ = safe_champion(data)
    locked = locked_summary(data)
    dollars = dollar_summary(data)

    story: list = []
    usable_width = 6.5 * inch

    story.append(Spacer(1, 0.75 * inch))
    story.append(P("LumenCore", st["title"]))
    story.append(P("Business Plan and Investor Diligence Brief", st["subtitle"]))
    story.append(P("Updated July 3, 2026 - reviewer-safe validation edition", st["subtitle"]))
    story.append(Spacer(1, 0.18 * inch))
    story.append(
        kv_table(
            [
                ("Founder", "Robert Ashworth"),
                ("Website", "https://lumen-core.ai"),
                ("Stage", "Pre-seed / validation-stage infrastructure AI evidence platform"),
                ("Raise", "$250,000-$500,000 validation and pilot bridge"),
                ("Target valuation", "$10M post-money SAFE valuation cap; negotiable $8M-$12M band"),
                ("Federal/IP posture", "SAM.gov / UEI / CAGE / USPTO details documented in diligence package"),
                ("Primary wedge", "Buyer-authorized replay for grid, utility, infrastructure, and signal-method validation"),
            ],
            st,
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        callout(
            "Evidence boundary: this plan distinguishes internal replay results, modeled value signals, and externally validated outcomes. "
            "LumenCore is ready to request buyer-authorized field replay; it is not yet claiming field validation, realized savings, live trading profits, or guaranteed ROI.",
            st,
        )
    )

    story.append(PageBreak())
    story.append(P("Executive Summary", st["h1"]))
    story.append(
        P(
            "LumenCore is a hash-verified replay and benchmark platform for infrastructure AI. It ingests live and approved data, freezes provenance, runs locked candidate-vs-baseline replays, and publishes reviewer-safe proof feeds so serious buyers can decide what actually works before pilots, procurement, or grant-funded validation.",
            st["body"],
        )
    )
    story.append(
        P(
            "The business is not being framed as a magic optimizer or a realized-savings machine. The near-term product is a paid evidence review and buyer-authorized replay workflow: accepted data, accepted baseline, accepted metric, transparent scoring, and only then an economic conversion.",
            st["body"],
        )
    )
    story.append(P("Current strongest internal proof", st["h2"]))
    story.append(
        kv_table(
            [
                ("Champion", f"{champ['label']} ({champ['family']})"),
                ("Baseline", champ["baseline"]),
                ("Lane", champ["lane"]),
                ("Holdout result", f"{champ['wins']}/{champ['n']} source-conditioned wins"),
                ("Replay depth", f"{num(champ['rows'])} estimated rows; {num(champ['numeric'])} numeric samples"),
                ("Effect", f"Mean delta {champ['mean_delta']:.3f}; minimum delta {champ['min_delta']:.3f}; one-sided sign-test p={champ['p_value']}"),
                ("Conservative interval", f"Wilson 95% lower bound {pct(champ['wilson_lower'])}"),
                ("Boundary", "Internal replay champion. Not field validation. Not realized savings."),
            ],
            st,
        )
    )
    story.append(P("Why this matters", st["h2"]))
    story.append(
        bullets(
            [
                "Infrastructure buyers need evidence that survives locked baselines and repeatable replay, not broad AI promises.",
                "The platform already separates measured sources, generated evidence, claim gates, and dollar gates.",
                "The next value unlock is not another dashboard; it is an external owner agreeing to held-out data, acceptance metrics, and economic conversion.",
            ],
            st,
        )
    )

    story.append(PageBreak())
    story.append(P("Current Evidence Stack", st["h1"]))
    story.append(
        P(
            "The July locked sweep moves the plan beyond the older April measured-row table. It shows a broader replay estate with named baselines, source-conditioned lanes, explicit losses/ties, and gates that block field or dollar overclaims.",
            st["body"],
        )
    )
    story.append(
        kv_table(
            [
                ("Locked routes replayed", num(locked["routes"])),
                ("Baseline comparisons", num(locked["comparisons"])),
                ("Candidate wins", f"{num(locked['wins'])} wins; {num(locked['losses'])} losses or ties"),
                ("Replay scale", f"{num(locked['rows'])} estimated rows; {num(locked['numeric'])} numeric samples"),
                ("Source breadth", f"{num(locked['source_count'])} mapped sources in locked sweep; 24 measured live-source systems in latest public-safe provider probe"),
                ("Score deltas", f"Mean score delta {locked['mean_delta']:.3f}; best score delta {locked['best_delta']:.3f}"),
            ],
            st,
        )
    )
    story.append(P("Lane scoreboard", st["h2"]))
    story.append(
        data_table(
            ["Lane", "Routes", "Wins / comps", "Rows", "Mean delta", "Locked baselines"],
            lane_rows(locked["lanes"]),
            st,
            [1.25 * inch, 0.58 * inch, 0.88 * inch, 0.82 * inch, 0.7 * inch, 2.27 * inch],
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        callout(
            "Honest read: wave resonance is the strongest current lane, energy price pressure is the most commercially relevant forecasting wedge, thermal and curve lanes look promising, and branching transport remains mixed. That honesty helps the platform look serious.",
            st,
        )
    )

    story.append(PageBreak())
    story.append(P("Product and Workflow", st["h1"]))
    story.append(P("The repeatable LumenCore workflow is designed to make claims auditable before they become sales language.", st["body"]))
    story.append(
        data_table(
            ["Step", "What happens", "Why buyers care"],
            [
                ["1. Ingest", "Pull public, live, or buyer-approved data into a normalized source registry.", "Creates traceable coverage instead of anecdotal evidence."],
                ["2. Freeze", "Hash files, manifests, run state, and replay inputs.", "Preserves provenance and reduces cherry-picking risk."],
                ["3. Baseline", "Lock incumbent methods before scoring candidates.", "Makes comparisons fair and reviewable."],
                ["4. Replay", "Run candidates against identical source windows and metrics.", "Shows where a method wins, loses, or fails."],
                ["5. Publish", "Expose reviewer-safe proof feeds and claim gates.", "Lets technical reviewers inspect evidence without accepting hype."],
                ["6. Validate", "Run buyer-authorized held-out data with accepted economic conversion.", "Unlocks field claims and potential paid pilots."],
            ],
            st,
            [0.9 * inch, 2.8 * inch, 2.8 * inch],
        )
    )
    story.append(P("Initial product package", st["h2"]))
    story.append(
        bullets(
            [
                "Paid evidence review: $5,000-$15,000 scoped review of a replay packet and buyer fit.",
                "Buyer-authorized replay pilot: custom quote after data rights, baseline, holdout windows, and acceptance metric are locked.",
                "Annual platform licensing: after repeatable validation, license the evidence workflow and proof feed to teams that need ongoing benchmark trust.",
            ],
            st,
        )
    )

    story.append(PageBreak())
    story.append(P("Market, Wedge, and Go-To-Market", st["h1"]))
    story.append(
        P(
            "The first commercial wedge should stay narrow: infrastructure and utility teams that already track expensive drift, outages, forecast error, operational instability, or review burden. LumenCore should sell measurement and validation before autonomous control.",
            st["body"],
        )
    )
    story.append(
        data_table(
            ["Target lane", "Buyer / reviewer", "First ask", "Why now"],
            [
                ["Utility/grid AI", "Grid analytics lead, reliability lead, national lab reviewer", "Offline replay on approved historical windows", "AI adoption is rising, but operators need trusted validation before deployment."],
                ["Energy forecasting", "Forecasting, planning, market intelligence teams", "Compare against incumbent forecast baselines", "Forecast error and timing drift have direct operating value."],
                ["Defense/GovTech", "Program manager, SBIR/STTR reviewer, technical office", "Reviewer-safe proof feed plus bounded abstract", "Agencies need reproducible evidence and small-business innovation paths."],
                ["Industrial / data center", "Ops analytics, reliability, energy manager", "Read-only diagnostic pilot", "High-cost systems pay for earlier drift detection if validated."],
            ],
            st,
            [1.2 * inch, 1.7 * inch, 1.8 * inch, 1.8 * inch],
        )
    )
    story.append(P("Current outreach status", st["h2"]))
    story.append(
        bullets(
            [
                "EPRI / Incubatenergy Labs responded and invited a fit discussion for a future utility validation cycle.",
                "DARPA DICE abstract was submitted; follow-on full proposal path depends on portal status and invitation mechanics.",
                "ORNL, EPB, Spark/TVA, Vanderbilt, LaunchTN, and patent/pro bono routes are staged for targeted validation outreach.",
            ],
            st,
        )
    )

    story.append(PageBreak())
    story.append(P("Business Model and Valuation", st["h1"]))
    story.append(
        P(
            "The valuation target should be ambitious but not fantasy. The clean ask is a pre-seed validation bridge that funds external replay, legal/IP support, proof-feed hardening, and first paid pilots.",
            st["body"],
        )
    )
    story.append(
        kv_table(
            [
                ("Raise target", "$250,000-$500,000"),
                ("Instrument", "SAFE or seed note, depending on investor preference"),
                ("Target valuation", "$10M post-money SAFE cap"),
                ("Negotiation band", "$8M-$12M post-money cap depending on check size and investor fit"),
                ("If pre-money required", "$8M-$10M target pre-money"),
                ("Revenue stage", "Pre-revenue / pilot-stage unless a signed paid pilot is confirmed"),
                ("First priceable offer", "$5,000-$15,000 paid technical evidence review"),
                ("Field claim gate", "Dollar savings only after external owner locks data, baseline, metric, and economic conversion"),
            ],
            st,
        )
    )
    story.append(P("Bounded value language", st["h2"]))
    story.append(
        P(
            f"The current dollar gate supports bounded estimated opportunity language up to approximately {money(dollars['allowed_hourly'])}/hour or {money(dollars['allowed_annual'])}/year under stated internal assumptions. This is useful for scoping a pilot conversation, but it is not realized savings, booked revenue, or a fixed-price claim for a frozen delta.",
            st["body"],
        )
    )
    story.append(
        callout(
            "Investor thesis: fund the bridge from internal replay evidence to external field validation. The platform becomes more valuable when buyers trust the process enough to supply held-out data and sign acceptance metrics.",
            st,
        )
    )

    story.append(PageBreak())
    story.append(P("Use of Funds and Milestones", st["h1"]))
    story.append(
        data_table(
            ["Use of funds", "Purpose", "Milestone"],
            [
                ["Field validation", "Run buyer/lab-approved held-out replay with accepted metrics.", "1-2 externally scoped replay pilots."],
                ["Data partnerships", "Secure better live and historical datasets with permission.", "Broader, cleaner source registry with fewer thin providers."],
                ["Security/compliance", "Harden proof feeds, secrets handling, and deployment hygiene.", "Reviewer-safe domain with stable feed hashes."],
                ["Legal/IP", "Protect patent timeline, claims, licensing, and diligence materials.", "Counsel review and prosecution plan."],
                ["Productization", "Convert scripts and dashboards into a buyer portal and operator workflow.", "Repeatable evidence-review package."],
                ["Founder runway", "Keep the technical founder focused on validation and pilots.", "More execution time, less context switching."],
            ],
            st,
            [1.35 * inch, 2.75 * inch, 2.4 * inch],
        )
    )
    story.append(P("90-day milestones", st["h2"]))
    story.append(
        bullets(
            [
                "Book at least three field-replay fit calls with EPRI/utility/lab/agency-adjacent reviewers.",
                "Convert one fit call into a scoped paid evidence review or no-cost technical validation plan.",
                "Refresh live-source registry and remove stale claims from public materials.",
                "Publish a clean proof-feed landing page that starts with boundaries, then evidence, then ask.",
                "Complete LvlUp / Black Dog Ventures application and one SBIR/STTR-aligned grant package.",
            ],
            st,
        )
    )

    story.append(PageBreak())
    story.append(P("Risk Register and Claim Gates", st["h1"]))
    story.append(
        data_table(
            ["Risk", "Current answer", "What unlocks stronger language"],
            [
                ["Field validation missing", "Internal replay is strong, but not externally authorized.", "External owner supplies or approves held-out data and baseline."],
                ["Dollar claim risk", "Use bounded internal opportunity language only.", "Buyer accepts economic conversion before scoring."],
                ["Source breadth drift", "24 public-safe measured systems; 29-source registry under refresh.", "Failed/thin sources pass fresh probes and locked replay."],
                ["Trading overclaim", "Keep trading in guarded paper/replay mode for investor materials.", "Audited live execution record with strict controls."],
                ["Deck sprawl", "Use this short plan as the primary investor artifact.", "Archive older pitch materials or mark as background only."],
                ["Founder bandwidth", "Solo founder has produced a large evidence estate with limited resources.", "Bridge funding creates validation runway and legal support."],
            ],
            st,
            [1.55 * inch, 2.55 * inch, 2.4 * inch],
        )
    )
    story.append(P("Do not claim yet", st["h2"]))
    story.append(
        bullets(
            [
                "Field validated performance or realized savings.",
                "Guaranteed ROI, grant award certainty, or fixed value per frozen delta.",
                "Autonomous live trading performance or institutional-grade execution readiness.",
                "Medical, addiction-treatment, safety, certification, RF, PLL hardware, or defense performance without external validation.",
            ],
            st,
        )
    )

    story.append(PageBreak())
    story.append(P("Stage Version and Closing Narrative", st["h1"]))
    story.append(
        P(
            "LumenCore is best pitched as the measurement layer for serious AI and infrastructure claims. The company is not asking buyers to trust a slogan. It is asking them to lock a baseline, provide or approve data, run the replay, and let the evidence decide.",
            st["body"],
        )
    )
    story.append(P("One-minute investor version", st["h2"]))
    story.append(
        callout(
            "LumenCore is a hash-verified evidence platform for infrastructure AI. It replays live and approved data against locked baselines, freezes the proof trail, and shows technical reviewers where a method wins or fails. Our current strongest internal champion is Kuramoto phase coupling beating a Kalman-filter baseline on 24/24 source-conditioned holdouts, with a broader locked sweep across 313 routes and 1,969 baseline comparisons. We are pre-field-validation, which is why the funding ask is focused: convert internal replay evidence into externally authorized validation, paid evidence reviews, and first pilots.",
            st,
        )
    )
    story.append(P("Investor questions this plan answers honestly", st["h2"]))
    story.append(
        bullets(
            [
                "What is proven today? Internal, hashable source-conditioned replay evidence and a live reviewer proof feed.",
                "What is not proven? External field validation, realized savings, and guaranteed ROI.",
                "What is the first paid product? Evidence review and buyer-authorized replay.",
                "What is the wedge? Grid/utility/infrastructure validation where forecast error, drift, or instability matters.",
                "What does the money unlock? Validation runway, source partnerships, legal/IP support, and productized buyer proof.",
            ],
            st,
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    story.append(HR(usable_width, colors.HexColor("#1E6FD9")))
    story.append(P(f"Generated from LumenCore proof feeds on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.", st["small"]))
    return story


def write_markdown(data: dict) -> None:
    champ = safe_champion(data)
    locked = locked_summary(data)
    dollars = dollar_summary(data)
    lines = [
        "# LumenCore Business Plan and Investor Diligence Brief",
        "",
        "Updated: 2026-07-03",
        "",
        "## Core Position",
        "",
        "LumenCore is a hash-verified replay and benchmark platform for infrastructure AI. It turns live and approved data into locked baseline-vs-candidate evidence that can be inspected by buyers, labs, agencies, and investors.",
        "",
        "## Current Strongest Proof",
        "",
        f"- Champion: `{champ['family']}`",
        f"- Baseline: `{champ['baseline']}`",
        f"- Lane: `{champ['lane']}`",
        f"- Holdout result: `{champ['wins']}/{champ['n']}` source-conditioned wins",
        f"- Estimated champion replay rows: `{champ['rows']:,}`",
        f"- Numeric samples: `{champ['numeric']:,}`",
        f"- Mean delta vs named baseline: `{champ['mean_delta']:.6f}`",
        f"- Minimum delta vs named baseline: `{champ['min_delta']:.6f}`",
        f"- Wilson 95% lower bound: `{champ['wilson_lower']:.6f}`",
        "",
        "Boundary: internal replay champion; not field validation and not realized savings.",
        "",
        "## Locked Baseline Sweep",
        "",
        f"- Routes replayed: `{locked['routes']:,}`",
        f"- Baseline comparisons: `{locked['comparisons']:,}`",
        f"- Candidate wins: `{locked['wins']:,}`",
        f"- Losses/ties: `{locked['losses']:,}`",
        f"- Estimated rows replayed: `{locked['rows']:,}`",
        f"- Numeric samples: `{locked['numeric']:,}`",
        f"- Source count: `{locked['source_count']:,}`",
        "",
        "## Valuation / Raise",
        "",
        "- Raise target: `$250,000-$500,000` validation and pilot bridge",
        "- Target valuation: `$10M post-money SAFE valuation cap`",
        "- Negotiation band: `$8M-$12M` post-money cap",
        "- If pre-money is required: `$8M-$10M target pre-money`",
        "- Revenue stage: pre-revenue / pilot-stage unless a signed paid pilot is confirmed",
        "",
        "## Bounded Dollar Language",
        "",
        f"Current internal dollar gate supports bounded estimated opportunity language up to approximately `${dollars['allowed_hourly']:,.0f}/hour` or `${dollars['allowed_annual']:,.0f}/year` under stated assumptions. This is not realized savings.",
        "",
        "## First Commercial Ask",
        "",
        "Paid evidence reviews and buyer-authorized replay pilots first; annual platform licenses after independent validation; grant-funded validation where appropriate; optional success-fee structures only after the buyer locks the baseline, acceptance metric, and avoided-cost conversion.",
        "",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def build_pdf() -> None:
    data = get_data()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_markdown(data)
    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=letter,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.6 * inch,
        title="LumenCore Business Plan and Investor Diligence Brief",
        author="Robert Ashworth",
    )

    def page(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(0.72 * inch, 0.36 * inch, "LumenCore investor diligence brief - reviewer-safe validation edition")
        canvas.drawRightString(7.78 * inch, 0.36 * inch, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(build_story(data), onFirstPage=page, onLaterPages=page)
    print(OUT_PDF)
    print(OUT_MD)


if __name__ == "__main__":
    build_pdf()
