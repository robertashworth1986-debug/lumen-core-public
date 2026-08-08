import os

from kraken_execution import arm_deadman_switch, get_balance, get_open_orders, verify_env_only


def _private_smoke_authorized() -> bool:
    return os.getenv("LUMA_ALLOW_PRIVATE_EXCHANGE_SMOKE", "").strip().lower() in {
        "1", "true", "yes", "on"
    }


def main() -> int:
    print("=== KRAKEN SMOKE TEST START ===")
    env_status = verify_env_only()
    if env_status.get("credential_state") != "configured":
        print("ENV CHECK FAILED: credentials_missing")
        return 2
    print("ENV CHECK OK")

    if not _private_smoke_authorized():
        print("PRIVATE CHECKS SKIPPED: explicit_operator_opt_in_required")
        print("=== KRAKEN SMOKE TEST END ===")
        return 0

    checks = (
        ("BALANCE", get_balance),
        ("OPEN ORDERS", get_open_orders),
        ("DEADMAN SWITCH", lambda: arm_deadman_switch(30)),
    )
    failed = False
    for label, operation in checks:
        try:
            operation()
            print(f"{label} OK")
        except Exception as exc:
            failed = True
            print(f"{label} FAILED: {type(exc).__name__}")
    print("=== KRAKEN SMOKE TEST END ===")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
