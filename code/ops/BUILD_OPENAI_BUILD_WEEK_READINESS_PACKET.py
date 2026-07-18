from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "build_week" / "prooflock_console"
OUT_DIR = ROOT / "grant_submissions" / "OPENAI_BUILD_WEEK_20260721"
OUT_JSON = OUT_DIR / "OPENAI_BUILD_WEEK_SUBMISSION_READINESS_2026-07-17.json"
OUT_MD = OUT_DIR / "OPENAI_BUILD_WEEK_SUBMISSION_READINESS_2026-07-17.md"
OUT_DESCRIPTION = OUT_DIR / "OPENAI_BUILD_WEEK_PROJECT_DESCRIPTION_DRAFT_2026-07-17.md"
OUT_DEMO = OUT_DIR / "OPENAI_BUILD_WEEK_DEMO_SCRIPT_2026-07-17.md"
OUT_REQUIREMENTS = OUT_DIR / "OPENAI_BUILD_WEEK_REQUIREMENTS_RECEIPT_2026-07-17.json"
PUBLIC_DEMO_RECEIPT = OUT_DIR / "OPENAI_BUILD_WEEK_PUBLIC_DEMO_RECEIPT_2026-07-18.json"

SUBMISSION_START_UTC = "2026-07-13T16:00:00Z"
DEADLINE_UTC = "2026-07-22T00:00:00Z"
OFFICIAL_SOURCES = {
    "overview": "https://openai.devpost.com/",
    "rules": "https://openai.devpost.com/rules",
    "submission_manager": "https://devpost.com/submit-to/30223-openai-build-week/manage/submissions",
}
APP_FILES = (
    "README.md",
    "app.js",
    "index.html",
    "sample_receipt.json",
    "styles.css",
    "verify_receipt.py",
)
CLAIM_BOUNDARY = (
    "This packet records a bounded Build Week readiness audit for the public ProofLock Console. "
    "It does not prove Devpost registration, GPT-5.6 model identity, a valid /feedback session ID, "
    "continuous public-demo availability, a YouTube upload, eligibility acceptance, final submission, "
    "judging outcome, OpenAI endorsement, prize entitlement, external validation, patent rights, "
    "safety, engineering performance, funding, or commercial value."
)


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def app_commit() -> dict[str, Any]:
    line = run_git(
        "log",
        "-1",
        "--format=%H%x09%cI%x09%s",
        "--",
        APP_DIR.relative_to(ROOT).as_posix(),
    )
    parts = line.split("\t", 2) if line else []
    if len(parts) != 3:
        return {"commit": "", "committed_at": "", "subject": "", "after_submission_start": False}
    commit, committed_at, subject = parts
    committed_utc = datetime.fromisoformat(committed_at).astimezone(timezone.utc)
    start_utc = datetime.fromisoformat(SUBMISSION_START_UTC.replace("Z", "+00:00"))
    return {
        "commit": commit,
        "committed_at": committed_at,
        "subject": subject,
        "after_submission_start": committed_utc >= start_utc,
        "github_tree_url": (
            "https://github.com/robertashworth1986-debug/lumen-core-public/tree/"
            f"{commit}/build_week/prooflock_console"
        ),
    }


def app_artifacts() -> list[dict[str, Any]]:
    rows = []
    for name in APP_FILES:
        path = APP_DIR / name
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "present": path.is_file(),
                "bytes": path.stat().st_size if path.is_file() else 0,
                "sha256": file_sha256(path) if path.is_file() else "",
            }
        )
    return rows


def verify_sample() -> dict[str, Any]:
    script = APP_DIR / "verify_receipt.py"
    spec = importlib.util.spec_from_file_location("prooflock_console_packet_verifier", script)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("ProofLock verifier module has no loader")
    spec.loader.exec_module(module)
    receipt = json.loads((APP_DIR / "sample_receipt.json").read_text(encoding="utf-8"))
    report = module.verify_receipt(receipt, ROOT)
    return {
        "integrity_valid": report["integrity_valid"],
        "promotion_allowed": report["promotion_allowed"],
        "recorded_decision": report["recorded_decision"],
        "artifact_count": report["artifact_count"],
        "artifact_hash_match_count": report["artifact_hash_match_count"],
        "required_open_or_failed_gates": report["required_open_or_failed_gates"],
        "receipt_sha256": report["receipt_hash"]["computed"],
    }


