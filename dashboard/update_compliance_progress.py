import json
from pathlib import Path

PROGRESS_PATH = Path('dashboard/compliance_mvp_progress.json')

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

# Example automation: mark as complete if a related file or config exists
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
    for path in AUTOMATION_RULES.get(item, []):
        if Path(path).exists():
            return True
    return False

def main():
    progress = []
    for entry in PROGRESS_ITEMS:
        status = "complete" if check_complete(entry["item"]) else "incomplete"
        progress.append({"item": entry["item"], "status": status, "notes": entry["notes"]})
    with open(PROGRESS_PATH, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)
    print("Compliance/MVP progress updated.")

if __name__ == "__main__":
    main()
