import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(
    os.getenv("LUMA_STACK_ROOT", r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
).resolve()
CONF = ROOT / "config"
OUT = ROOT / "out"
ENV_PATH = CONF / "luma_live_keys.env"
SMOKE = ROOT / "code" / "kraken_smoke_test_stage2.py"
PROOF = OUT / "runtime_env_hydration_proof.json"

NEEDED = (
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
    "ALPHAVANTAGE_API_KEY",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def configured_slot_count() -> int:
    return sum(bool(os.environ.get(name, "").strip()) for name in NEEDED)


def private_exchange_contact_authorized() -> bool:
    return os.getenv("LUMA_ALLOW_PRIVATE_EXCHANGE_SMOKE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def main() -> int:
    before_count = configured_slot_count()
    env_file = parse_env(ENV_PATH)
    for key, value in env_file.items():
        if isinstance(value, str) and value.strip():
            os.environ[key] = value.strip()
    after_count = configured_slot_count()

    smoke_exists = SMOKE.is_file()
    smoke_return_code: int | None = None
    smoke_status = "missing"
    smoke_markers = {
        "env_check_ok": False,
        "private_checks_skipped": False,
        "validate_only_ok": False,
    }
    error_code: str | None = None

    if smoke_exists:
        try:
            result = subprocess.run(
                [sys.executable, str(SMOKE)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                env=os.environ.copy(),
                timeout=120,
                check=False,
            )
            smoke_return_code = int(result.returncode)
            stdout = result.stdout or ""
            smoke_markers = {
                "env_check_ok": "ENV CHECK OK" in stdout,
                "private_checks_skipped": "PRIVATE CHECKS SKIPPED" in stdout,
                "validate_only_ok": "VALIDATE-ONLY ORDER OK" in stdout,
            }
            smoke_status = "pass" if result.returncode == 0 else "fail"
        except subprocess.TimeoutExpired:
            smoke_status = "timeout"
            error_code = "SMOKE_TIMEOUT"
        except (OSError, ValueError) as exc:
            smoke_status = "error"
            error_code = f"SMOKE_{type(exc).__name__.upper()}"

    proof = {
        "generated_utc": now_utc(),
        "credential_file_found": ENV_PATH.is_file(),
        "credential_source_file": ENV_PATH.name if ENV_PATH.is_file() else None,
        "configured_slot_count_before": before_count,
        "configured_slot_count_after": after_count,
        "smoke_script_found": smoke_exists,
        "smoke_return_code": smoke_return_code,
        "smoke_status": smoke_status,
        "smoke_markers": smoke_markers,
        "private_exchange_contact_authorized": private_exchange_contact_authorized(),
        "raw_process_output_persisted": False,
        "error_code": error_code,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    PROOF.write_text(json.dumps(proof, indent=2), encoding="utf-8")

    print("RUNTIME ENV HYDRATION COMPLETE")
    print(f"proof: {PROOF}")
    print(f"smoke_status: {smoke_status}")
    print(f"smoke_return_code: {smoke_return_code}")
    return 0 if smoke_status in {"pass", "missing"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
