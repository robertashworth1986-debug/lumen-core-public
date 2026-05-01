import os, json
from pathlib import Path
from datetime import datetime, timezone
import subprocess

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONF = ROOT / "config"
OUT  = ROOT / "out"
ENV_PATH = CONF / "luma_live_keys.env"
SMOKE = ROOT / "code" / "kraken_smoke_test_stage2.py"
PROOF = OUT / "runtime_env_hydration_proof.json"

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def parse_env(path):
    env = {}
    p = Path(path)
    if not p.exists():
        return env
    for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env_file = parse_env(ENV_PATH)

needed = [
    "KRAKEN_API_KEY",
    "KRAKEN_API_SECRET",
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET",
    "FINNHUB_API_KEY",
    "FRED_API_KEY",
    "EIA_API_KEY",
    "BLS_API_KEY",
    "BEA_API_KEY",
    "CENSUS_API_KEY",
    "NASA_API_KEY",
    "NOAA_API_TOKEN",
    "NREL_API_KEY",
    "EPA_AQS_KEY",
    "EPA_AQS_EMAIL",
    "TWELVE_DATA_API_KEY",
    "MASSIVE_API_KEY",
    "USGS_WATER_API_KEY",
    "WEBHOOK_SHARED_SECRET",
    "ALPHAVANTAGE_API_KEY"
]

before = {k: bool(os.environ.get(k, "").strip()) for k in needed}

for k, v in env_file.items():
    if isinstance(v, str) and v.strip():
        os.environ[k] = v.strip()

after = {k: bool(os.environ.get(k, "").strip()) for k in needed}

smoke_exists = SMOKE.exists()
smoke_rc = None
smoke_stdout = ""
smoke_stderr = ""

if smoke_exists:
    try:
        r = subprocess.run(
            ["python", str(SMOKE)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            timeout=120
        )
        smoke_rc = r.returncode
        smoke_stdout = (r.stdout or "")[-12000:]
        smoke_stderr = (r.stderr or "")[-12000:]
    except Exception as e:
        smoke_stderr = f"{type(e).__name__}: {e}"

proof = {
    "generated_utc": now_utc(),
    "env_file": str(ENV_PATH),
    "smoke_script": str(SMOKE),
    "smoke_exists": smoke_exists,
    "before_present": before,
    "after_present": after,
    "kraken_key_after": after.get("KRAKEN_API_KEY", False),
    "kraken_secret_after": after.get("KRAKEN_API_SECRET", False),
    "smoke_return_code": smoke_rc,
    "smoke_stdout_tail": smoke_stdout,
    "smoke_stderr_tail": smoke_stderr
}

PROOF.write_text(json.dumps(proof, indent=2), encoding="utf-8")

print("RUNTIME ENV HYDRATION COMPLETE")
print("proof:", PROOF)
print("kraken_key_after:", proof["kraken_key_after"])
print("kraken_secret_after:", proof["kraken_secret_after"])
print("smoke_return_code:", proof["smoke_return_code"])