import smtplib
from email.mime.text import MIMEText
from pathlib import Path

# Config
ALERT_EMAIL = "your_alert_email@example.com"
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASS = "your_smtp_password"

# Files to check for issues
WATCHDOG_STATUS = Path('dashboard/orchestrator_watchdog_status.txt')
API_KEY_STATUS = Path('dashboard/api_key_status.txt')
COMPLIANCE_STATUS = Path('dashboard/compliance_mvp_progress.json')

# Compose alert if any issues detected
def check_watchdog():
    if not WATCHDOG_STATUS.exists():
        return "Watchdog status file missing."
    txt = WATCHDOG_STATUS.read_text()
    if "ISSUES DETECTED" in txt:
        return txt
    return None

def check_api_keys():
    if not API_KEY_STATUS.exists():
        return "API key status file missing."
    txt = API_KEY_STATUS.read_text()
    if "missing" in txt:
        return txt
    return None

def check_compliance():
    if not COMPLIANCE_STATUS.exists():
        return "Compliance status file missing."
    import json
    data = json.loads(COMPLIANCE_STATUS.read_text())
    issues = [x for x in data if x['status'] != 'complete']
    if issues:
        return f"Compliance items incomplete: {[x['item'] for x in issues]}"
    return None

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