def public_demo_state() -> dict[str, Any]:
    default = {
        "verified": False,
        "status": "PUBLIC_DEMO_RECEIPT_MISSING",
        "demo_url": "",
        "required_file_count": 0,
        "hash_match_count": 0,
        "receipt_sha256": "",
        "receipt_path": PUBLIC_DEMO_RECEIPT.relative_to(ROOT).as_posix(),
    }
    if not PUBLIC_DEMO_RECEIPT.is_file():
        return default
    try:
        payload = json.loads(PUBLIC_DEMO_RECEIPT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {**default, "status": "PUBLIC_DEMO_RECEIPT_UNREADABLE"}

    unhashed = dict(payload)
    recorded_hash = unhashed.pop("receipt_sha256", "")
    receipt_hash_valid = bool(recorded_hash) and recorded_hash == stable_hash(unhashed)
    expected_url = "https://lumen-core.ai/build_week/prooflock_console/"
    verified = all(
        (
            payload.get("schema") == "lumencore.openai_build_week_public_demo_receipt.v1",
            payload.get("status") == "PUBLIC_DEMO_HASH_VERIFIED",
            payload.get("public_demo_verified") is True,
            payload.get("demo_url") == expected_url,
            payload.get("all_http_200") is True,
            payload.get("all_hashes_match") is True,
            payload.get("required_file_count") == 10,
            payload.get("http_200_count") == 10,
            payload.get("hash_match_count") == 10,
            payload.get("browser_qa_verified") is True,
            receipt_hash_valid,
        )
    )
    return {
        "verified": verified,
        "status": payload.get("status", "PUBLIC_DEMO_RECEIPT_INVALID"),
        "demo_url": payload.get("demo_url", ""),
        "required_file_count": payload.get("required_file_count", 0),
        "hash_match_count": payload.get("hash_match_count", 0),
        "receipt_sha256": recorded_hash,
        "receipt_hash_valid": receipt_hash_valid,
        "receipt_path": PUBLIC_DEMO_RECEIPT.relative_to(ROOT).as_posix(),
        "observed_utc": payload.get("generated_utc", ""),
    }


def requirements_receipt() -> dict[str, Any]:
    facts: dict[str, Any] = {
        "submission_period": {
            "start_utc": SUBMISSION_START_UTC,
            "deadline_pacific": "2026-07-21T17:00:00-07:00",
            "deadline_central": "2026-07-21T19:00:00-05:00",
            "deadline_utc": DEADLINE_UTC,
        },
        "category": "Developer Tools",
        "required_project": "A working project built with Codex and GPT-5.6.",
        "required_submission_materials": [
            "category",
            "project description",
            "public YouTube demonstration shorter than three minutes with audio",
            "code repository URL with relevant licensing and setup instructions",
            "working demo or test access available free through judging",
            "README explaining Codex collaboration and key decisions",
            "/feedback Codex Session ID for the thread containing most core functionality",
        ],
        "existing_project_rule": (
            "Pre-existing projects must be meaningfully extended after the submission period begins, "
            "and the entrant must distinguish prior work from new work with dated evidence."
        ),
        "judging": {
            "stage_one": "Pass/fail theme fit and use of the required tools.",
            "stage_two_equal_weight_criteria": [
                "Technological Implementation",
                "Design",
                "Potential Impact",
                "Quality of the Idea",
            ],
        },
        "project_testing_rule": (
            "Judges must receive free access to a working website, demo, test build, sandbox, or test account."
        ),
        "plugin_required": False,
        "free_credit_request_deadline_pacific": "2026-07-17T12:00:00-07:00",
    }
    receipt: dict[str, Any] = {
        "schema": "lumencore.openai_build_week_requirements_receipt.v1",
        "captured_date": "2026-07-17",
        "capture_method": "VISIBLE_OFFICIAL_PAGE_REVIEW_NORMALIZED_FACT_RECORD",
        "raw_html_archived": False,
        "official_sources": OFFICIAL_SOURCES,
        "facts": facts,
        "facts_sha256": stable_hash(facts),
        "claim_boundary": (
            "This is a normalized fact record from the visible official overview and rules pages, "
            "not a raw-page archive or legal interpretation. The official rules and current Devpost "
            "submission interface remain authoritative."
        ),
    }
    receipt["receipt_sha256"] = stable_hash(receipt)
    return receipt


def gate(gate_id: str, label: str, status: str, owner: str, basis: str) -> dict[str, str]:
    return {"gate_id": gate_id, "label": label, "status": status, "owner": owner, "basis": basis}


def build_payload() -> dict[str, Any]:
    artifacts = app_artifacts()
    commit = app_commit()
    sample = verify_sample()
    public_demo = public_demo_state()
    remote = run_git("remote", "get-url", "origin")
    license_path = ROOT / "LICENSE"

    gates = [
        gate(
            "working_project",
            "Working project",
            "PASS" if all(row["present"] for row in artifacts) and sample["integrity_valid"] else "FAIL",
            "Codex",
            "The static console, browser verifier, Python verifier, sample receipt, and README are present; the bundled sample verifies 4/4 declared artifacts.",
        ),
        gate(
            "post_start_new_work",
            "Post-start new work",
            "PASS" if commit.get("after_submission_start") else "OPEN",
            "Git",
            f"First scoped evidence commit: {commit.get('commit') or 'not committed'} at {commit.get('committed_at') or 'unknown'}.",
        ),
        gate(
            "public_repository",
            "Public repository",
            "PASS" if remote == "https://github.com/robertashworth1986-debug/lumen-core-public.git" else "OPEN",
            "GitHub",
            remote or "Repository remote not detected.",
        ),
        gate(
            "relevant_license",
            "Relevant license",
            "PASS" if license_path.is_file() and "MIT License" in license_path.read_text(encoding="utf-8") else "OPEN",
            "Repository",
            "The root MIT license is present and applies to the public repository unless a path states otherwise.",
        ),
        gate(
            "model_provenance",
            "GPT-5.6 provenance",
            "OPEN",
            "Robert",
            "Confirm the model label from the project-building Codex session; do not infer it from prose or local filenames.",
        ),
        gate(
            "feedback_session",
            "/feedback session ID",
            "OPEN",
            "Robert",
            "Generate and paste the Codex /feedback Session ID for the task containing most of the console implementation.",
        ),
        gate(
            "public_demo",
            "Public working demo",
            "PASS" if public_demo["verified"] else "OPEN",
            "Codex",
            (
                f"{public_demo['demo_url']} returned the exact {public_demo['hash_match_count']}/"
                f"{public_demo['required_file_count']} recorded file hashes at "
                f"{public_demo.get('observed_utc') or 'an unverified observation time'}."
                if public_demo["verified"]
                else "Deploy the self-contained console to a stable public URL and verify all four artifact fetches from that URL."
            ),
        ),
        gate(
            "youtube_demo",
            "Public demo video",
            "OPEN",
            "Robert",
            "Record the bounded script with voice, keep it under three minutes, upload it publicly to YouTube, and review privacy before publishing.",
        ),
        gate(
            "devpost_registration",
            "Devpost registration",
            "OPEN",
            "Robert",
            "Log in or create the Devpost account, review the rules, and join the hackathon.",
        ),
        gate(
            "final_submission",
            "Final submission",
            "OPEN",
            "Robert",
            "Review every populated field, publicity/IP terms, repository visibility, demo video, and final certification before the final submit action.",
        ),
    ]

    core_gate_ids = {"working_project", "post_start_new_work", "public_repository", "relevant_license"}
    core_ready = all(row["status"] == "PASS" for row in gates if row["gate_id"] in core_gate_ids)
    final_ready = all(row["status"] == "PASS" for row in gates)
    payload: dict[str, Any] = {
        "schema": "lumencore.openai_build_week_submission_readiness.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PROJECT_CORE_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN" if core_ready else "PROJECT_CORE_INCOMPLETE",
        "project": {
            "name": "ProofLock Console",
            "tagline": "Hash what exists. Hold what is not proven.",
            "category": "Developer Tools",
            "public_repo": "https://github.com/robertashworth1986-debug/lumen-core-public",
            "scoped_tree": commit.get("github_tree_url", ""),
            "app_path": APP_DIR.relative_to(ROOT).as_posix(),
            "local_demo_url": "http://127.0.0.1:8088/build_week/prooflock_console/",
            "public_demo_url": public_demo["demo_url"] if public_demo["verified"] else None,
            "youtube_demo_url": None,
            "feedback_session_id": None,
            "confirmed_model": None,
        },
        "official_requirements": requirements_receipt(),
        "new_work_evidence": commit,
        "app_artifacts": artifacts,
        "sample_verification": sample,
        "public_demo_verification": public_demo,
        "gates": gates,
        "counts": {
            "gate_total": len(gates),
            "pass": sum(1 for row in gates if row["status"] == "PASS"),
            "open": sum(1 for row in gates if row["status"] == "OPEN"),
            "fail": sum(1 for row in gates if row["status"] == "FAIL"),
        },
        "core_ready": core_ready,
        "ready_for_final_submission": final_ready,
        "next_actions": [
            "Confirm GPT-5.6 model provenance and obtain the /feedback Session ID.",
            "Recheck the public demo from the final Devpost preview and preserve the observed URL.",
            "Record and publish the under-three-minute YouTube demo after privacy review.",
            "Join the Devpost challenge, populate the draft, and obtain action-time approval before final submission.",
        ],
        "claim_boundary": CLAIM_BOUNDARY,
        "outputs": {
            "json": OUT_JSON.relative_to(ROOT).as_posix(),
            "markdown": OUT_MD.relative_to(ROOT).as_posix(),
            "description_draft": OUT_DESCRIPTION.relative_to(ROOT).as_posix(),
            "demo_script": OUT_DEMO.relative_to(ROOT).as_posix(),
            "requirements_receipt": OUT_REQUIREMENTS.relative_to(ROOT).as_posix(),
            "public_demo_receipt": PUBLIC_DEMO_RECEIPT.relative_to(ROOT).as_posix(),
        },
    }
    payload["packet_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    project = payload["project"]
    counts = payload["counts"]
    lines = [
        "# OpenAI Build Week Submission Readiness - 2026-07-17",
        "",
        f"Status: `{payload['status']}`",
        f"Packet SHA-256: `{payload['packet_sha256']}`",
        "",
        "## Project",
        "",
        f"- Name: {project['name']}",
        f"- Tagline: {project['tagline']}",
        f"- Category: {project['category']}",
        f"- Repository: {project['public_repo']}",
        f"- Scoped tree: {project['scoped_tree']}",
        f"- Local demo: {project['local_demo_url']}",
        f"- Public demo: {project['public_demo_url'] or 'not verified'}",
        f"- Core ready: `{str(payload['core_ready']).lower()}`",
        f"- Final-submission ready: `{str(payload['ready_for_final_submission']).lower()}`",
        f"- Gates: `{counts['pass']}` pass / `{counts['open']}` open / `{counts['fail']}` fail",
        "",
        "## Gates",
        "",
        "| Gate | Status | Owner | Basis |",
        "|---|---|---|---|",
    ]
    for row in payload["gates"]:
        lines.append(f"| {row['label']} | `{row['status']}` | {row['owner']} | {row['basis']} |")
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"{index}. {item}" for index, item in enumerate(payload["next_actions"], start=1))
    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"], ""])
    return "\n".join(lines)


def render_description(payload: dict[str, Any]) -> str:
    project = payload["project"]
    return f"""# {project['name']} - Devpost Description Draft

## Tagline

{project['tagline']}

## Project Description

AI-assisted software can move faster than its evidence. ProofLock Console is a small developer tool that keeps those two things synchronized. It accepts a canonical JSON receipt, recomputes its SHA-256 identity, fetches and rehashes declared public repository artifacts, and evaluates required promotion gates separately from receipt integrity.

The bundled demonstration uses a real public artifact lineage created during the challenge window: the FLOWFORM V2 and V3 curved-motherboard and honeycomb-battery concept renders and their manifests. The console verifies all four artifact hashes and the declared lineage, then deliberately holds promotion because engineering CAD, prototype testing, qualified safety review, and human release remain open. A valid receipt is therefore not mistaken for a validated product claim.

The browser implementation uses Web Crypto and blocks arbitrary or escaping artifact paths. A matching Python CLI provides the same fail-closed review path for automation and CI. Deterministic tests cover receipt tampering, path traversal, artifact custody, and attempts to promote while required gates remain open. The interface is responsive and requires no account, API key, build step, or paid service for the bundled test.

## Build Week New Work

The focused console, receipt contract, CLI verifier, responsive interface, and tests were added after the submission period opened. The larger LumenCore repository and source concept assets are pre-existing dependencies. The scoped commit and directory make that boundary inspectable.

## Codex Collaboration

Codex reviewed the official rules, narrowed the product to one judge-testable workflow, implemented the browser and Python verification paths, wrote the tests, ran desktop and mobile QA, and preserved explicit human/final-submission gates. Before submission, add the verified GPT-5.6 model label and the `/feedback` Session ID from the task containing most of the implementation; do not infer either value.

## Testing

Repository: {project['public_repo']}

Scoped source: {project['scoped_tree']}

Public demo: {project['public_demo_url'] or 'not yet verified'}

Run `python -m http.server 8088` from the repository root and open `/build_week/prooflock_console/`, or run `python build_week/prooflock_console/verify_receipt.py` for the CLI verification report.

## Boundary

{payload['claim_boundary']}
"""


def render_demo_script(payload: dict[str, Any]) -> str:
    return f"""# ProofLock Console Demo Script - Target 2:40

## 0:00-0:20 - Problem

"AI can produce software and artifacts quickly. ProofLock Console makes the evidence boundary visible: it hashes what exists and holds what has not been proven."

Show the project title, category, and verified sample state.

## 0:20-0:55 - Working Verification

Select **Load sample**, then **Verify receipt**. Show `4 / 4` artifact matches, the canonical receipt SHA-256, and the `HOLD` decision.

Say: "The console rehashes four real repository artifacts in the browser. Receipt integrity and promotion authority are separate decisions."

## 0:55-1:25 - Honest Claim Gate

Show the FLOWFORM V3 image, claim boundary, and authority gates.

Say: "Custody and V2-to-V3 lineage pass. CAD, prototype testing, qualified safety review, and human release remain open, so the concept cannot be promoted as engineering evidence."

## 1:25-1:55 - Tamper Detection

Add one character to `claim_boundary`, then select **Verify receipt**.

Say: "Any receipt mutation changes the canonical hash and fails verification."

Reload the sample.

## 1:55-2:20 - Fail-Closed Promotion

Change `decision` from `HOLD` to `PROMOTE` without closing the required gates. Verify again.

Say: "The verifier blocks promotion while required gates are open. The matching Python CLI applies the same control in automation and CI."

Reload the sample.

## 2:20-2:40 - Codex And Close

Say: "Codex helped scope, implement, test, and visually verify this post-start extension. The README records the new-work boundary, setup steps, key decisions, and the verified GPT-5.6 and `/feedback` session facts included with the final entry."

End on the repository URL and working public demo URL.

## Recording Gates

- Public YouTube video, under three minutes, with voice audio.
- No copyrighted music, private tabs, credentials, personal notifications, or patent-sensitive documents on screen.
- Show the exact final commit, public demo URL, and `/feedback` Session ID only after verifying them.
- Do not state that the concept is CAD, a prototype, tested, certified, patented, externally validated, or commercially ready.

Claim boundary: {payload['claim_boundary']}
"""


def write_outputs(payload: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    OUT_DESCRIPTION.write_text(render_description(payload), encoding="utf-8")
    OUT_DEMO.write_text(render_demo_script(payload), encoding="utf-8")
    OUT_REQUIREMENTS.write_text(
        json.dumps(payload["official_requirements"], indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(json.dumps({
        "status": payload["status"],
        "core_ready": payload["core_ready"],
        "ready_for_final_submission": payload["ready_for_final_submission"],
        "counts": payload["counts"],
        "commit": payload["new_work_evidence"]["commit"],
        "packet_sha256": payload["packet_sha256"],
    }, indent=2))
    return 0 if payload["core_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
