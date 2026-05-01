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
    immersive.main()
    portal.main()
    print(json.dumps({
        "status": "ok",
        "artifacts": [
            str(unified.DASH / "LUMENCORE_MASTER_DASHBOARD_UNIFIED_20260425.html"),
            str(alpaca.HTML_OUT),
            str(scout.HTML_OUT),
            str(immersive.OUT),
            str(portal.HTML_OUT),
            str(portal.INDEX_OUT),
        ],
    }, indent=2))


if __name__ == "__main__":
    main()