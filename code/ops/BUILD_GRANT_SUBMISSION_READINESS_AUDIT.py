from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GRANTS = ROOT / "grant_submissions"
OUT = ROOT / "out" / "ops"
DOCS = ROOT / "docs"

JSON_OUT = OUT / "grant_submission_readiness_audit_latest.json"
MD_OUT = GRANTS / "TOP5_SUBMISSION_READINESS_AUDIT_2026-06-19.md"
SAM_CAPTURE_JSON = OUT / "sam_gov_entity_status_capture_latest.json"
HARBOR_AIS_INJECTION_JSON = OUT / "harbor_ais_injection_benchmark_latest.json"
DICE_LIVE_REPLAY_JSON = OUT / "dice_live_breadth_replay_latest.json"
DICE_LIVE_REPLAY_ROOT = ROOT / "out" / "dice_live_breadth_replay"
HARBOR_REVIEW_BURDEN_JSON = OUT / "harbor_ais_review_burden_profile_latest.json"
HARBOR_REVIEW_BURDEN_ROOT = ROOT / "out" / "harbor_ais_review_burden"
LOCAL_ICLOUD_INTAKE_JSON = OUT / "local_icloud_evidence_intake_latest.json"
LOCAL_ICLOUD_INTAKE_MD = GRANTS / "LOCAL_ICLOUD_EVIDENCE_INTAKE_2026-06-21.md"

