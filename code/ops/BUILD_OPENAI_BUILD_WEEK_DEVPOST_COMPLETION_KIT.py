from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "grant_submissions" / "OPENAI_BUILD_WEEK_20260721"
FIELD_REGISTRY_PATH = OUT_DIR / "OPENAI_BUILD_WEEK_DEVPOST_FIELD_REGISTRY_2026-07-18.json"
PROJECT_COPY_PATH = OUT_DIR / "OPENAI_BUILD_WEEK_DEVPOST_PROJECT_COPY_2026-07-18.md"
COMPLETION_KIT_PATH = OUT_DIR / "OPENAI_BUILD_WEEK_DEVPOST_COMPLETION_KIT_2026-07-18.md"
READINESS_RECEIPT_PATH = OUT_DIR / "OPENAI_BUILD_WEEK_DEVPOST_READINESS_RECEIPT_2026-07-18.json"
PORTAL_PROGRESS_RECEIPT_PATH = OUT_DIR / "OPENAI_BUILD_WEEK_PORTAL_PROGRESS_2026-07-19.json"
ORCHESTRATION_RECEIPT_PATH = OUT_DIR / "CODEX_AGENT_ORCHESTRATION_RECEIPT_2026-07-19.json"
VIDEO_WORK_DIR = ROOT / "output" / "video" / "prooflock_console_build_week_v1"
DEMO_VIDEO_PATH = VIDEO_WORK_DIR / "prooflock_console_openai_build_week_demo_v1.mp4"
DEMO_VIDEO_RECEIPT_PATH = VIDEO_WORK_DIR / "prooflock_console_openai_build_week_demo_v1.receipt.json"
THUMBNAIL_PATH = VIDEO_WORK_DIR / "prooflock_console_devpost_thumbnail_v1.png"

DEADLINE_CENTRAL = "2026-07-21T19:00:00-05:00"
DEADLINE_UTC = "2026-07-22T00:00:00Z"
PUBLIC_COMMIT = "281b76fe20d281974a2e2b44670a6a63815fe421"
PUBLIC_SCOPED_SOURCE_URL = (
    "https://github.com/robertashworth1986-debug/lumen-core-public/tree/"
    f"{PUBLIC_COMMIT}/build_week/prooflock_console"
)

OFFICIAL_SOURCES = {
    "overview": "https://openai.devpost.com/",
    "rules": "https://openai.devpost.com/rules",
    "submission_manager": "https://devpost.com/submit-to/30223-openai-build-week/manage/submissions",
    "devpost_submission_steps": "https://help.devpost.com/article/126-know-your-submission-steps",
}

SOURCE_PATHS = {
    "readiness_snapshot": OUT_DIR / "OPENAI_BUILD_WEEK_SUBMISSION_READINESS_2026-07-17.json",
    "requirements_receipt": OUT_DIR / "OPENAI_BUILD_WEEK_REQUIREMENTS_RECEIPT_2026-07-17.json",
    "public_demo_receipt": OUT_DIR / "OPENAI_BUILD_WEEK_PUBLIC_DEMO_RECEIPT_2026-07-18.json",
    "browser_qa_receipt": OUT_DIR / "OPENAI_BUILD_WEEK_BROWSER_QA_CAPTURE_2026-07-18.json",
    "description_draft": OUT_DIR / "OPENAI_BUILD_WEEK_PROJECT_DESCRIPTION_DRAFT_2026-07-17.md",
    "demo_script": OUT_DIR / "OPENAI_BUILD_WEEK_DEMO_SCRIPT_2026-07-17.md",
    "prooflock_readme": ROOT / "build_week" / "prooflock_console" / "README.md",
    "sample_receipt": ROOT / "build_week" / "prooflock_console" / "sample_receipt.json",
    "repository_license": ROOT / "LICENSE",
    "portal_progress_receipt": PORTAL_PROGRESS_RECEIPT_PATH,
    "orchestration_receipt": ORCHESTRATION_RECEIPT_PATH,
    "demo_video_receipt": DEMO_VIDEO_RECEIPT_PATH,
    "demo_video": DEMO_VIDEO_PATH,
    "thumbnail_asset": THUMBNAIL_PATH,
}

RECORD_HASH_KEYS = {
    "readiness_snapshot": "packet_sha256",
    "requirements_receipt": "receipt_sha256",
    "public_demo_receipt": "receipt_sha256",
    "browser_qa_receipt": "capture_sha256",
    "portal_progress_receipt": "receipt_sha256",
    "orchestration_receipt": "receipt_sha256",
    "demo_video_receipt": "receipt_sha256",
}

MODEL_USAGE_SENTENCE = (
    "A lead Codex workflow coordinated bounded specialist roles for implementation, adversarial testing, "
    "evidence reconciliation, and independent review. A privacy-preserving machine receipt records five "
    "identity-backed Build Week spawn events across five role categories, with one completion directly "
    "observed; maximum concurrency remains NOT_PROVEN. The active build task records gpt-5.6-sol at ultra "
    "reasoning effort."
)

PLACEHOLDERS = {
    "confirmed_model_label": "gpt-5.6-sol",
    "model_usage_sentence": MODEL_USAGE_SENTENCE,
    "feedback_session_id": None,
    "public_youtube_url": None,
    "thumbnail_asset": "output/video/prooflock_console_build_week_v1/prooflock_console_devpost_thumbnail_v1.png",
    "submitter_type": None,
    "country_of_residence": None,
    "representative_authorization": None,
}

