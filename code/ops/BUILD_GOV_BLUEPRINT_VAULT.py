from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "out" / "ops" / "gov_blueprint_vault"
HEARTBEAT_LATEST_PATH = OUT_DIR / "gov_blueprint_vault_heartbeat_latest.json"


ENGINE_BINDING = {
    "family": "harmonic_alpha_edge_lock",
    "primary_engine": "harmonic_edge_lock",
    "operating_modes": [
        "harmonic",
        "alpha_lock",
        "harmonic_edge_lock",
    ],
    "mission_profile": "sniper_relentless_fearless_edge_alpha_hunter",
    "governance": "guarded_live_with_evidence_chain",
}


ASSET_TEMPLATES: list[dict[str, Any]] = [
    {
        "asset_id": "curved_motherboard_flowform",
        "asset_name": "Curved FlowForm Motherboard Architecture",
        "domain": "advanced_hardware",
        "thesis": "Curved routing geometry can reduce high-frequency path interference and improve thermal spread in dense compute rails.",
        "scientific_basis": [
            "electromagnetic field distribution in curved conductors",
            "signal integrity and impedance continuity in high-speed PCB routing",
            "thermal conduction optimization with non-linear trace layouts",
        ],
        "architecture_stack": [
            "multi-layer curved PCB topology",
            "phase-aware clock routing spine",
            "distributed thermal vias with anisotropic heat channels",
            "harmonic lock telemetry taps for runtime drift detection",
        ],
        "validation_plan": [
            "hardware-in-loop EMI benchmark against planar baseline",
            "thermal camera delta map under sustained load",
            "bit-error-rate stress test across frequency sweep",
        ],
        "trl_current": 3,
        "trl_target": 6,
        "grant_tags": [
            "advanced_manufacturing",
            "microelectronics",
            "resilient_compute",
            "defense_hardware",
        ],
        "valuation_lever": "licensable board geometry IP for compute OEMs",
        "confidence_note": "engineering hypothesis with measurable validation rails",
    },
    {
        "asset_id": "honeycomb_battery_cell_mesh",
        "asset_name": "Honeycomb Battery Mesh and Safety Lattice",
        "domain": "energy_storage",
        "thesis": "Honeycomb compartmentalization can improve thermal runaway isolation and energy-density-to-safety balance.",
        "scientific_basis": [
            "electrochemical cell thermal propagation modeling",
            "mechanical crush resistance of honeycomb lattices",
            "fault containment in segmented energy packs",
        ],
        "architecture_stack": [
            "hex-cell modular pack",
            "local thermal cutoffs per segment",
            "real-time impedance health telemetry",
            "harmonic edge lock fault-prioritization layer",
        ],
        "validation_plan": [
            "thermal runaway containment testing",
            "charge-discharge cycle degradation curves",
            "impact and vibration qualification",
        ],
        "trl_current": 4,
        "trl_target": 7,
        "grant_tags": [
            "battery",
            "grid_storage",
            "ev_safety",
            "critical_infrastructure_resilience",
        ],
        "valuation_lever": "safety-first pack architecture for energy and mobility markets",
        "confidence_note": "physics-backed direction; requires controlled prototype campaigns",
    },
    {
        "asset_id": "cymatic_control_chamber",
        "asset_name": "Cymatic Resonance Control Chambers",
        "domain": "signal_control",
        "thesis": "Controlled acoustic and vibrational resonance chambers can be used as deterministic testbeds for waveform-driven material and sensor behavior.",
        "scientific_basis": [
            "acoustic resonance and standing-wave dynamics",
            "vibro-mechanical coupling in sensor arrays",
            "frequency-domain system identification",
        ],
        "architecture_stack": [
            "programmable frequency driver array",
            "closed-loop resonance sensing",
            "phase coherence scoring",
            "harmonic lock mode classifier",
        ],
        "validation_plan": [
            "repeatability score across frequency bands",
            "sensor drift tracking under resonance load",
            "cross-material response cataloging",
        ],
        "trl_current": 3,
        "trl_target": 5,
        "grant_tags": [
            "materials_research",
            "advanced_sensing",
            "defense_r_and_d",
            "human_machine_interface",
        ],
        "valuation_lever": "novel test infrastructure for defense and manufacturing labs",
        "confidence_note": "research-grade architecture; publication and lab replication required",
    },
    {
        "asset_id": "autonomous_robotics_stack",
        "asset_name": "Autonomous Robotics Mission Stack",
        "domain": "robotics",
        "thesis": "Unified perception-planning-actuation with harmonic edge ranking can improve robustness in uncertain terrain and infrastructure tasks.",
        "scientific_basis": [
            "SLAM and probabilistic state estimation",
            "model-predictive control for dynamic robotics",
            "sensor fusion under partial observability",
        ],
        "architecture_stack": [
            "multi-sensor perception bus",
            "edge-ranked task planner",
            "mission safety supervisor",
            "telemetry proof chain for after-action audit",
        ],
        "validation_plan": [
            "navigation success across randomized obstacle fields",
            "task completion latency under degraded comms",
            "mission resilience score under subsystem faults",
        ],
        "trl_current": 4,
        "trl_target": 7,
        "grant_tags": [
            "robotics",
            "autonomy",
            "defense",
            "space_operations",
            "infrastructure_inspection",
        ],
        "valuation_lever": "dual-use autonomy platform for government and industrial contracts",
        "confidence_note": "strong control-theory footing; integration complexity is primary risk",
    },
    {
        "asset_id": "harmonic_frontier_xr",
        "asset_name": "Harmonic Frontier XR: Alpha Lock and Harmonic Edge Lock",
        "domain": "xr_simulation",
        "thesis": "An immersive training and strategy game can encode real-time flow intuition by coupling visual trajectory fields with validated haptic and vestibular cues.",
        "scientific_basis": [
            "sensorimotor adaptation in virtual reality",
            "multimodal feedback and neuroplastic learning loops",
            "state-space navigation training in high-dimensional systems",
        ],
        "architecture_stack": [
            "holographic AR and VR scene renderer",
            "terraforming-Mars simulation campaign layer",
            "left-right hemispheric training protocol via bilateral tasks",
            "harmonic edge lock reward and progression engine",
        ],
        "validation_plan": [
            "pre/post performance deltas on spatial cognition tasks",
            "reaction-time and stability metrics under sensory load",
            "controlled A/B study on decision quality uplift",
        ],
        "trl_current": 2,
        "trl_target": 6,
        "grant_tags": [
            "xr",
            "augmented_reality",
            "virtual_reality",
            "training_simulation",
            "space_mission_planning",
            "serious_games",
        ],
        "valuation_lever": "defense-grade simulation IP with commercial XR expansion path",
        "confidence_note": "concept is plausible; human-subject validation must precede performance claims",
    },
    {
        "asset_id": "full_body_haptic_skin_suit",
        "asset_name": "Adaptive Full-Body Haptic Skin Suit",
        "domain": "human_machine_interface",
        "thesis": "Frequency-programmable vibrotactile arrays across the body can create controllable proprioceptive illusions for training, rehabilitation, and simulation immersion.",
        "scientific_basis": [
            "vibrotactile perception thresholds and adaptation",
            "proprioceptive feedback entrainment",
            "closed-loop human factors control",
        ],
        "architecture_stack": [
            "distributed actuator mesh",
            "latency-bounded haptic control bus",
            "frequency profile compiler",
            "biometric safety monitor",
        ],
        "validation_plan": [
            "comfort and safety envelope mapping",
            "latency and synchronization tolerance tests",
            "task-immersion and performance correlation study",
        ],
        "trl_current": 3,
        "trl_target": 6,
        "grant_tags": [
            "haptics",
            "wearables",
            "human_performance",
            "rehabilitation_tech",
            "defense_training",
        ],
        "valuation_lever": "core platform for simulation, medical, and defense licensing",
        "confidence_note": "requires regulatory and ethics pathway for broad deployment",
    },
    {
        "asset_id": "neuro_haptic_crown",
        "asset_name": "Neuro-Haptic Crown",
        "domain": "neuro_interface",
        "thesis": "Targeted cranial haptic stimulation and EEG-informed adaptation may enhance attentional state control in high-load decision environments.",
        "scientific_basis": [
            "non-invasive neurofeedback loops",
            "attention modulation via sensory entrainment",
            "bio-signal adaptive control",
        ],
        "architecture_stack": [
            "dry-electrode EEG channels",
            "cranial vibrotactile transducer ring",
            "state classifier and adaptation model",
            "harmonic lock protocol scheduler",
        ],
        "validation_plan": [
            "EEG feature stability and artifact rejection benchmark",
            "attention and cognitive-load protocol trials",
            "safety and tolerability studies",
        ],
        "trl_current": 2,
        "trl_target": 5,
        "grant_tags": [
            "neurotechnology",
            "human_machine_interface",
            "cognitive_performance",
            "defense_research",
        ],
        "valuation_lever": "high-barrier neuro-HMI IP with strategic defense relevance",
        "confidence_note": "must remain evidence-first; no therapeutic claims without clinical validation",
    },
    {
        "asset_id": "deep_space_robotics_ops",
        "asset_name": "Deep Space Robotics and Terraforming Ops Layer",
        "domain": "space_robotics",
        "thesis": "Autonomous robotics with harmonic edge prioritization can improve reliability for habitat construction, resource handling, and maintenance under communication delay.",
        "scientific_basis": [
            "delay-tolerant autonomy in space systems",
            "fault-tolerant robotics in extreme environments",
            "resource-constrained operations planning",
        ],
        "architecture_stack": [
            "multi-robot coordination mesh",
            "delay-aware mission planner",
            "in-situ resource workflow simulator",
            "proof-first mission telemetry archive",
        ],
        "validation_plan": [
            "digital twin mission rehearsals with delayed comms",
            "fault injection and recovery benchmarks",
            "resource throughput and energy-efficiency scoring",
        ],
        "trl_current": 3,
        "trl_target": 7,
        "grant_tags": [
            "space_robotics",
            "nasa",
            "deep_space_operations",
            "terraforming_simulation",
            "autonomous_systems",
        ],
        "valuation_lever": "moonshot platform with government contract and defense dual-use upside",
        "confidence_note": "requires staged simulation-to-field progression with stringent verification",
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def _dedupe_terms(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip().lower().replace(" ", "_")
        if not token or token in seen:
            continue
        out.append(token)
        seen.add(token)
    return out


def build_payload(exposure_level: str) -> dict[str, Any]:
    assets: list[dict[str, Any]] = []
    all_terms: list[str] = []

    for row in ASSET_TEMPLATES:
        asset = dict(row)
        asset["disclosure_level"] = str(exposure_level)
        assets.append(asset)

        all_terms.extend([str(x) for x in asset.get("grant_tags", [])])
        all_terms.extend([str(x) for x in asset.get("domain", "").split("_") if x])

    all_terms.extend(ENGINE_BINDING.get("operating_modes", []))
    all_terms.extend([
        "harmonic",
        "alpha_lock",
        "harmonic_edge_lock",
        "sniper_edge",
        "government_grade",
    ])

    terms = _dedupe_terms(all_terms)

    return {
        "generated_utc": now_iso(),
        "scope": "gov_blueprint_vault",
        "engine_binding": ENGINE_BINDING,
        "summary": {
            "asset_count": len(assets),
            "focus_term_count": len(terms),
            "highest_trl_target": max(int(a.get("trl_target", 0)) for a in assets) if assets else 0,
            "domains": sorted({str(a.get("domain") or "") for a in assets}),
            "disclosure_level": str(exposure_level),
        },
        "grant_focus_terms": terms,
        "assets": assets,
        "evidence_policy": {
            "claim_model": "evidence_first_no_unverified_performance_claims",
            "proof_requirement": "benchmarks_and_or_pilot_data_before_marketing_superlatives",
            "submission_posture": "government_grade_architecture_with_validation_plan",
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    assets = payload.get("assets", []) if isinstance(payload, dict) else []
    engine = payload.get("engine_binding", {}) if isinstance(payload, dict) else {}

    lines: list[str] = []
    lines.append("# Government-Grade Blueprint Vault")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Scope: {payload.get('scope', '')}")
    lines.append("")
    lines.append("## Engine Binding")
    lines.append(f"- Family: {engine.get('family', '')}")
    lines.append(f"- Primary Engine: {engine.get('primary_engine', '')}")
    lines.append(f"- Modes: {', '.join(str(x) for x in engine.get('operating_modes', []))}")
    lines.append(f"- Mission Profile: {engine.get('mission_profile', '')}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Asset Count: {summary.get('asset_count', 0)}")
    lines.append(f"- Focus Term Count: {summary.get('focus_term_count', 0)}")
    lines.append(f"- Highest TRL Target: {summary.get('highest_trl_target', 0)}")
    lines.append(f"- Disclosure Level: {summary.get('disclosure_level', '')}")
    lines.append("")

    for idx, row in enumerate(assets if isinstance(assets, list) else [], start=1):
        if not isinstance(row, dict):
            continue
        lines.append(f"## {idx}. {row.get('asset_name', '')}")
        lines.append(f"- Asset ID: {row.get('asset_id', '')}")
        lines.append(f"- Domain: {row.get('domain', '')}")
        lines.append(f"- TRL: {row.get('trl_current', 0)} -> {row.get('trl_target', 0)}")
        lines.append(f"- Thesis: {row.get('thesis', '')}")
        lines.append(f"- Valuation Lever: {row.get('valuation_lever', '')}")
        lines.append(f"- Confidence: {row.get('confidence_note', '')}")
        lines.append("- Scientific Basis:")
        for item in row.get("scientific_basis", []):
            lines.append(f"  - {item}")
        lines.append("- Architecture Stack:")
        for item in row.get("architecture_stack", []):
            lines.append(f"  - {item}")
        lines.append("- Validation Plan:")
        for item in row.get("validation_plan", []):
            lines.append(f"  - {item}")
        lines.append("- Grant Tags:")
        for item in row.get("grant_tags", []):
            lines.append(f"  - {item}")
        lines.append("")

    terms = payload.get("grant_focus_terms", []) if isinstance(payload, dict) else []
    lines.append("## Grant Focus Terms")
    lines.append(", ".join(str(x) for x in terms if str(x).strip()))
    lines.append("")
    return "\n".join(lines)


def write_heartbeat(
    *,
    status: str,
    reason: str,
    run_tag: str,
    exposure_level: str,
    summary: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_utc": now_iso(),
        "scope": "gov_blueprint_vault",
        "mode": "export",
        "status": str(status),
        "reason": str(reason),
        "run_tag": str(run_tag),
        "config": {
            "exposure_level": str(exposure_level),
        },
        "summary": summary if isinstance(summary, dict) else {},
        "artifacts": artifacts if isinstance(artifacts, dict) else {},
    }
    if error:
        payload["error"] = str(error)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    heartbeat_ts = OUT_DIR / f"gov_blueprint_vault_heartbeat_{run_tag}.json"
    txt = json.dumps(payload, indent=2)
    heartbeat_ts.write_text(txt, encoding="utf-8")
    HEARTBEAT_LATEST_PATH.write_text(txt, encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build government-grade blueprint vault for mission valuation and grant alignment.")
    parser.add_argument(
        "--exposure-level",
        default="highest_level",
        choices=["highest_level", "technical", "internal"],
        help="Narrative exposure level label for generated artifacts",
    )
    args = parser.parse_args()

    run_tag = now_tag()
    exposure_level = str(args.exposure_level)
    write_heartbeat(
        status="running",
        reason="build_started",
        run_tag=run_tag,
        exposure_level=exposure_level,
    )

    try:
        payload = build_payload(exposure_level=exposure_level)
        md = render_markdown(payload)

        json_ts = OUT_DIR / f"gov_blueprint_vault_{run_tag}.json"
        md_ts = OUT_DIR / f"gov_blueprint_vault_{run_tag}.md"
        json_latest = OUT_DIR / "gov_blueprint_vault_latest.json"
        md_latest = OUT_DIR / "gov_blueprint_vault_latest.md"

        write_json(json_ts, payload)
        write_json(json_latest, payload)
        write_text(md_ts, md)
        write_text(md_latest, md)

        summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
        write_heartbeat(
            status="ok",
            reason="build_complete",
            run_tag=run_tag,
            exposure_level=exposure_level,
            summary=summary if isinstance(summary, dict) else {},
            artifacts={
                "json_latest": str(json_latest),
                "json_timestamped": str(json_ts),
                "md_latest": str(md_latest),
                "md_timestamped": str(md_ts),
            },
        )

        print("BUILD_GOV_BLUEPRINT_VAULT")
        print(f"asset_count={summary.get('asset_count', 0)}")
        print(f"focus_term_count={summary.get('focus_term_count', 0)}")
        print(f"json={json_latest}")
        print(f"md={md_latest}")
        return 0
    except Exception as exc:
        write_heartbeat(
            status="error",
            reason="build_failed",
            run_tag=run_tag,
            exposure_level=exposure_level,
            error=str(exc),
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