TOP5 = {
    "DICE": {
        "portal": "DARPA BAAT",
        "package": GRANTS / "DICE_HR001126S0010",
        "required_files": [
            GRANTS / "DICE_HR001126S0010" / "LumenCore_DICE_Abstract_WORKING_DRAFT.docx",
            GRANTS / "DICE_HR001126S0010" / "DICE_FINALIZATION_AUDIT_2026-06-19.md",
            GRANTS / "DICE_HR001126S0010" / "DICE_DOCX_QA_AND_REFERENCE_CHECK_2026-06-19.md",
            GRANTS / "DICE_HR001126S0010" / "DICE_REFERENCE_RELEVANCE_MATRIX_2026-06-20.md",
            GRANTS / "DICE_HR001126S0010" / "DICE_HEILMEIER_REVIEWER_MATRIX_2026-06-20.md",
            GRANTS / "DICE_HR001126S0010" / "DICE_EVIDENCE_SYNTHESIS_2026-06-20.md",
            GRANTS / "DICE_HR001126S0010" / "DICE_LIVE_BREADTH_REPLAY_2026-06-20.md",
            GRANTS / "LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md",
            LOCAL_ICLOUD_INTAKE_MD,
            GRANTS / "DICE_HR001126S0010" / "DICE_SUBMISSION_LOCK_PACKET_2026-06-20.md",
            GRANTS / "DICE_HR001126S0010" / "DICE_COST_BASIS_WORKING.md",
            GRANTS / "DICE_HR001126S0010" / "DICE_NEXT_11_DAY_SPRINT_2026-06-19.md",
            GRANTS / "DICE_HR001126S0010" / "render_qa_20260619_manual_clean_v5" / "LumenCore_DICE_Abstract_WORKING_DRAFT.pdf",
        ],
        "render_dir": GRANTS / "DICE_HR001126S0010" / "render_qa_20260619_manual_clean_v5",
        "min_png_pages": 7,
        "evidence_dirs": [
            ROOT / "out" / "dice_constraint_contract" / "20260618T_DICE_CONTRACT_V2_ROLE_SHUFFLE",
            ROOT / "out" / "dice_preliminary" / "20260613T_DICE_V1_500A_200PAIRS_OPT",
        ],
        "portal_blockers": [
            "BAAT account, organization profile, and submitter authority are unverified.",
            "SAM.gov entity status/linkage must be verified.",
            "DICE local submission lock packet exists; portal upload and certification remain blocked.",
            "Heilmeier/reviewer answer matrix exists; final human signoff is still required.",
            "Preliminary reference-relevance matrix exists; final human signoff is still required.",
            "Cost is an abstract-stage ROM planning estimate, not a reviewed cost proposal.",
            "Fresh action-time approval is required before any upload or submit action.",
        ],
    },
    "HarborSentinel": {
        "portal": "DSIP",
        "package": GRANTS / "NV063_HarborSentinel",
        "required_files": [
            GRANTS / "NV063_HarborSentinel" / "NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.md",
            GRANTS / "NV063_HarborSentinel" / "NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.docx",
            GRANTS / "NV063_HarborSentinel" / "NV063_FINALIZATION_AUDIT_2026-06-19.md",
            GRANTS / "NV063_HarborSentinel" / "NV063_REPRESENTATIVE_DATA_AND_FORMAT_PLAN_2026-06-19.md",
            GRANTS / "NV063_HarborSentinel" / "NV063_DATA_SOURCE_ACCESS_AUDIT_2026-06-20.md",
            GRANTS / "NV063_HarborSentinel" / "NV063_AIS_PILOT_SOURCE_REGISTRY_2026-06-20.md",
            GRANTS / "NV063_HarborSentinel" / "NV063_AIS_PILOT_ACQUISITION_2026-06-20.md",
            GRANTS / "NV063_HarborSentinel" / "NV063_AIS_HELDOUT_SPLIT_MANIFEST_2026-06-20.md",
            GRANTS / "NV063_HarborSentinel" / "NV063_PUBLIC_AIS_GATE_2026-06-20.md",
            GRANTS / "NV063_HarborSentinel" / "NV063_AIS_INJECTION_BENCHMARK_2026-06-20.md",
            GRANTS / "NV063_HarborSentinel" / "NV063_AIS_REVIEW_BURDEN_PROFILE_2026-06-21.md",
            GRANTS / "NV063_HarborSentinel" / "NV063_NAVY_REVIEWER_PROOF_MATRIX_2026-06-20.md",
            GRANTS / "LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md",
            LOCAL_ICLOUD_INTAKE_MD,
            GRANTS / "NV063_HarborSentinel" / "NV063_VOLUME2_SOURCE_QA_2026-06-19.md",
            GRANTS / "NV063_HarborSentinel" / "NV063_COST_BASIS_WORKING.md",
            GRANTS / "NV063_HarborSentinel" / "render_qa_20260620_baselines_v1" / "NV063_VOLUME2_TECHNICAL_DRAFT_2026-06-19.pdf",
        ],
        "render_dir": GRANTS / "NV063_HarborSentinel" / "render_qa_20260620_baselines_v1",
        "min_png_pages": 6,
        "evidence_dirs": [
            ROOT / "out" / "harbor_sentinel_validation" / "20260619T_NV063_V6_SOURCE_LANE_COVERAGE",
        ],
        "portal_blockers": [
            "DSIP organization linkage and submitter authority are unverified.",
            "DoD representations, FOCI, export, cybersecurity, and U.S. ownership/operation checks remain.",
            "CMMC/SPRS/Affirming Official status is unverified.",
            "Navy reviewer proof matrix exists; final human/domain signoff is still required.",
            "Public NOAA AIS raw data, held-out splits, and single-lane AIS readiness gate exist, but this is still public AIS data-readiness evidence rather than HarborSentinel detection-performance, multi-source fusion, ADS-B, radar, Navy/SSDS, or field validation.",
            "Final DSIP upload preview and fresh action-time approval are required.",
        ],
    },
    "NSF Project Pitch": {
        "portal": "NSF Seed Fund Project Pitch portal",
        "package": GRANTS / "NSF_Project_Pitch",
        "required_files": [
            GRANTS / "NSF_Project_Pitch" / "PROJECT_PITCH_PORTAL_FIELDS_2026-06-19.md",
            GRANTS / "NSF_Project_Pitch" / "PROJECT_PITCH_PASTE_CHECK_2026-06-19.md",
            GRANTS / "NSF_Project_Pitch" / "PROJECT_PITCH_READINESS.md",
        ],
        "evidence_dirs": [],
        "portal_blockers": [
            "Legal business name and PI/founder title must be confirmed.",
            "Duplicate-pitch/open-invitation/full-proposal status must be checked in the portal.",
            "Portal paste counts must be confirmed after the user logs in.",
            "Fresh action-time approval is required before final save/submit actions.",
        ],
    },
    "MissionWeave": {
        "portal": "DSIP",
        "package": GRANTS / "DLA26BZ03_NV011_MissionWeave",
        "required_files": [
            GRANTS / "DLA26BZ03_NV011_MissionWeave" / "MISSIONWEAVE_CONCEPT_DRAFT.md",
            GRANTS / "DLA26BZ03_NV011_MissionWeave" / "MISSIONWEAVE_FINALIZATION_AUDIT_2026-06-19.md",
            GRANTS / "DLA26BZ03_NV011_MissionWeave" / "MISSIONWEAVE_BOUNDED_PROCESS_PLAN_2026-06-19.md",
            GRANTS / "DLA26BZ03_NV011_MissionWeave" / "MISSIONWEAVE_COST_BASIS_WORKING.md",
        ],
        "evidence_dirs": [
            ROOT / "out" / "missionweave_validation" / "20260613T_MISSIONWEAVE_V3_DEV16_VAL30",
        ],
        "portal_blockers": [
            "Selected bounded process needs user/domain confirmation.",
            "DSIP topic budget/form requirements and organization linkage are unverified.",
            "Representative-data path and DLA-domain review are not complete.",
            "Fresh action-time approval is required before any upload or submit action.",
        ],
    },
    "NV065": {
        "portal": "DSIP",
        "package": GRANTS / "NV065_AdaptiveSensorManagement",
        "required_files": [
            GRANTS / "NV065_AdaptiveSensorManagement" / "NV065_CONCEPT_DRAFT.md",
            GRANTS / "NV065_AdaptiveSensorManagement" / "NV065_FINALIZATION_AUDIT_2026-06-19.md",
            GRANTS / "NV065_AdaptiveSensorManagement" / "NV065_COST_BASIS_WORKING.md",
        ],
        "evidence_dirs": [
            ROOT / "out" / "nv065_sensor_tasking" / "20260619T_NV065_SENSOR_TASKING_V2_SENSOR_PROFILE",
        ],
        "portal_blockers": [
            "Representative radar-resource assumptions need sensor-domain review.",
            "DSIP account, organization linkage, and compliance gates are unverified.",
            "Cost basis is a ROM planning estimate only.",
            "Fresh action-time approval is required before any upload or submit action.",
        ],
    },
}