CLAIM_BOUNDARY = (
    "This kit prepares source-backed draft content and a field-by-field completion contract. "
    "It confirms a bounded project draft and locally verified release assets. It does not prove a /feedback "
    "Session ID, eligibility, ownership, legal acceptance, video publication, final submission, "
    "judging outcome, endorsement, award, external validation, patent rights, safety, funding, or value."
)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"path escapes repository root: {path}") from exc


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {repo_relative(path)}")
    return payload


def validate_embedded_hash(payload: dict[str, Any], hash_key: str) -> dict[str, Any]:
    recorded = str(payload.get(hash_key) or "").lower()
    unhashed = dict(payload)
    unhashed.pop(hash_key, None)
    computed = stable_hash(unhashed)
    return {
        "hash_key": hash_key,
        "recorded": recorded,
        "computed": computed,
        "valid": bool(recorded) and recorded == computed,
    }


def source_registry() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for source_id, path in SOURCE_PATHS.items():
        if not path.is_file():
            raise FileNotFoundError(f"required Build Week source is missing: {repo_relative(path)}")
        row: dict[str, Any] = {
            "source_id": source_id,
            "path": repo_relative(path),
            "bytes": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        hash_key = RECORD_HASH_KEYS.get(source_id)
        if hash_key:
            row["embedded_integrity"] = validate_embedded_hash(load_json(path), hash_key)
            if not row["embedded_integrity"]["valid"]:
                raise ValueError(f"embedded hash is invalid: {repo_relative(path)}")
        rows[source_id] = row
    return rows


def readiness_snapshot() -> dict[str, Any]:
    payload = load_json(SOURCE_PATHS["readiness_snapshot"])
    counts = payload.get("counts") or {}
    expected = {"gate_total": 10, "pass": 5, "open": 5, "fail": 0}
    observed = {key: counts.get(key) for key in expected}
    if observed != expected:
        raise ValueError(f"Build Week gate snapshot changed: expected {expected}, observed {observed}")
    if payload.get("ready_for_final_submission") is not False:
        raise ValueError("readiness source unexpectedly promotes final submission")

    gates = {row.get("gate_id"): row.get("status") for row in payload.get("gates", [])}
    expected_open = {
        "model_provenance",
        "feedback_session",
        "youtube_demo",
        "devpost_registration",
        "final_submission",
    }
    observed_open = {gate_id for gate_id, status in gates.items() if status == "OPEN"}
    if observed_open != expected_open:
        raise ValueError(
            f"Build Week open-gate set changed: expected {sorted(expected_open)}, "
            f"observed {sorted(observed_open)}"
        )
    return {
        "status": payload.get("status"),
        "counts": expected,
        "core_ready": payload.get("core_ready") is True,
        "ready_for_final_submission": False,
        "open_gate_ids": sorted(expected_open),
        "packet_sha256": payload.get("packet_sha256"),
        "source_path": repo_relative(SOURCE_PATHS["readiness_snapshot"]),
    }


def portal_progress_snapshot() -> dict[str, Any]:
    payload = load_json(PORTAL_PROGRESS_RECEIPT_PATH)
    integrity = validate_embedded_hash(payload, "receipt_sha256")
    if not integrity["valid"]:
        raise ValueError("portal progress receipt hash is invalid")

    facts = payload.get("normalized_facts")
    if not isinstance(facts, dict) or payload.get("facts_sha256") != stable_hash(facts):
        raise ValueError("portal progress normalized facts hash is invalid")

    browser = facts.get("browser_confirmation") or {}
    gmail = facts.get("gmail_confirmation") or {}
    expected_gmail_metadata = {
        "message_id": "19f795524f98f57a",
        "sender": "Devpost <support@devpost.com>",
        "subject": "OpenAI Build Week: You're in!",
        "timestamp_utc": "2026-07-19T07:44:10Z",
    }
    observed_gmail_metadata = {key: gmail.get(key) for key in expected_gmail_metadata}
    if observed_gmail_metadata != expected_gmail_metadata:
        raise ValueError("portal progress Gmail metadata differs from the bounded evidence contract")

    expected_open = [
        "additional_info_completion",
        "feedback_session_id",
        "final_preview_review",
        "final_submission",
        "project_details_completion",
        "public_youtube_video",
    ]
    required_states = {
        "schema": payload.get("schema") == "lumencore.openai_build_week_portal_progress_receipt.v1",
        "status": payload.get("status") == "PROJECT_DRAFT_2_OF_5_VIDEO_FEEDBACK_OPEN",
        "basis_count": payload.get("evidence_basis_count") == 2,
        "registration": payload.get("registration_confirmed") is True,
        "project": payload.get("project_shell_creation_confirmed") is True,
        "submission": payload.get("final_submission_confirmed") is False,
        "ready": payload.get("ready_for_final_submission") is False,
        "open_gates": payload.get("open_gate_ids") == expected_open,
        "browser_class": browser.get("evidence_class") == "DIRECT_BROWSER_OBSERVATION",
        "browser_text": browser.get("visible_confirmation_text") == "ProofLock Console | Draft | 2/5 steps done",
        "browser_url": browser.get("page_url", "").endswith(
            "/1104232-prooflock-console/project_details/edit"
        ),
        "browser_registration": browser.get("challenge_registration_confirmed") is True,
        "project_name": browser.get("project_name") == "ProofLock Console",
        "project_state": browser.get("project_state") == "DRAFT",
        "steps": browser.get("steps_completed") == 2 and browser.get("steps_total") == 5,
        "project_proven": browser.get("project_shell_creation_proven") is True,
        "gmail_class": gmail.get("evidence_class") == "INDEPENDENT_GMAIL_METADATA",
        "gmail_registration": gmail.get("bounded_confirmation", {}).get(
            "challenge_registration_confirmed"
        )
        is True,
        "gmail_deadline": gmail.get("bounded_confirmation", {}).get("deadline_utc") == DEADLINE_UTC,
        "gmail_metadata_only": gmail.get("message_body_retained") is False,
        "no_tracking": gmail.get("tracking_links_retained") is False,
        "no_private_ids": gmail.get("private_account_identifiers_retained") is False,
    }
    failed = sorted(key for key, valid in required_states.items() if not valid)
    if failed:
        raise ValueError(f"portal progress receipt failed closed checks: {failed}")

    return {
        "source_path": repo_relative(PORTAL_PROGRESS_RECEIPT_PATH),
        "receipt_sha256": payload["receipt_sha256"],
        "facts_sha256": payload["facts_sha256"],
        "recorded_observation_utc": payload["recorded_observation_utc"],
        "evidence_basis_count": 2,
        "evidence_classes": ["DIRECT_BROWSER_OBSERVATION", "INDEPENDENT_GMAIL_METADATA"],
        "challenge_registration_state": "CONFIRMED",
        "project_shell_creation_state": "DRAFT_2_OF_5_CONFIRMED",
        "submission_confirmation_state": "NONE_OBSERVED",
        "open_gate_ids": expected_open,
    }


def effective_readiness(snapshot: dict[str, Any], portal_progress: dict[str, Any]) -> dict[str, Any]:
    if portal_progress.get("challenge_registration_state") != "CONFIRMED":
        raise ValueError("portal progress does not confirm challenge registration")
    open_gate_ids = set(snapshot["open_gate_ids"])
    if "devpost_registration" not in open_gate_ids:
        raise ValueError("base readiness no longer exposes the Devpost registration gate")
    open_gate_ids.remove("devpost_registration")
    counts = dict(snapshot["counts"])
    counts["pass"] += 1
    counts["open"] -= 1
    return {
        "counts": counts,
        "open_gate_ids": sorted(open_gate_ids),
        "newly_satisfied_gate_ids": ["devpost_registration"],
        "ready_for_final_submission": False,
        "basis": "verified portal progress receipt",
    }


def field(
    field_id: str,
    step: str,
    portal_label: str | None,
    label_authority: str,
    required: bool,
    value: Any,
    completion_state: str,
    source_refs: list[str],
    human_gate: str | None = None,
    format_rule: str | None = None,
) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "step": step,
        "portal_label": portal_label,
        "portal_label_exact": portal_label is not None,
        "label_authority": label_authority,
        "required": required,
        "proposed_value": value,
        "completion_state": completion_state,
        "source_refs": source_refs,
        "human_gate": human_gate,
        "format_rule": format_rule,
    }


