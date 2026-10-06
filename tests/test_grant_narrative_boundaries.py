"""Fictional local fixtures exercising applicant/evidence claim boundaries."""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "code") not in sys.path:
    sys.path.insert(0, str(ROOT / "code"))

import grant_application_factory as factory  # noqa: E402
from grant_submission_kit import build_preflight  # noqa: E402


@pytest.fixture
def inputs(monkeypatch):
    """No account access, real applicant, real partner, publication, or award."""
    monkeypatch.setattr(factory, "build_program_spotlights", lambda *a, **k: [])
    program = {
        "id": "FICTIONAL-NARRATIVE-BOUNDARY",
        "agency": "Fictional Example Agency",
        "program": "Fictional Workflow Demonstrator",
        "topic_area": "Local document-review mechanics",
        "ceiling_usd": 10000,
        "duration_months": 3,
    }
    profile = {
        "company": {
            "legal_name": "FICTIONAL ONLY — Narrative Tools Inc",
            "dba": "Fixture Tools",
            "email": "fictional@example.invalid",
            "phone": "TO_BE_FILLED",
        },
        "pi": {
            "name": "Fictional Reviewer",
            "title": "Example Principal Investigator",
            "bio_short": "Fictional biography for local testing only.",
            "employed_pct": 100,
        },
        "project": {},
        "submission_readiness": {},
    }
    evidence = {
        "run_utc": "20261006T120000Z",
        "evidence_type": "synthetic_fixture",
        "layers": {
            "benchmark": {"n_datasets": 0, "n_models": 0, "n_families": 0},
            "meta_router": {
                "wins": 0, "n": 0, "win_rate": 0,
                "median_rel_rmse_vs_oracle": 0,
            },
            "hybrid_stacker": {"j_beats_v2_oracle": 0, "k_beats_v2_oracle": 0},
            "ci_calibration": {"mean_cov80": 0, "mean_cov95": 0},
            "stacking_blender": {
                "wins": 0, "n": 0, "median_blend_rel_vs_v2_oracle": 0,
                "avg_blend_weights": {"fictional_model": 0},
            },
            "anomaly_scanner": {"n_with_2sigma": 0, "n_datasets": 0},
            "regime_shift": {"n_with_break": 0, "n_datasets": 0, "n_recent": 0},
            "measured_breadth": {
                "artifacts_measured": 0, "parse_ok_count": 0, "rows_total": 0,
            },
            "active_registry": {},
        },
    }
    budget = {
        "ceiling_usd": 10000,
        "duration_months": 3,
        "total": 10000,
        "categories": {"fictional_planning_reserve": 10000},
        "notes": ["Fictional planning numbers, not a verified cost or rate."],
    }
    return program, profile, evidence, budget


RENDERERS = (
    "render_project_summary", "render_technical_volume", "render_commercialization",
    "render_cover_letter", "render_application_md", "render_nsf_project_pitch",
)


def render(name, inputs):
    program, profile, evidence, budget = inputs
    renderer = getattr(factory, name)
    if name == "render_application_md":
        return renderer(program, profile, evidence, budget)
    return renderer(program, profile, evidence)


def all_text(inputs):
    return "\n\n".join(render(name, inputs) for name in RENDERERS)


@pytest.mark.parametrize("name", RENDERERS)
def test_unrelated_applicant_does_not_inherit_legacy_claims(name, inputs):
    text = render(name, inputs)
    forbidden = (
        "LumenCore", "$999", "$9,999", "$50–250k", "$50-250k",
        "ships a production", "production, evidence-chained",
        "validated end-to-end", "DOE partner laboratory", "deployed API surfaces",
        "<200ms", "≥55%", "≥30%", "https://lumen-core.ai",
        "U.S.-owned small business", "Every quantitative claim",
        "independently rebuild any number", "strong cross-layer evidence signal",
    )
    for claim in forbidden:
        assert claim not in text, f"{name} leaked unsupported claim: {claim}"


def test_supplied_project_scope_is_retained_and_missing_scope_is_unresolved(inputs):
    text = all_text(inputs)
    assert "TO_BE_FILLED" in text
    supplied = {
        "summary": "FICTIONAL PURPOSE: compare local document revision workflows.",
        "methods": "FICTIONAL METHOD: manually review two supplied document sets.",
        "validation_plan": "FICTIONAL VALIDATION PLAN: record local reviewer disagreements.",
        "facilities": "FICTIONAL FACILITY: one local laptop, no hosted deployment.",
        "commercial_plan": "FICTIONAL COMMERCIAL ASSUMPTION: buyer discovery; price unapproved.",
    }
    inputs[1]["project"] = supplied
    supplied_text = all_text(inputs)
    for value in supplied.values():
        assert value in supplied_text
    assert "unapproved" in supplied_text


