import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

# Config
ALERT_EMAIL = "your_alert_email@example.com"
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASS = "your_smtp_password"

# Files to check for issues
ROOT = Path(__file__).resolve().parents[1]
WATCHDOG_STATUS = ROOT / 'dashboard/orchestrator_watchdog_status.txt'
API_KEY_STATUS = ROOT / 'dashboard/api_key_status.txt'
COMPLIANCE_STATUS = ROOT / 'dashboard/compliance_mvp_progress.json'

# Compose alert if any issues detected
def check_watchdog():
    try:
        with WATCHDOG_STATUS.open('rb') as stream:
            content = stream.read(65537)
        if len(content) > 65536:
            return "Watchdog observation is oversized; runtime health remains unverified."
        lines = content.decode('utf-8').splitlines()
        checked_lines = [line.removeprefix('Checked: ') for line in lines if line.startswith('Checked: ')]
        if not lines or lines[0] != '# Orchestrator Log Observation' or len(checked_lines) != 1:
            return "Watchdog observation is legacy or malformed; runtime health remains unverified."
        checked = datetime.fromisoformat(checked_lines[0])
        if checked.tzinfo is None:
            return "Watchdog observation lacks an explicit timezone; runtime health remains unverified."
        age = (datetime.now(timezone.utc) - checked).total_seconds()
        if not -2 <= age <= 600:
            return "Watchdog observation is stale or future-dated; runtime health remains unverified."
        if 'Runtime health: UNVERIFIED; restart authorization: FALSE' not in lines:
            return "Watchdog observation contains unsupported authority; runtime health remains unverified."
    except (OSError, UnicodeError, ValueError):
        return "Watchdog observation is unavailable; runtime health remains unverified."
    if 'ISSUES DETECTED:' in lines:
        return "Watchdog reports log issues. Inspect the local observation; runtime health and restart authority remain unverified."
    return None

def check_api_keys():
    if not API_KEY_STATUS.exists():
        return "API key status file missing."
    txt = API_KEY_STATUS.read_text()
    if "missing" in txt:
        return txt
    return None

def check_compliance():
    """Read inventory availability; a legacy 'complete' label is not approval."""
    import json
    try:
        with COMPLIANCE_STATUS.open('rb') as stream:
            content = stream.read(65537)
        if len(content) > 65536:
            return "Implementation inventory is too large to inspect; compliance remains unverified."
        data = json.loads(content.decode('utf-8'))
        if not isinstance(data, list) or not data or len(data) > 100 or any(not isinstance(row, dict) for row in data):
            return "Implementation inventory is empty or invalid; compliance remains unverified."
    except (OSError, UnicodeError, ValueError):
        return "Implementation inventory is unavailable; compliance remains unverified."
    # Never echo arbitrary file content into an outbound alert or treat a
    # file-presence status as functional, legal, or compliance acceptance.
    return f"Implementation inventory contains {len(data)} items. Completion and compliance remain unverified; file presence is not acceptance evidence."

def send_alert(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = ALERT_EMAIL
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [ALERT_EMAIL], msg.as_string())

def main():
    alerts = []
    for check, label in [
        (check_watchdog, "Orchestrator Watchdog"),
        (check_api_keys, "API Key Status"),
        (check_compliance, "Compliance Progress")]:
        result = check()
        if result:
            alerts.append(f"[{label}]\n{result}")
    if alerts:
        send_alert("LumaTrader Stack Alert", "\n\n".join(alerts))
        print("Alert sent.")
    else:
        print("No issues detected.")

if __name__ == "__main__":
    main()