def project_story() -> str:
    return f"""## Inspiration

AI-assisted development can move faster than the evidence behind a claim. ProofLock Console was built to make that boundary visible and testable for developers, reviewers, and automated workflows.

## What it does

ProofLock Console loads a canonical JSON receipt, recomputes its SHA-256 identity, resolves only repository-bounded artifact paths, rehashes the declared files, and evaluates required promotion gates separately from receipt integrity. The bundled example verifies four declared V2/V3 concept artifacts, then correctly keeps the decision at HOLD because engineering, prototype, safety, and human-release gates remain open.

## How we built it

The project pairs a static browser experience using Web Crypto with a matching Python verifier for local automation and CI. Deterministic tests cover receipt tampering, path traversal, artifact custody, duplicate or invalid gates, and attempts to promote while required gates remain open. Codex helped narrow the scope, implement both verification paths, review the evidence boundary, and build the test suite. {MODEL_USAGE_SENTENCE}

## Challenges we ran into

The hardest design problem was keeping integrity and truth distinct. A receipt can be internally intact without proving the underlying engineering claim, so the interface and verifier report `integrity_valid` and `promotion_allowed` as separate decisions and fail closed when evidence is missing.

## Accomplishments that we're proud of

The public demo was observed with all ten required files returning HTTP 200 and matching their local SHA-256 identities. Desktop and mobile checks recorded zero horizontal overflow, and the bundled sample verified all four declared artifacts while preserving the HOLD decision.

## What we learned

Auditability improves when every important assertion names its evidence class, every artifact has a stable identity, and a missing human or technical gate cannot be converted into approval by polished prose.

## What's next for ProofLock Console

Next steps are an independent reproduction run, signed receipt adapters, CI integration, and additional schemas for evidence workflows. These are planned directions, not completed capabilities."""


