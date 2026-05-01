from kraken_execution import (
    verify_env_only,
    get_balance,
    get_open_orders,
    arm_deadman_switch,
    submit_order_validate_only,
)

print("=== KRAKEN STAGE 2 SMOKE TEST START ===")

print("ENV:", verify_env_only())

try:
    bal = get_balance()
    print("BALANCE OK")
    print(bal)
except Exception as e:
    print("BALANCE FAILED:", e)

try:
    oo = get_open_orders()
    print("OPEN ORDERS OK")
    print(oo)
except Exception as e:
    print("OPEN ORDERS FAILED:", e)

try:
    dms = arm_deadman_switch(30)
    print("DEADMAN SWITCH OK")
    print(dms)
except Exception as e:
    print("DEADMAN FAILED:", e)

try:
    result = submit_order_validate_only(
        controller="Robert",
        pair="XBTUSD",
        side="buy",
        notional_usd=25.0,
        note="Stage 2 smoke test validate-only"
    )
    print("VALIDATE-ONLY ORDER OK")
    print(result)
except Exception as e:
    print("VALIDATE-ONLY ORDER FAILED:", e)

print("=== KRAKEN STAGE 2 SMOKE TEST END ===")
