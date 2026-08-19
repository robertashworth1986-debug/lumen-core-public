from __future__ import annotations


RETIREMENT_REASON = (
    "legacy live arming is quarantined; use the canonical execution readiness "
    "workflow with a fresh hash-bound human action-time authority receipt"
)


class LegacyLiveArmingRetired(RuntimeError):
    pass


def _refuse_legacy_live_arming() -> None:
    raise LegacyLiveArmingRetired(RETIREMENT_REASON)


def arm_live_mode() -> dict:
    _refuse_legacy_live_arming()


def arm_paper_runtime() -> dict:
    _refuse_legacy_live_arming()


def create_live_arm_confirm() -> dict:
    _refuse_legacy_live_arming()


def write_proof(runtime_control: dict, paper_runtime: dict, confirm: dict) -> None:
    del runtime_control, paper_runtime, confirm
    _refuse_legacy_live_arming()


def main() -> int:
    print(f"REFUSED: {RETIREMENT_REASON}.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