def project_copy_payload() -> dict[str, Any]:
    return {
        "project_name": "ProofLock Console",
        "tagline": "Hash what exists. Hold what is not proven.",
        "category": "Developer Tools",
        "repository_url": "https://github.com/robertashworth1986-debug/lumen-core-public",
        "exact_source_url": PUBLIC_SCOPED_SOURCE_URL,
        "try_it_out_url": "https://lumen-core.ai/build_week/prooflock_console/",
        "video_demo_url": None,
        "local_video_asset": repo_relative(DEMO_VIDEO_PATH),
        "local_video_sha256": file_sha256(DEMO_VIDEO_PATH),
        "local_video_duration_seconds": 124.634,
        "video_receipt_asset": repo_relative(DEMO_VIDEO_RECEIPT_PATH),
        "video_receipt_sha256": load_json(DEMO_VIDEO_RECEIPT_PATH)["receipt_sha256"],
        "orchestration_receipt_asset": repo_relative(ORCHESTRATION_RECEIPT_PATH),
        "orchestration_receipt_sha256": load_json(ORCHESTRATION_RECEIPT_PATH)["receipt_sha256"],
        "thumbnail_asset": repo_relative(THUMBNAIL_PATH),
        "thumbnail_sha256": file_sha256(THUMBNAIL_PATH),
        "built_with_confirmed": [
            "Codex",
            "gpt-5.6-sol",
            "JavaScript",
            "Web Crypto API",
            "Python",
            "pytest",
            "HTML",
            "CSS",
        ],
        "built_with_blocked_pending_model_provenance": [],
        "project_story_markdown": project_story(),
        "installation_and_testing": (
            "Open the public demo URL for the no-build browser path. For local CLI verification, clone the "
            "repository and run `python build_week/prooflock_console/verify_receipt.py`. Run the focused "
            "test with `python -m pytest -q tests/test_prooflock_console.py`."
        ),
        "supported_platforms": (
            "Current desktop and mobile browsers with Web Crypto and Fetch support, plus Python 3 for the CLI."
        ),
        "testing_access": (
            "The public demo requires no account, API key, paid service, rebuild, or test credentials for the "
            "bundled verification path. Availability is proven only at the recorded observation time."
        ),
        "preexisting_project_boundary": (
            "The larger repository and source concept assets predate the submission period. The focused console, "
            "receipt contract, browser and Python verification paths, responsive interface, and tests are the "
            "scoped Build Week extension identified by the dated commit record."
        ),
        "confirmed_model_label": "gpt-5.6-sol",
        "model_usage_sentence": MODEL_USAGE_SENTENCE,
        "feedback_session_placeholder": "[[FEEDBACK_SESSION_ID]]",
        "video_url_placeholder": "[[PUBLIC_YOUTUBE_URL]]",
        "copy_state": "VIDEO_ASSETS_VERIFIED_FEEDBACK_AND_PUBLICATION_OPEN",
        "source_refs": [
            "readiness_snapshot",
            "requirements_receipt",
            "public_demo_receipt",
            "browser_qa_receipt",
            "description_draft",
            "demo_script",
            "prooflock_readme",
            "sample_receipt",
            "repository_license",
            "orchestration_receipt",
            "demo_video_receipt",
            "demo_video",
            "thumbnail_asset",
        ],
    }