GEOMETRY_REGISTRY = ROOT / "out" / "geometry_championship_v1" / "20260621T_GEOMETRY_READINESS_V4_EXPANDED_75"

RISKY_CLAIMS = [
    "field validated",
    "operationally validated",
    "ssds integrated",
    "cmmc certified",
    "classified performance",
    "trading profit",
    "guaranteed award",
    "demo site committed",
]

NSF_LIMITS = {
    "Technology Innovation": 3500,
    "Technical Objectives and Challenges": 3500,
    "Market Opportunity": 1750,
    "Company and Team": 1750,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = load_json(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def sam_capture() -> dict[str, Any]:
    payload = read_json(SAM_CAPTURE_JSON)
    if payload.get("schema") != "sam_gov_entity_status_capture_v1":
        return {}
    return payload


def sam_is_active(payload: dict[str, Any]) -> bool:
    return str(payload.get("registration_status", "")).strip().lower() == "active registration"


def harbor_injection_benchmark() -> dict[str, Any]:
    payload = read_json(HARBOR_AIS_INJECTION_JSON)
    if payload.get("schema") != "harbor_ais_injection_benchmark_v1":
        return {}
    return payload


def harbor_injection_ready(payload: dict[str, Any]) -> bool:
    return str(payload.get("posture", "")).strip() == "PUBLIC_AIS_INJECTION_BENCHMARK_READY"


def harbor_review_burden_profile() -> dict[str, Any]:
    payload = read_json(HARBOR_REVIEW_BURDEN_JSON)
    if payload.get("schema") != "harbor_ais_review_burden_profile_v1":
        return {}
    return payload


def harbor_review_burden_ready(payload: dict[str, Any]) -> bool:
    gate = payload.get("claim_gate", {}) if isinstance(payload, dict) else {}
    return (
        payload.get("posture") == "PUBLIC_AIS_REVIEW_BURDEN_PROFILE_READY"
        and bool(gate.get("ready_for_portal_upload")) is False
        and bool(gate.get("measures_false_positive_rate")) is False
        and int((payload.get("review_queue", {}) or {}).get("validation_candidates", 0) or 0) > 0
    )


def dice_live_replay() -> dict[str, Any]:
    payload = read_json(DICE_LIVE_REPLAY_JSON)
    if payload.get("schema") != "dice_live_breadth_replay_v1":
        return {}
    return payload


def dice_live_replay_ready(payload: dict[str, Any]) -> bool:
    gate = payload.get("claim_gate", {}) if isinstance(payload, dict) else {}
    return (
        payload.get("schema") == "dice_live_breadth_replay_v1"
        and bool(gate.get("ready_for_portal_upload")) is False
        and bool(gate.get("live_replay_proves_dice_metric_attainment")) is False
        and int((payload.get("configuration", {}) or {}).get("scenario_count", 0) or 0) > 0
    )


def local_icloud_intake() -> dict[str, Any]:
    payload = read_json(LOCAL_ICLOUD_INTAKE_JSON)
    if payload.get("schema") != "local_icloud_evidence_intake_v1":
        return {}
    return payload


def local_icloud_intake_ready(payload: dict[str, Any]) -> bool:
    gate = payload.get("claim_gate", {}) if isinstance(payload, dict) else {}
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    return (
        payload.get("schema") == "local_icloud_evidence_intake_v1"
        and bool(gate.get("ready_for_portal_upload")) is False
        and bool(gate.get("field_validation_proven")) is False
        and int(summary.get("records", 0) or 0) > 0
    )


def latest_run_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    candidates = [path for path in root.iterdir() if path.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def verify_manifest(run_dir: Path) -> dict[str, Any]:
    manifest = run_dir / "manifest.sha256.json"
    result: dict[str, Any] = {
        "run_dir": rel(run_dir),
        "manifest": rel(manifest),
        "exists": manifest.exists(),
        "matched": 0,
        "expected": 0,
        "mismatches": [],
    }
    if not manifest.exists():
        result["mismatches"].append("missing manifest.sha256.json")
        return result
    data = load_json(manifest)
    files = data.get("files", {}) if isinstance(data, dict) else {}
    result["schema"] = data.get("schema") if isinstance(data, dict) else None
    result["generated_utc"] = data.get("generated_utc") if isinstance(data, dict) else None
    result["expected"] = len(files)
    for name, expected in files.items():
        target = run_dir / name
        if not target.exists():
            result["mismatches"].append(f"{name}: missing")
            continue
        actual_bytes = target.stat().st_size
        actual_sha = sha256_file(target)
        expected_bytes = int(expected.get("bytes", -1))
        expected_sha = str(expected.get("sha256", ""))
        if actual_bytes == expected_bytes and actual_sha == expected_sha:
            result["matched"] += 1
        else:
            result["mismatches"].append(
                f"{name}: expected {expected_bytes}/{expected_sha}, got {actual_bytes}/{actual_sha}"
            )
    return result


def file_status(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": rel(path),
        "exists": exists,
        "bytes": path.stat().st_size if exists and path.is_file() else None,
    }


def render_status(render_dir: Path | None, min_png_pages: int | None) -> dict[str, Any] | None:
    if render_dir is None:
        return None
    pdfs = sorted(render_dir.glob("*.pdf")) if render_dir.exists() else []
    pngs = sorted(render_dir.glob("*.png")) if render_dir.exists() else []
    return {
        "render_dir": rel(render_dir),
        "exists": render_dir.exists(),
        "pdf_count": len(pdfs),
        "png_count": len(pngs),
        "min_png_pages": min_png_pages,
        "ok": render_dir.exists() and len(pdfs) >= 1 and len(pngs) >= int(min_png_pages or 0),
        "pdfs": [rel(p) for p in pdfs],
    }


def read_all_package_text(package_dir: Path) -> str:
    chunks = []
    for path in sorted(package_dir.glob("*.md")):
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            pass
    return "\n".join(chunks).lower()


def claim_scan(package_dir: Path) -> list[str]:
    text = read_all_package_text(package_dir)
    hits = []
    lines = text.splitlines()
    for phrase in RISKY_CLAIMS:
        for idx, line in enumerate(lines):
            if phrase not in line:
                continue
            prior_two = lines[max(idx - 2, 0):idx]
            context = " ".join([*prior_two, line])
            # Boundary language is desirable; only flag positive/unqualified claims.
            if any(
                marker in context
                for marker in (
                    "do not",
                    "do not use",
                    "does not",
                    "cannot",
                    "no ",
                    "not ",
                    "without ",
                    "never ",
                    "false",
                    "claim_gate",
                )
            ):
                continue
            hits.append(phrase)
            break
    return hits


def extract_nsf_fields(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="ignore")
    fields: dict[str, dict[str, Any]] = {}
    headings = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    for idx, match in enumerate(headings):
        title = re.sub(r"^\d+\.\s*", "", match.group(1).strip())
        if title not in NSF_LIMITS:
            continue
        start = match.end()
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(text)
        body = text[start:end].strip()
        count = len(body)
        fields[title] = {
            "characters": count,
            "limit": NSF_LIMITS[title],
            "ok": count <= NSF_LIMITS[title],
            "remaining": NSF_LIMITS[title] - count,
        }
    return fields


def package_audit(name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    evidence_dirs = list(cfg.get("evidence_dirs", []))
    if name == "DICE":
        latest_live_replay = latest_run_dir(DICE_LIVE_REPLAY_ROOT)
        if latest_live_replay is not None:
            evidence_dirs.append(latest_live_replay)
    if name == "HarborSentinel":
        latest_review_burden = latest_run_dir(HARBOR_REVIEW_BURDEN_ROOT)
        if latest_review_burden is not None:
            evidence_dirs.append(latest_review_burden)
    required = [file_status(path) for path in cfg.get("required_files", [])]
    missing = [row["path"] for row in required if not row["exists"]]
    manifests = [verify_manifest(path) for path in evidence_dirs]
    manifest_blockers = [
        f"{row['run_dir']}: {item}"
        for row in manifests
        for item in row.get("mismatches", [])
    ]
    render = render_status(cfg.get("render_dir"), cfg.get("min_png_pages"))
    render_blockers = []
    if render is not None and not render["ok"]:
        render_blockers.append(f"{render['render_dir']}: render QA packet incomplete")
    claim_hits = claim_scan(cfg["package"])
    claim_blockers = [f"risky claim phrase found in markdown: {hit}" for hit in claim_hits]

    nsf_fields = {}
    nsf_blockers = []
    if name == "NSF Project Pitch":
        nsf_fields = extract_nsf_fields(cfg["package"] / "PROJECT_PITCH_PORTAL_FIELDS_2026-06-19.md")
        missing_fields = [field for field in NSF_LIMITS if field not in nsf_fields]
        nsf_blockers.extend(f"missing NSF field: {field}" for field in missing_fields)
        nsf_blockers.extend(
            f"{field}: {row['characters']} exceeds {row['limit']}"
            for field, row in nsf_fields.items()
            if not row["ok"]
        )

    local_blockers = []
    local_blockers.extend(f"missing required artifact: {path}" for path in missing)
    local_blockers.extend(manifest_blockers)
    local_blockers.extend(render_blockers)
    local_blockers.extend(claim_blockers)
    local_blockers.extend(nsf_blockers)

    portal_blockers = list(cfg.get("portal_blockers", []))
    verified_portal_facts: list[str] = []
    sam = sam_capture()
    if sam_is_active(sam):
        verified_portal_facts.append(
            "SAM.gov active registration verified from signed-in workspace: "
            "SAM entity identifiers recorded, "
            f"purpose {sam.get('purpose_of_registration', 'recorded')}, "
            f"expiration {sam.get('expiration_date', 'recorded')}."
        )
        portal_blockers = [
            item
            for item in portal_blockers
            if item != "SAM.gov entity status/linkage must be verified."
        ]
    if name == "HarborSentinel":
        injection = harbor_injection_benchmark()
        if harbor_injection_ready(injection):
            result = injection.get("controlled_injection_benchmark", {})
            verified_portal_facts.append(
                "HarborSentinel public AIS controlled-injection benchmark ready: "
                f"{result.get('total_injected_segments', 'n/a')} injected validation segments, "
                f"motion-consistency recall {result.get('motion_consistency_recall', 'n/a')}, "
                f"speed-only baseline recall {result.get('speed_only_baseline_recall', 'n/a')}; "
                f"best single-axis baseline recall "
                f"{result.get('baseline_suite', {}).get('best_single_axis_baseline', {}).get('recall', 'n/a')}; "
                "boundary: controlled kinematic injections are not real threat labels, multi-source fusion, or field validation."
            )
            portal_blockers = [
                item
                for item in portal_blockers
                if item
                != "Public NOAA AIS raw data, held-out splits, and single-lane AIS readiness gate exist, but this is still public AIS data-readiness evidence rather than HarborSentinel detection-performance, multi-source fusion, ADS-B, radar, Navy/SSDS, or field validation."
            ]
        review_burden = harbor_review_burden_profile()
        if harbor_review_burden_ready(review_burden):
            queue = review_burden.get("review_queue", {})
            tiers = {
                str(row.get("density_tier")): row
                for row in review_burden.get("density_tiers", []) or []
                if isinstance(row, dict)
            }
            verified_portal_facts.append(
                "HarborSentinel AIS review-burden profile ready: "
                f"validation candidate rate {queue.get('validation_candidate_rate', 'n/a')}, "
                f"mean candidates/hour {queue.get('mean_candidates_per_hour', 'n/a')}, "
                f"p95 candidates/hour {queue.get('p95_candidates_per_hour', 'n/a')}, "
                f"sparse-tier candidate rate {(tiers.get('sparse') or {}).get('candidate_rate', 'n/a')}; "
                "boundary: unlabeled review queue, not precision, false-positive rate, field validation, or operational suitability."
            )
    if name == "DICE":
        replay = dice_live_replay()
        if dice_live_replay_ready(replay):
            paired = replay.get("paired_metrics", {})
            config = replay.get("configuration", {})
            source_manifest = replay.get("source_manifest", {})
            safe = (paired.get("safe_completion_rate", {}) or {}).get("mean_delta", "n/a")
            violation = (paired.get("constraint_violation_rate", {}) or {}).get("mean_delta", "n/a")
            messages = (paired.get("messages_per_safe_completion", {}) or {}).get("mean_delta", "n/a")
            false_rejection = (paired.get("false_rejection_rate", {}) or {}).get("mean_delta", "n/a")
            verified_portal_facts.append(
                "DICE frozen live-breadth replay ready: "
                f"{source_manifest.get('source_count', 'n/a')} live-source files, "
                f"{config.get('scenario_count', 'n/a')} deterministic replay windows, "
                f"safe-completion delta {safe}, constraint-violation delta {violation}, "
                f"messages-per-safe-completion delta {messages}; known cost: false-rejection delta {false_rejection}. "
                "Boundary: live rows are stress signals with deterministic derived labels, not DICE metric attainment, field validation, or trading proof."
            )
    if name in {"DICE", "HarborSentinel"}:
        intake = local_icloud_intake()
        if local_icloud_intake_ready(intake):
            summary = intake.get("summary", {})
            by_lane = summary.get("by_grant_lane", {}) if isinstance(summary, dict) else {}
            verified_portal_facts.append(
                "Local/iCloud legacy evidence intake ready: "
                f"{summary.get('records', 'n/a')} candidate records across local and iCloud roots, "
                f"{by_lane.get('evidence_provenance', 'n/a')} provenance records, "
                f"{by_lane.get('federal_grant_context', 'n/a')} federal-grant context records, "
                f"{by_lane.get('DOE_or_critical_infrastructure', 'n/a')} DOE/critical-infrastructure records. "
                "Boundary: metadata/provenance intake only; not field validation, performance proof, trading profit, or portal authority."
            )
    readiness = "LOCAL_READY_PORTAL_BLOCKED" if not local_blockers else "LOCAL_BLOCKED"
    if portal_blockers:
        readiness = readiness + "_USER_GATES"

    return {
        "name": name,
        "portal": cfg["portal"],
        "readiness": readiness,
        "required_artifacts": required,
        "evidence_manifests": manifests,
        "render": render,
        "nsf_fields": nsf_fields,
        "local_blockers": local_blockers,
        "portal_user_blockers": portal_blockers,
        "verified_portal_facts": verified_portal_facts,
    }


def build_audit() -> dict[str, Any]:
    packages = [package_audit(name, cfg) for name, cfg in TOP5.items()]
    geometry = verify_manifest(GEOMETRY_REGISTRY)
    sam = sam_capture()
    local_blocker_count = sum(len(pkg["local_blockers"]) for pkg in packages)
    portal_blocker_count = sum(len(pkg["portal_user_blockers"]) for pkg in packages)
    posture = "LOCAL_READY_PORTAL_BLOCKED" if local_blocker_count == 0 else "LOCAL_BLOCKED"
    return {
        "generated_utc": now_utc(),
        "schema": "grant_submission_readiness_audit_v1",
        "posture": posture,
        "summary": {
            "packages": len(packages),
            "local_blockers": local_blocker_count,
            "portal_user_blockers": portal_blocker_count,
            "geometry_registry_matched": geometry.get("matched"),
            "geometry_registry_expected": geometry.get("expected"),
        },
        "packages": packages,
        "geometry_registry": geometry,
        "sam_gov": {
            "verified": sam_is_active(sam),
            "status": sam.get("registration_status", "unverified"),
            "expiration_date": sam.get("expiration_date", ""),
            "purpose_of_registration": sam.get("purpose_of_registration", ""),
            "capture": rel(SAM_CAPTURE_JSON) if sam else "",
            "boundary": (
                "SAM active registration reduces entity-status uncertainty. It does not verify BAAT, "
                "DSIP, Grants.gov, Research.gov, CMMC/SPRS, Affirming Official authority, cost validity, "
                "or final submit authority."
            ),
        },
        "claim_boundary": (
            "Live-measured rows and frozen live replay are the promoted evidence lanes. "
            "Synthetic benchmarks remain bounded controls for labels, ablations, and failure injection only. "
            "Portal authority, certifications, partners, cost validity, field validation, and submit actions "
            "remain user-verified gates."
        ),
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Top-Five Grant Submission Readiness Audit",
        "",
        f"Generated UTC: {audit['generated_utc']}",
        "",
        f"Posture: {audit['posture']}",
        "",
        "## Summary",
        "",
        f"- Packages checked: {audit['summary']['packages']}",
        f"- Local blockers: {audit['summary']['local_blockers']}",
        f"- Portal/user blockers: {audit['summary']['portal_user_blockers']}",
        f"- Geometry registry manifest: {audit['summary']['geometry_registry_matched']}/{audit['summary']['geometry_registry_expected']} matched",
        "",
        "## Verified Portal Facts",
        "",
        f"- SAM.gov verified: {audit.get('sam_gov', {}).get('verified')}",
        f"- SAM.gov status: {audit.get('sam_gov', {}).get('status')}",
        f"- SAM.gov expiration: {audit.get('sam_gov', {}).get('expiration_date') or 'n/a'}",
        f"- SAM.gov purpose: {audit.get('sam_gov', {}).get('purpose_of_registration') or 'n/a'}",
        f"- Boundary: {audit.get('sam_gov', {}).get('boundary')}",
        "",
        "## Claim Boundary",
        "",
        audit["claim_boundary"],
        "",
        "## Package Readiness",
        "",
    ]
    for pkg in audit["packages"]:
        lines.extend(
            [
                f"### {pkg['name']}",
                "",
                f"- portal: {pkg['portal']}",
                f"- readiness: {pkg['readiness']}",
                f"- required artifacts present: {sum(1 for row in pkg['required_artifacts'] if row['exists'])}/{len(pkg['required_artifacts'])}",
                f"- evidence manifests matched: {sum(row['matched'] for row in pkg['evidence_manifests'])}/{sum(row['expected'] for row in pkg['evidence_manifests'])}",
            ]
        )
        if pkg.get("render"):
            render = pkg["render"]
            lines.append(f"- render QA: pdfs={render['pdf_count']}, pngs={render['png_count']}, min_png_pages={render['min_png_pages']}, ok={render['ok']}")
        if pkg.get("nsf_fields"):
            lines.append("- NSF field counts:")
            for field, row in pkg["nsf_fields"].items():
                lines.append(f"  - {field}: {row['characters']}/{row['limit']} ({row['remaining']} remaining)")
        if pkg.get("verified_portal_facts"):
            lines.append("- verified portal facts:")
            lines.extend(f"  - {item}" for item in pkg["verified_portal_facts"])
        lines.append("- local blockers:")
        if pkg["local_blockers"]:
            lines.extend(f"  - {item}" for item in pkg["local_blockers"])
        else:
            lines.append("  - none")
        lines.append("- portal/user blockers:")
        if pkg["portal_user_blockers"]:
            lines.extend(f"  - {item}" for item in pkg["portal_user_blockers"])
        else:
            lines.append("  - none")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    GRANTS.mkdir(parents=True, exist_ok=True)
    audit = build_audit()
    JSON_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    MD_OUT.write_text(render_markdown(audit), encoding="utf-8")
    print(json.dumps({"posture": audit["posture"], "local_blockers": audit["summary"]["local_blockers"], "portal_user_blockers": audit["summary"]["portal_user_blockers"], "json": rel(JSON_OUT), "md": rel(MD_OUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
