from kraken_execution import verify_env_only, get_balance, get_open_orders, arm_deadman_switch

print("=== KRAKEN SMOKE TEST START ===")

env_status = verify_env_only()
print("ENV STATUS:", env_status)

try:
    balance = get_balance()
    print("BALANCE OK")
    print(balance)
except Exception as e:
    print("BALANCE FAILED:", e)

try:
    open_orders = get_open_orders()
    print("OPEN ORDERS OK")
    print(open_orders)
except Exception as e:
    print("OPEN ORDERS FAILED:", e)

try:
    deadman = arm_deadman_switch(30)
    print("DEADMAN SWITCH OK")
    print(deadman)
except Exception as e:
    print("DEADMAN FAILED:", e)

print("=== KRAKEN SMOKE TEST END ===")