def build_fields(copy: dict[str, Any]) -> list[dict[str, Any]]:
    standard = "DEVPOST_STANDARD_SUBMISSION_STEPS"
    contest = "OPENAI_BUILD_WEEK_RULES_SEMANTIC_REQUIREMENT_PORTAL_LABEL_UNOBSERVED"
    return [
        field(
            "team_members",
            "1_manage_team",
            "Teammates",
            standard,
            False,
            None,
            "OPTIONAL_NOT_SELECTED",
            [],
            "Human confirms whether the entry is individual, team, or organization.",
        ),
        field(
            "project_name",
            "2_project_overview",
            "Project name",
            standard,
            True,
            copy["project_name"],
            "SOURCE_BACKED_READY",
            ["readiness_snapshot", "prooflock_readme"],
        ),
        field(
            "project_tagline",
            "2_project_overview",
            "Project tagline",
            standard,
            True,
            copy["tagline"],
            "SOURCE_BACKED_READY",
            ["readiness_snapshot"],
            format_rule="Maximum 140 characters per Devpost standard field documentation.",
        ),
        field(
            "thumbnail_image",
            "2_project_overview",
            "Thumbnail image for the Project Gallery",
            standard,
            True,
            copy["thumbnail_asset"],
            "SOURCE_BACKED_LOCAL_UPLOAD_READY_PUBLICATION_OPEN",
            ["thumbnail_asset", "demo_video_receipt"],
            "Upload the verified local asset, then inspect the public preview before final submission.",
            "JPG, PNG, or GIF; 5 MB maximum; 3:2 recommended.",
        ),
        field(
            "project_story",
            "3_project_details",
            "Project story",
            standard,
            True,
            copy["project_story_markdown"],
            "SOURCE_BACKED_READY_FINAL_PREVIEW_RECHECK_REQUIRED",
            ["description_draft", "prooflock_readme", "public_demo_receipt", "browser_qa_receipt", "orchestration_receipt"],
            "Recheck Markdown rendering in the final Devpost preview.",
            "Markdown accepted by Devpost.",
        ),
        field(
            "built_with_tags",
            "3_project_details",
            "Built with tags",
            standard,
            True,
            copy["built_with_confirmed"],
            "SOURCE_BACKED_READY_FINAL_PREVIEW_RECHECK_REQUIRED",
            ["prooflock_readme", "readiness_snapshot", "orchestration_receipt"],
            "Recheck that every tag is accepted by the portal widget.",
        ),
        field(
            "try_it_out_link",
            "3_project_details",
            "Try it Out links",
            standard,
            True,
            copy["try_it_out_url"],
            "SOURCE_BACKED_READY_FINAL_PREVIEW_RECHECK_REQUIRED",
            ["public_demo_receipt", "browser_qa_receipt"],
            "Recheck from the final Devpost preview and preserve a new observation receipt.",
        ),
        field(
            "image_gallery",
            "3_project_details",
            "Image Gallery",
            standard,
            False,
            None,
            "OPTIONAL_PRIVACY_REVIEW_OPEN",
            [],
            "Use only public, owned, privacy-reviewed screenshots if selected.",
        ),
        field(
            "video_demo_link",
            "3_project_details",
            "Video demo link",
            standard,
            True,
            None,
            "LOCAL_VIDEO_VERIFIED_PUBLICATION_OPEN",
            ["demo_script", "requirements_receipt", "demo_video_receipt", "demo_video"],
            "The verified MP4 is ready locally; public YouTube upload remains an external publication action.",
            "Public YouTube URL; video shorter than three minutes; audio covers the project and required tools.",
        ),
        field(
            "submitter_type",
            "4_additional_details",
            "Submitter Type",
            standard,
            True,
            None,
            "MISSING_HUMAN_LEGAL_INPUT",
            [],
            "Human chooses Individual, Team, or Organization and confirms authority.",
        ),
        field(
            "country_of_residence",
            "4_additional_details",
            "Countries of Residence",
            standard,
            True,
            None,
            "MISSING_PRIVATE_HUMAN_INPUT",
            [],
            "Enter directly in Devpost; do not persist the private answer in this public kit.",
        ),
        field(
            "category",
            "4_additional_details",
            None,
            contest,
            True,
            copy["category"],
            "SOURCE_BACKED_READY_PORTAL_LABEL_UNOBSERVED",
            ["requirements_receipt", "readiness_snapshot"],
            "Verify the exact custom field label and option spelling after joining.",
        ),
        field(
            "repository_url",
            "4_additional_details",
            None,
            contest,
            True,
            copy["repository_url"],
            "SOURCE_BACKED_READY_EXTERNAL_ACCESS_RECHECK_REQUIRED",
            ["readiness_snapshot", "prooflock_readme", "repository_license"],
            "Verify anonymous repository access from the final preview.",
        ),
        field(
            "repository_license",
            "4_additional_details",
            None,
            contest,
            True,
            "MIT License at repository root",
            "SOURCE_BACKED_READY_HUMAN_REPRESENTATION_REQUIRED",
            ["repository_license", "readiness_snapshot"],
            "Human confirms license scope and any third-party obligations.",
        ),
        field(
            "new_or_existing_project",
            "4_additional_details",
            None,
            contest,
            True,
            "Pre-existing project meaningfully extended during the submission period",
            "SOURCE_BACKED_READY_PORTAL_LABEL_UNOBSERVED",
            ["readiness_snapshot", "description_draft", "prooflock_readme"],
            "Verify the exact custom field label and available choices after joining.",
        ),
        field(
            "hackathon_improvement_explanation",
            "4_additional_details",
            None,
            contest,
            True,
            copy["preexisting_project_boundary"],
            "SOURCE_BACKED_READY_PORTAL_LABEL_UNOBSERVED",
            ["readiness_snapshot", "description_draft", "prooflock_readme"],
        ),
        field(
            "confirmed_model_identity",
            "4_additional_details",
            None,
            contest,
            True,
            copy["confirmed_model_label"],
            "SOURCE_BACKED_READY_PORTAL_LABEL_UNOBSERVED",
            ["orchestration_receipt"],
            "Confirm the exact custom portal label before saving the additional-information step.",
        ),
        field(
            "feedback_session_id",
            "4_additional_details",
            None,
            contest,
            True,
            None,
            "MISSING_FEEDBACK_SESSION_ID",
            [],
            "Human obtains the /feedback Session ID from the task containing most core functionality; never invent it.",
        ),
        field(
            "representative_authorization",
            "4_additional_details",
            None,
            contest,
            True,
            None,
            "MISSING_CONDITIONAL_LEGAL_ATTESTATION",
            [],
            "Required if entering as a team or organization; human confirms the entrant and authority.",
        ),
        field(
            "official_rules_and_terms",
            "5_submit",
            "Agree to the hackathon terms and conditions",
            standard,
            True,
            None,
            "HUMAN_LEGAL_ACCEPTANCE_REQUIRED",
            ["requirements_receipt"],
            "Only the entrant may review and accept the official rules, publicity/IP terms, and Devpost terms.",
        ),
        field(
            "final_submit_action",
            "5_submit",
            "Submit project",
            standard,
            True,
            None,
            "FINAL_HUMAN_ACTION_BLOCKED",
            [],
            "Requires action-time human review and approval after every required field and legal gate is complete.",
        ),
    ]