def test_missing_project_scope_stays_a_preflight_blocker(inputs, tmp_path):
    # Other readiness gates may also fail: this assertion specifically checks
    # that neutral prose cannot erase the missing substantive project facts.
    program, profile, evidence, budget = inputs
    for filename, renderer in {
        "application.md": "render_application_md",
        "technical_volume.md": "render_technical_volume",
        "commercialization_plan.md": "render_commercialization",
        "cover_letter.md": "render_cover_letter",
    }.items():
        (tmp_path / filename).write_text(render(renderer, inputs), encoding="utf-8")
    payloads = {
        "application.json": {
            "program_id": program["id"], "agency": program["agency"],
            "program": program["program"], "applicant": profile["company"],
            "budget": budget, "evidence_summary": evidence["layers"],
            "eligibility": {"eligible": True},
        },
        "budget.json": budget, "eligibility_report.json": {"eligible": True},
        "evidence_manifest.json": {}, "approval_state.json": {"state": "draft"},
    }
    for filename, payload in payloads.items():
        (tmp_path / filename).write_text(json.dumps(payload), encoding="utf-8")
    # Preflight is a read/check path; no external submission is performed.
    preflight = build_preflight(program["id"], tmp_path, None)
    assert preflight["ready"] is False
    assert any("TO_BE_FILLED" in blocker for blocker in preflight["blockers"])


def replace_metric_leaves(layers, value):
    """Keep structure, make every supplied metric unknown or invalid."""
    for data in layers.values():
        if not isinstance(data, dict):
            continue
        for key, current in list(data.items()):
            if isinstance(current, dict):
                for subkey in current:
                    current[subkey] = value
            elif isinstance(current, (int, float)):
                data[key] = value


@pytest.mark.parametrize("unknown", [None, float("nan"), float("inf"), True])
def test_unknown_metrics_do_not_raise_or_become_reported_results(inputs, unknown):
    altered = copy.deepcopy(inputs)
    replace_metric_leaves(altered[2]["layers"], unknown)
    text = all_text(altered)
    assert "unavailable" in text.lower()
    assert not re.search(r"\b(?:None|nan|inf|True)\b", text)


def test_finite_zero_is_not_treated_as_missing_evidence(inputs):
    text = render("render_project_summary", inputs)
    # Zero belongs to a result line, not merely to the timestamp or budget.
    assert re.search(r"(?im)^.*(?:benchmark|series|dataset|coverage|mean_cov80).*\b0\b", text)


@pytest.mark.parametrize("name", RENDERERS)
def test_missing_evidence_layers_are_unavailable_without_promoting_validity(inputs, name):
    inputs[2]["layers"] = {}
    text = render(name, inputs)
    if name != "render_commercialization":
        assert "unavailable" in text.lower()
        assert "not independently verified" in text.lower()


def test_synthetic_and_unknown_provenance_remain_explicit(inputs):
    text = render("render_project_summary", inputs)
    assert "synthetic_fixture" in text
    inputs[2].pop("evidence_type")
    text = render("render_project_summary", inputs)
    assert "not established" in text.lower()
    inputs[2]["evidence_type"] = "claimed_production"
    inputs[2]["demo_notice"] = True
    text = render("render_project_summary", inputs)
    assert "synthetic" in text.lower()
    assert "fictional" in text.lower()
    assert "claimed_production" not in text


@pytest.mark.parametrize("kind", ["synthetic_fixture", None])
def test_generated_json_retains_the_evidence_stage(inputs, tmp_path, monkeypatch, kind):
    program, profile, evidence, _ = inputs
    evidence["evidence_type"] = kind
    monkeypatch.setattr(factory, "GRANTS", tmp_path / "grants")
    monkeypatch.setattr(factory, "_file_provenance", lambda path: {"available": False})
    run = factory.write_bundle(
        program, profile, evidence, {"eligible": True, "score": 0}, "20261006T120000Z"
    )
    for filename in ("application.json", "evidence_manifest.json"):
        payload = json.loads((run / filename).read_text(encoding="utf-8"))
        reported_kind = payload.get("evidence_type")
        if kind == "synthetic_fixture":
            assert reported_kind == kind
        else:
            assert reported_kind == "not established"


def test_demo_notice_cannot_be_overridden_by_a_production_label_in_json(inputs, tmp_path, monkeypatch):
    program, profile, evidence, _ = inputs
    evidence.update({"evidence_type": "claimed_production", "demo_notice": True})
    monkeypatch.setattr(factory, "GRANTS", tmp_path / "grants")
    monkeypatch.setattr(factory, "_file_provenance", lambda path: {"available": False})
    run = factory.write_bundle(
        program, profile, evidence, {"eligible": True, "score": 0}, "20261006T120000Z"
    )
    for filename in ("application.json", "evidence_manifest.json"):
        payload = json.loads((run / filename).read_text(encoding="utf-8"))
        assert "synthetic" in payload["evidence_type"].lower()
        assert payload["demo_notice"] is True


