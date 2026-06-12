from __future__ import annotations

import json

import BUILD_ALPACA_PREMIUM_DASHBOARD as alpaca
import BUILD_DASHBOARD_PORTAL as portal
import BUILD_LUMA_EXPERIENCE_WEBAPP as immersive
import BUILD_LAMASCOUT_PREMIUM_DASHBOARD as scout
import UNIFIED_MASTER_DASHBOARD_BUILDER as unified


def main() -> None:
    unified.main()
    alpaca.main()
    scout.main()
    immersive_status = "ok"
    try:
        immersive.main()
    except SystemExit as exc:
        # Immersive mode is an optional presentation surface. A missing source
        # page must not terminate the production dashboard refresh loop.
        immersive_status = f"skipped: {exc}"
    portal.main()
    print(json.dumps({
        "status": "ok",
        "immersive_status": immersive_status,
        "artifacts": [
            str(unified.DASH / "LUMENCORE_MASTER_DASHBOARD_UNIFIED_20260425.html"),
            str(alpaca.HTML_OUT),
            str(scout.HTML_OUT),
            str(immersive.OUT) if immersive.OUT.exists() else None,
            str(portal.HTML_OUT),
            str(portal.INDEX_OUT),
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