def checklist_item(
    item_id: str,
    text: str,
    status: str,
    source_refs: list[str],
    human_gate: bool = False,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "text": text,
        "status": status,
        "source_refs": source_refs,
        "human_gate": human_gate,
    }


def build_checklists() -> dict[str, list[dict[str, Any]]]:
    return {
        "public_demo": [
            checklist_item(
                "demo_hashes",
                "All ten required public files returned HTTP 200 and matched local SHA-256 identities at the recorded observation.",
                "PASS_OBSERVED",
                ["public_demo_receipt"],
            ),
            checklist_item(
                "desktop_mobile_qa",
                "Desktop and mobile browser QA records are integrity-valid and recorded no horizontal overflow.",
                "PASS_OBSERVED",
                ["public_demo_receipt", "browser_qa_receipt"],
            ),
            checklist_item(
                "anonymous_access",
                "Load the demo and repository from a signed-out browser without credentials or private identifiers.",
                "OPEN_FINAL_PREVIEW_RECHECK",
                ["public_demo_receipt", "prooflock_readme"],
                True,
            ),
            checklist_item(
                "judging_period_availability",
                "Confirm the free demo will remain available without restriction through the judging period.",
                "OPEN_FUTURE_AVAILABILITY_NOT_PROVABLE",
                ["requirements_receipt"],
                True,
            ),
            checklist_item(
                "behavior_matches_copy",
                "Verify the public behavior matches the submitted story and video, including the HOLD decision.",
                "OPEN_FINAL_PREVIEW_RECHECK",
                ["sample_receipt", "public_demo_receipt"],
                True,
            ),
        ],
        "video": [
            checklist_item(
                "script",
                "Use the bounded demo script and keep the final cut shorter than 180 seconds.",
                "DRAFT_PRESENT_RECORDING_OPEN",
                ["demo_script", "requirements_receipt"],
                True,
            ),
            checklist_item(
                "working_demo",
                "Show the live receipt load, 4/4 artifact verification, HOLD decision, tamper failure, and blocked promotion.",
                "OPEN_RECORDING_REQUIRED",
                ["demo_script", "sample_receipt", "public_demo_receipt"],
                True,
            ),
            checklist_item(
                "required_tool_audio",
                "Audio must accurately explain how Codex and the directly confirmed required model were used.",
                "BLOCKED_MODEL_PROVENANCE_MISSING",
                ["requirements_receipt"],
                True,
            ),
            checklist_item(
                "rights_review",
                "Exclude unlicensed music, third-party trademarks, private screens, credentials, and patent-sensitive material.",
                "OPEN_PRIVACY_IP_REVIEW",
                ["requirements_receipt"],
                True,
            ),
            checklist_item(
                "public_youtube",
                "Upload to YouTube, make it public and embeddable, then verify playback while signed out.",
                "OPEN_PUBLICATION_REQUIRED",
                ["requirements_receipt"],
                True,
            ),
        ],
        "privacy_ip": [
            checklist_item(
                "credentials",
                "No passwords, API keys, OTPs, cookies, private portal identifiers, or meeting credentials appear in any artifact.",
                "HUMAN_REVIEW_REQUIRED",
                [],
                True,
            ),
            checklist_item(
                "personal_data",
                "No private addresses, phone numbers, tax identifiers, signatures, or unrelated personal data are published.",
                "HUMAN_REVIEW_REQUIRED",
                [],
                True,
            ),
            checklist_item(
                "patent_boundary",
                "No unpublished claim language, private patent drafts, CUI/export-controlled material, or grant-portal screenshots are disclosed.",
                "HUMAN_REVIEW_REQUIRED",
                [],
                True,
            ),
            checklist_item(
                "ownership",
                "Entrant confirms original ownership, third-party permissions, and open-source license compliance.",
                "HUMAN_LEGAL_REVIEW_REQUIRED",
                ["repository_license", "requirements_receipt"],
                True,
            ),
            checklist_item(
                "publicity_terms",
                "Entrant reviews the non-exclusive judging license and the publicity use of name, likeness, voice, and image before acceptance.",
                "HUMAN_LEGAL_REVIEW_REQUIRED",
                ["requirements_receipt"],
                True,
            ),
            checklist_item(
                "claim_accuracy",
                "Every performance statement is traceable to the recorded receipt and preserves time-bounded observation language.",
                "HUMAN_REVIEW_REQUIRED",
                ["public_demo_receipt", "readiness_snapshot"],
                True,
            ),
        ],
    }


