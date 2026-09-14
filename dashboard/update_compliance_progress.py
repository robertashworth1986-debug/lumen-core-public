"""Inventory legacy implementation artifacts without certifying completion."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROGRESS_PATH = ROOT / 'dashboard/compliance_mvp_progress.json'
EVIDENCE_BOUNDARY = (
    "File inventory only. Functionality, legal sufficiency, compliance, "
    "credential validity and account access are not verified."
)

# Define the compliance/MVP items and automation logic
PROGRESS_ITEMS = [
    {"item": "User onboarding flow", "notes": "UI, registration, and account creation"},
    {"item": "KYC/AML integration", "notes": "ID verification, compliance checks"},
    {"item": "Funding/deposit system", "notes": "Bank, crypto, and fiat onramp"},
    {"item": "Withdrawal/settlement system", "notes": "User-initiated withdrawals, compliance review"},
    {"item": "Live dashboard for users", "notes": "Personalized analytics, notifications"},
    {"item": "Notifications/alerts", "notes": "Email, SMS, in-app"},
    {"item": "Audit trail & reporting", "notes": "Exportable logs, compliance evidence"},
    {"item": "API key management UI", "notes": "User and admin key management"},
    {"item": "Legal/terms of service", "notes": "User agreements, disclosures"}
]

# These are inventory locators, never acceptance or compliance rules.
AUTOMATION_RULES = {
    "User onboarding flow": ["dashboard/user_onboarding.html", "dashboard/user_onboarding.json"],
    "KYC/AML integration": ["dashboard/kyc_status.json", "dashboard/kyc_module.py"],
    "Funding/deposit system": ["dashboard/funding_status.json", "dashboard/funding_module.py"],
    "Withdrawal/settlement system": ["dashboard/withdrawal_status.json", "dashboard/withdrawal_module.py"],
    "Live dashboard for users": ["dashboard/live_user_dashboard.html"],
    "Notifications/alerts": ["dashboard/notifications.json", "dashboard/notifications_module.py"],
    "Audit trail & reporting": ["dashboard/audit_log.json", "dashboard/audit_module.py"],
    "API key management UI": ["dashboard/api_key_status.txt"],
    "Legal/terms of service": ["dashboard/legal.html", "dashboard/terms_of_service.html"]
}

def check_complete(item):
    """Compatibility helper: this inventory has no completion authority."""
    return False


def inspect_item(item, root=None):
    root = Path(root or ROOT).resolve()
    artifacts = []
    for relative in AUTOMATION_RULES.get(item, []):
        path = root / relative
        observation = {"path": relative, "state": "not_found"}
        try:
            if not path.resolve().is_relative_to(root):
                observation["state"] = "outside_root_not_inspected"
            elif path.is_symlink():
                observation["state"] = "symlink_not_inspected"
            else:
                metadata = path.stat()
                if not stat.S_ISREG(metadata.st_mode):
                    observation["state"] = "not_a_regular_file"
                else:
                    observation.update({
                        "state": "nonempty_file_observed" if metadata.st_size else "empty_file_observed",
                        "bytes": metadata.st_size,
                        "modified_utc": datetime.fromtimestamp(metadata.st_mtime, timezone.utc).isoformat(),
                    })
        except FileNotFoundError:
            pass
        except OSError:
            observation["state"] = "metadata_unavailable"
        artifacts.append(observation)
    return artifacts


def build_progress(root=None, checked_utc=None):
    checked = checked_utc or datetime.now(timezone.utc)
    if not isinstance(checked, datetime) or checked.tzinfo is None:
        raise ValueError("Inventory timestamp must be timezone-aware")
    progress = []
    for entry in PROGRESS_ITEMS:
        artifacts = inspect_item(entry["item"], root)
        observed = any(item["state"] == "nonempty_file_observed" for item in artifacts)
        progress.append({
            **entry, "status": "artifact_present_unverified" if observed else "no_usable_artifact_observed",
            "schema": "lumencore.implementation_inventory.v2", "evidence_scope": "file_metadata_only",
            "checked_utc": checked.astimezone(timezone.utc).isoformat(),
            "completion_verified": False, "compliance_verified": False,
            "boundary": EVIDENCE_BOUNDARY, "artifacts": artifacts,
        })
    return progress


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = args.output or (PROGRESS_PATH if args.root == ROOT else args.root / "dashboard/compliance_mvp_progress.json")
    progress = build_progress(args.root)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(progress, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print("Implementation inventory updated. Completion and compliance remain unverified.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
