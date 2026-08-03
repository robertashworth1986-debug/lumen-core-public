from __future__ import annotations

import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "ops"
SPRINT = ROOT / "grant_submissions" / "funding_sprint_20260709"

JSON_OUT = OUT / "epri_opai_brand_asset_packet_latest.json"
MD_OUT = SPRINT / "EPRI_OPAI_BRAND_ASSET_PACKET_2026-07-25.md"

ASSETS = (
    {
        "role": "logo_on_dark",
        "path": "dashboard/brand/lumencore_logo_on_dark_1024.png",
        "intended_background": "dark",
    },
    {
        "role": "logo_on_light",
        "path": "dashboard/brand/lumencore_logo_on_light_1024.png",
        "intended_background": "light",
    },
)

CLAIM_BOUNDARY = (
    "This packet verifies two local LumenCore PNG brand assets requested during "
    "Open Power AI onboarding. It does not prove that either asset was sent, "
    "received, accepted, published, or endorsed by EPRI or the consortium."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Not a valid PNG: {path}")
    if header[12:16] != b"IHDR":
        raise ValueError(f"PNG is missing an IHDR header: {path}")
    return struct.unpack(">II", header[16:24])


def inspect_asset(spec: dict[str, str]) -> dict[str, Any]:
    relative_path = spec["path"]
    path = ROOT / Path(relative_path)
    exists = path.is_file()
    row: dict[str, Any] = {
        **spec,
        "exists": exists,
        "bytes": path.stat().st_size if exists else 0,
        "width": 0,
        "height": 0,
        "sha256": "",
        "ready": False,
        "blockers": [],
    }
    if not exists:
        row["blockers"].append("MISSING_ASSET")
        return row
    if row["bytes"] <= 0:
        row["blockers"].append("ZERO_BYTE_ASSET")
        return row
    try:
        width, height = png_dimensions(path)
    except ValueError:
        row["blockers"].append("INVALID_PNG")
        return row
    row["width"] = width
    row["height"] = height
    row["sha256"] = sha256_file(path)
    if (width, height) != (1024, 1024):
        row["blockers"].append("UNEXPECTED_DIMENSIONS")
    row["ready"] = not row["blockers"]
    return row


def build_packet() -> dict[str, Any]:
    assets = [inspect_asset(spec) for spec in ASSETS]
    all_ready = len(assets) == 2 and all(row["ready"] for row in assets)
    payload: dict[str, Any] = {
        "schema": "lumencore.epri_opai_brand_asset_packet.v1",
        "generated_utc": now_utc(),
        "lane_id": "epri_open_power_ai_onboarding",
        "source_event": {
            "observed_utc": "2026-07-24T16:02:01Z",
            "request": (
                "Provide one light-background and one dark-background "
                "LumenCore logo in PNG format."
            ),
        },
        "status": (
            "ASSETS_READY_HUMAN_SEND_REQUIRED"
            if all_ready
            else "ASSET_PACKET_BLOCKED"
        ),
        "summary": {
            "asset_count": len(assets),
            "ready_asset_count": sum(bool(row["ready"]) for row in assets),
            "all_assets_ready": all_ready,
            "attachment_count_if_approved": 2 if all_ready else 0,
        },
        "assets": assets,
        "controls": {
            "send_performed": False,
            "gmail_draft_created": False,
            "external_send_allowed_without_human": False,
            "existing_onboarding_thread_required": True,
            "fresh_duplicate_check_required": True,
            "additional_attachment_allowed": False,
        },
        "safest_next_action": (
            "After a fresh full-thread duplicate check and exact action-time "
            "approval, reply in the existing onboarding thread with only these "
            "two PNG files."
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    payload["packet_sha256"] = canonical_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# EPRI Open Power AI Brand Asset Packet",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Assets",
        "",
        "| Role | Path | Dimensions | Bytes | SHA-256 | Ready |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in payload["assets"]:
        dimensions = f"{row['width']}x{row['height']}"
        lines.append(
            f"| `{row['role']}` | `{row['path']}` | `{dimensions}` | "
            f"`{row['bytes']}` | `{row['sha256']}` | "
            f"`{str(row['ready']).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Controls",
            "",
            "- Send performed: `false`",
            "- Gmail draft created: `false`",
            "- Existing onboarding thread required: `true`",
            "- Fresh duplicate check required: `true`",
            "- Exact action-time approval required: `true`",
            "- Additional attachment allowed: `false`",
            "",
            "## Safest Next Action",
            "",
            payload["safest_next_action"],
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            f"Packet SHA-256: `{payload['packet_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_packet(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or build_packet()
    OUT.mkdir(parents=True, exist_ok=True)
    SPRINT.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    MD_OUT.write_text(render_markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    payload = write_packet()
    print(
        json.dumps(
            {
                "status": payload["status"],
                "ready_asset_count": payload["summary"]["ready_asset_count"],
                "asset_count": payload["summary"]["asset_count"],
                "packet_sha256": payload["packet_sha256"],
                "json": JSON_OUT.relative_to(ROOT).as_posix(),
                "markdown": MD_OUT.relative_to(ROOT).as_posix(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["summary"]["all_assets_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