def build_field_registry(generated_utc: str) -> dict[str, Any]:
    sources = source_registry()
    portal_progress = portal_progress_snapshot()
    copy = project_copy_payload()
    fields = build_fields(copy)
    checklists = build_checklists()
    registry: dict[str, Any] = {
        "schema": "lumencore.openai_build_week_devpost_field_registry.v1",
        "generated_utc": generated_utc,
        "deadline": {
            "central": DEADLINE_CENTRAL,
            "utc": DEADLINE_UTC,
            "timezone_label": "CDT",
        },
        "portal_observation": {
            "observed_utc": portal_progress["recorded_observation_utc"],
            "authentication_state": "SIGNED_IN_AT_OBSERVATION",
            "hackathon_join_state": "REGISTERED_CONFIRMED",
            "project_state": "DRAFT_2_OF_5_CONFIRMED",
            "submission_confirmation_state": "NONE_OBSERVED",
            "observation_basis": (
                "A direct browser observation displayed the ProofLock Console project draft at two of five "
                "steps on the project-details page; independent bounded Gmail metadata confirms registration "
                "and the deadline."
            ),
            "limitations": (
                "Project details, additional information, final preview, and final submission remain incomplete."
            ),
            "progress_receipt": portal_progress,
        },
        "official_sources": OFFICIAL_SOURCES,
        "field_registry_policy": {
            "standard_labels": (
                "Labels marked exact come from Devpost's current standard submission-step documentation."
            ),
            "custom_labels": (
                "Contest-specific semantics come from the official Build Week overview and rules, but their exact "
                "portal labels remain null until the joined form is observed."
            ),
            "no_inference": (
                "Model identity, session IDs, entrant type, residence, representative authority, and legal acceptance "
                "must never be inferred from repository prose or filenames."
            ),
        },
        "source_registry": sources,
        "project_copy": copy,
        "model_and_session_placeholders": PLACEHOLDERS,
        "fields": fields,
        "checklists": checklists,
        "actions_prohibited_for_this_kit": [
            "authenticate",
            "join_or_register",
            "create_or_import_project",
            "upload_file_or_video",
            "publish",
            "accept_terms",
            "certify",
            "submit",
            "contact_anyone",
        ],
        "actions_observed_external_to_this_kit": ["challenge_registration", "project_shell_creation"],
        "claim_boundary": CLAIM_BOUNDARY,
    }
    registry["registry_sha256"] = stable_hash(registry)
    return registry


def render_project_copy(registry: dict[str, Any]) -> str:
    copy = registry["project_copy"]
    built_with = ", ".join(copy["built_with_confirmed"])
    return f"""# ProofLock Console - Source-Backed Devpost Copy

Copy state: `{copy['copy_state']}`

Do not paste or submit this as final copy until every bracketed placeholder is replaced from direct evidence and the privacy/IP checklist is approved.

## Project Name

{copy['project_name']}

## Tagline

{copy['tagline']}

## Category

{copy['category']}

## Built With - Confirmed Components

{built_with}

Required model tag: `{copy['confirmed_model_label']}`

## Project Story

{copy['project_story_markdown']}

## Try It Out

{copy['try_it_out_url']}

## Repository

{copy['repository_url']}

Exact scoped source:

{copy['exact_source_url']}

## Installation And Testing

{copy['installation_and_testing']}

## Supported Platforms

{copy['supported_platforms']}

## Testing Access

{copy['testing_access']}

## Pre-Existing / New Work Boundary

{copy['preexisting_project_boundary']}

## Verified Local Release Assets

- Video: `{copy['local_video_asset']}`
- Video duration: `{copy['local_video_duration_seconds']} seconds`
- Video SHA-256: `{copy['local_video_sha256']}`
- Thumbnail: `{copy['thumbnail_asset']}`
- Thumbnail SHA-256: `{copy['thumbnail_sha256']}`
- Video receipt: `{copy['video_receipt_asset']}`
- Video receipt SHA-256: `{copy['video_receipt_sha256']}`
- Orchestration receipt: `{copy['orchestration_receipt_asset']}`
- Orchestration receipt SHA-256: `{copy['orchestration_receipt_sha256']}`

These paths identify local upload candidates. They do not claim that either asset is public or accepted by Devpost.

## Required External Placeholders

- `/feedback` Session ID: `[[FEEDBACK_SESSION_ID]]`
- Public YouTube URL: `[[PUBLIC_YOUTUBE_URL]]`

## Claim Boundary

{registry['claim_boundary']}
"""


def render_completion_kit(registry: dict[str, Any], snapshot: dict[str, Any]) -> str:
    state = registry["portal_observation"]
    effective = effective_readiness(snapshot, state["progress_receipt"])
    lines = [
        "# OpenAI Build Week - Devpost Completion Kit",
        "",
        f"Deadline: `{registry['deadline']['central']}` (`{registry['deadline']['utc']}`)",
        f"Observed portal state: `{state['authentication_state']}` / `{state['hackathon_join_state']}` / "
        f"`{state['project_state']}` / `{state['submission_confirmation_state']}`",
        f"Base readiness: `{snapshot['counts']['pass']}/{snapshot['counts']['gate_total']}` gates pass. "
        f"Verified portal progress raises effective readiness to "
        f"`{effective['counts']['pass']}/{effective['counts']['gate_total']}`; final submission remains blocked.",
        "",
        "## Field Registry",
        "",
        "| Step | Field | Portal Label | Exact? | Required | State |",
        "|---|---|---|---|---|---|",
    ]
    for row in registry["fields"]:
        label = row["portal_label"] or "unobserved custom label"
        lines.append(
            f"| {row['step']} | `{row['field_id']}` | {label} | "
            f"`{str(row['portal_label_exact']).lower()}` | `{str(row['required']).lower()}` | "
            f"`{row['completion_state']}` |"
        )

    for checklist_name, items in registry["checklists"].items():
        title = "Privacy/IP" if checklist_name == "privacy_ip" else checklist_name.replace("_", " ").title()
        lines.extend(["", f"## {title} Checklist", ""])
        for item in items:
            lines.append(f"- `{item['status']}` - {item['text']}")

    lines.extend(
        [
            "",
            "## Hard Stop Conditions",
            "",
            "- Challenge registration and a two-of-five project draft are confirmed; no final submission confirmation exists.",
            "- Project details and additional information remain incomplete.",
            "- The `/feedback` Session ID is not present.",
            "- A verified local under-three-minute demo exists, but no public YouTube URL is recorded.",
            "- Entrant type, residence, representative authority, rules, publicity/IP terms, and final certification require human review.",
            "- Contest-specific portal labels must be captured from the joined form before field population is called exact.",
            "",
            "## Actions Not Authorized By This Kit",
            "",
        ]
    )
    lines.extend(f"- `{action}`" for action in registry["actions_prohibited_for_this_kit"])
    lines.extend(["", "## Claim Boundary", "", registry["claim_boundary"], ""])
    return "\n".join(lines)