@pytest.mark.parametrize("nsf_pitch", [False, True])
@pytest.mark.parametrize("missing_methods", [None, "", "   "])
def test_missing_methods_block_both_full_proposal_and_pitch(inputs, tmp_path, monkeypatch,
                                                          nsf_pitch, missing_methods):
    program, profile, evidence, _ = inputs
    if nsf_pitch:
        program.update({"id": "nsf_sbir_FICTIONAL_BOUNDARY", "agency": "Fictional NSF",
                        "program": "Fictional SBIR pitch"})
    profile["company"]["phone"] = "FICTIONAL_PHONE_ONLY"
    profile["project"] = {
        "summary": "FICTIONAL supplied purpose.",
        "methods": missing_methods,
        "validation_plan": "FICTIONAL supplied validation plan.",
        "facilities": "FICTIONAL local facility.",
        "commercial_plan": "FICTIONAL supplied commercial assumptions.",
    }
    monkeypatch.setattr(factory, "GRANTS", tmp_path / "grants")
    monkeypatch.setattr(factory, "_file_provenance", lambda path: {"available": False})
    run = factory.write_bundle(
        program, profile, evidence, {"eligible": True, "score": 0}, "20261006T120000Z"
    )
    preflight = build_preflight(program["id"], run, None)
    assert preflight["ready"] is False
    method_blocked = False
    for missing in preflight["missing_fields"]:
        if ":line:" in missing:
            filename, line_number = missing.rsplit(":line:", 1)
            line = (run / filename).read_text(encoding="utf-8").splitlines()[int(line_number) - 1]
            if "TO_BE_FILLED: project.methods" in line:
                method_blocked = True
    assert method_blocked, "Missing methods did not become a substantive preflight blocker"


def test_unknown_spotlight_does_not_claim_a_strong_signal():
    text = "\n".join(factory.format_spotlight_lines([{
        "dataset": "FICTIONAL_UNKNOWN_SERIES", "domain": "fictional",
        "anomaly": {"max_abs_z": None, "n_anomalies_3sigma": None},
        "regime": {"n_breaks_total": None, "recent_break": False},
        "model_performance": {"router_rel_vs_oracle": None},
    }]))
    assert "strong cross-layer evidence signal" not in text
    assert any(word in text.lower() for word in ("unavailable", "unverified", "unknown"))


@pytest.mark.parametrize("unknown", [None, float("nan"), float("inf"), True])
def test_invalid_spotlight_metrics_do_not_become_findings(unknown):
    text = "\n".join(factory.format_spotlight_lines([{
        "dataset": "FICTIONAL_UNKNOWN_SERIES", "domain": "fictional",
        "anomaly": {"max_abs_z": unknown, "n_anomalies_3sigma": unknown},
        "regime": {"n_breaks_total": unknown, "recent_break": False},
        "model_performance": {"router_rel_vs_oracle": unknown},
    }]))
    assert "max |z|" not in text
    assert "router/oracle RMSE" not in text
    assert ">=3sigma anomalies" not in text
    assert "regime breaks" not in text
    assert not re.search(r"\b(?:None|nan|inf|True)\b", text)


@pytest.mark.parametrize("publication", [
    None,
    {"verified": False, "url": "https://example.invalid/FICTIONAL-EVIDENCE"},
    {"verified": "true", "url": "https://example.invalid/FICTIONAL-EVIDENCE"},
    {"verified": True, "url": "http://example.invalid/FICTIONAL-EVIDENCE"},
    {"verified": True, "url": "https://user:secret@example.invalid/FICTIONAL-EVIDENCE"},
    {"verified": True, "url": "javascript:FICTIONAL-EVIDENCE"},
    {"verified": True, "url": "https:///FICTIONAL-EVIDENCE"},
])
def test_unverified_or_unsafe_public_locator_is_not_emitted(inputs, publication):
    inputs[2]["publication"] = publication
    assert "FICTIONAL-EVIDENCE" not in all_text(inputs)


def test_explicit_verified_https_locator_is_retained_without_blanket_validation(inputs):
    url = "https://example.invalid/FICTIONAL-EVIDENCE"
    inputs[2]["publication"] = {"verified": True, "url": url}
    text = all_text(inputs)
    assert url in text
    assert "validated end-to-end" not in text
    assert "independently rebuild any number" not in text