def output_artifact(path: Path) -> dict[str, Any]:
    return {
        "path": repo_relative(path),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def build_readiness_receipt(
    generated_utc: str,
    registry: dict[str, Any],
    snapshot: dict[str, Any],
    output_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    fields = registry["fields"]
    portal_progress = registry["portal_observation"]["progress_receipt"]
    effective = effective_readiness(snapshot, portal_progress)
    exact_label_count = sum(1 for row in fields if row["portal_label_exact"])
    source_ready_count = sum(1 for row in fields if row["completion_state"].startswith("SOURCE_BACKED_READY"))
    receipt: dict[str, Any] = {
        "schema": "lumencore.openai_build_week_devpost_readiness_receipt.v1",
        "generated_utc": generated_utc,
        "status": "NOT_READY_FOR_SUBMISSION",
        "deadline": registry["deadline"],
        "portal_observation": registry["portal_observation"],
        "existing_readiness_snapshot": snapshot,
        "effective_readiness_after_portal_progress": effective,
        "field_counts": {
            "total": len(fields),
            "required": sum(1 for row in fields if row["required"]),
            "exact_standard_labels": exact_label_count,
            "custom_labels_unobserved": len(fields) - exact_label_count,
            "source_backed_ready_or_conditionally_ready": source_ready_count,
        },
        "model_and_session_provenance": {
            "confirmed_model_label": "gpt-5.6-sol",
            "model_usage_evidence": repo_relative(ORCHESTRATION_RECEIPT_PATH),
            "feedback_session_id": None,
            "state": "MODEL_RECORDED_FEEDBACK_SESSION_OPEN",
            "inference_prohibited": True,
        },
        "submission_artifacts": output_artifacts,
        "hard_blockers": [
            "NO_SUBMISSION_CONFIRMATION",
            "PROJECT_DETAILS_INCOMPLETE",
            "ADDITIONAL_INFO_INCOMPLETE",
            "FEEDBACK_SESSION_ID_MISSING",
            "PUBLIC_YOUTUBE_VIDEO_MISSING",
            "FINAL_PREVIEW_REVIEW_OPEN",
            "CUSTOM_PORTAL_LABELS_UNOBSERVED",
            "PRIVACY_IP_REVIEW_OPEN",
            "LEGAL_ACCEPTANCE_OPEN",
            "FINAL_HUMAN_SUBMIT_ACTION_OPEN",
        ],
        "ready_for_portal_population": False,
        "ready_for_final_submission": False,
        "actions_performed": [],
        "actions_observed_external_to_this_builder": ["challenge_registration", "project_shell_creation"],
        "actions_not_performed": registry["actions_prohibited_for_this_kit"],
        "claim_boundary": CLAIM_BOUNDARY,
    }
    receipt["receipt_sha256"] = stable_hash(receipt)
    return receipt


def write_outputs(generated_utc: str | None = None) -> dict[str, Path]:
    generated_utc = generated_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    registry = build_field_registry(generated_utc)
    snapshot = readiness_snapshot()

    FIELD_REGISTRY_PATH.write_text(
        json.dumps(registry, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    PROJECT_COPY_PATH.write_text(render_project_copy(registry), encoding="utf-8")
    COMPLETION_KIT_PATH.write_text(render_completion_kit(registry, snapshot), encoding="utf-8")

    output_artifacts = [
        output_artifact(FIELD_REGISTRY_PATH),
        output_artifact(PROJECT_COPY_PATH),
        output_artifact(COMPLETION_KIT_PATH),
    ]
    receipt = build_readiness_receipt(generated_utc, registry, snapshot, output_artifacts)
    READINESS_RECEIPT_PATH.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return {
        "field_registry": FIELD_REGISTRY_PATH,
        "project_copy": PROJECT_COPY_PATH,
        "completion_kit": COMPLETION_KIT_PATH,
        "readiness_receipt": READINESS_RECEIPT_PATH,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the bounded OpenAI Build Week Devpost completion kit.")
    parser.add_argument(
        "--generated-utc",
        default=None,
        help="Optional ISO-8601 UTC generation time for deterministic reproduction.",
    )
    args = parser.parse_args()
    paths = write_outputs(args.generated_utc)
    print(json.dumps({name: repo_relative(path) for name, path in paths.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
