"""Build a deterministic, public-safe LumaSkin protocol status packet."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "lumaskin_test_protocol_v1.json"
OUTPUT_JSON = ROOT / "out" / "ops" / "lumaskin_protocol_packet_latest.json"
OUTPUT_MD = (
    ROOT
    / "docs"
    / "hardware"
    / "lumaskin_xr_research_platform"
    / "PROTOCOL_STATUS.md"
)
ASSET_METADATA_PATH = (
    ROOT / "assets" / "hardware" / "flowform_lumaskin_xr_research_v1_concept.json"
)
ARTIFACT_PATHS = (
    "config/lumaskin_test_protocol_v1.json",
    "code/hardware/lumaskin_safety_controller.py",
    "code/ops/BUILD_LUMASKIN_PROTOCOL_PACKET.py",
    "assets/hardware/flowform_lumaskin_xr_research_v1_concept.svg",
    "assets/hardware/flowform_lumaskin_xr_research_v1_concept.json",
    "docs/hardware/lumaskin_xr_research_platform/README.md",
    "build_week/lumaskin_lab/index.html",
    "build_week/lumaskin_lab/styles.css",
    "build_week/lumaskin_lab/app.js",
    "tests/test_lumaskin_xr_research_platform.py",
)
CANONICAL_STATUS = "BENCH_PROTOCOL_READY_HUMAN_TESTS_BLOCKED"
CANONICAL_ASSET_STATUS = "CONCEPT_DIAGRAM_NOT_ENGINEERING_VALIDATION"


class ProtocolError(ValueError):
    pass


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _file_receipt(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    content = path.read_bytes()
    return {
        "path": relative_path,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def build_artifact_manifest() -> dict[str, Any]:
    metadata = json.loads(ASSET_METADATA_PATH.read_text(encoding="utf-8"))
    visual_path = ROOT / metadata["asset_path"]
    visual_bytes = visual_path.read_bytes()
    visual_sha256 = hashlib.sha256(visual_bytes).hexdigest()
    if metadata.get("status") != CANONICAL_ASSET_STATUS:
        raise ProtocolError("concept asset status is stronger than the canonical boundary")
    if metadata.get("bytes") != len(visual_bytes):
        raise ProtocolError("concept asset byte count does not match its metadata")
    if metadata.get("sha256") != visual_sha256:
        raise ProtocolError("concept asset SHA-256 does not match its metadata")

    artifacts = [_file_receipt(path) for path in ARTIFACT_PATHS]
    return {
        "schema": "lumencore.lumaskin_artifact_manifest.v1",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "manifest_sha256": hashlib.sha256(_canonical_bytes({"artifacts": artifacts})).hexdigest(),
        "visual_lineage_verified": True,
    }


def validate_public_projection(
    packet: dict[str, Any], projection: dict[str, Any]
) -> None:
    """Reject a reviewer-facing status that is stronger than the canonical packet."""

    expected = packet["public_projection"]
    for key in (
        "program_status",
        "asset_status",
        "human_testing_authorized",
        "independent_validation_complete",
    ):
        if projection.get(key) != expected.get(key):
            raise ProtocolError(f"public projection mismatch: {key}")


def validate_protocol(payload: dict[str, Any]) -> None:
    if payload.get("schema") != "lumencore.lumaskin_test_protocol.v1":
        raise ProtocolError("unexpected LumaSkin protocol schema")
    if "HUMAN_TESTS_BLOCKED" not in str(payload.get("status", "")):
        raise ProtocolError("V1 must remain explicitly blocked for human testing")

    tests = payload.get("test_families", [])
    gates = payload.get("authority_gates", [])
    test_ids = [item.get("id") for item in tests]
    gate_ids = [item.get("id") for item in gates]

    if test_ids != [f"TF-{number:02d}" for number in range(1, 9)]:
        raise ProtocolError("expected exactly eight ordered test families")
    if gate_ids != [f"AG-{number:02d}" for number in range(1, 9)]:
        raise ProtocolError("expected exactly eight ordered authority gates")

    for item in tests:
        if not item.get("comparator") or not item.get("primary_endpoints"):
            raise ProtocolError(f"{item.get('id')} lacks comparator or primary endpoints")
        if not item.get("acceptance_rule"):
            raise ProtocolError(f"{item.get('id')} lacks an acceptance rule")

    for gate in gates:
        if not gate.get("required_evidence"):
            raise ProtocolError(f"{gate.get('id')} lacks required evidence")

    hold = payload.get("human_test_hold", {})
    if hold.get("blocked_until_gates_pass") != [
        "AG-01",
        "AG-02",
        "AG-03",
        "AG-04",
        "AG-05",
        "AG-06",
    ]:
        raise ProtocolError("human-test hold must include gates AG-01 through AG-06")

    boundary = str(payload.get("claim_boundary", "")).lower()
    for phrase in (
        "non-medical",
        "not a fabricated product",
        "not a safety certification",
        "no strength amplification",
        "no unsupervised human use",
    ):
        if phrase not in boundary:
            raise ProtocolError(f"claim boundary is missing: {phrase}")


def build_packet(payload: dict[str, Any]) -> dict[str, Any]:
    validate_protocol(payload)
    tests = payload["test_families"]
    gates = payload["authority_gates"]
    packet = {
        "schema": "lumencore.lumaskin_protocol_packet.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "protocol_id": payload["protocol_id"],
        "protocol_version": payload["version"],
        "protocol_sha256": hashlib.sha256(_canonical_bytes(payload)).hexdigest(),
        "status": CANONICAL_STATUS,
        "summary": {
            "test_family_count": len(tests),
            "authority_gate_count": len(gates),
            "human_authority_gates_required": 6,
            "human_authority_gates_evidenced": 0,
            "human_testing_authorized": False,
            "independent_validation_complete": False,
        },
        "test_families": [
            {
                "id": item["id"],
                "name": item["name"],
                "stage": item["stage"],
                "status": "PROTOCOL_DEFINED_NOT_RUN",
            }
            for item in tests
        ],
        "authority_gates": [
            {
                "id": item["id"],
                "name": item["name"],
                "status": "OPEN",
                "required_evidence_count": len(item["required_evidence"]),
            }
            for item in gates
        ],
        "claim_boundary": payload["claim_boundary"],
        "artifact_manifest": build_artifact_manifest(),
        "public_projection": {
            "program_status": CANONICAL_STATUS,
            "asset_status": CANONICAL_ASSET_STATUS,
            "human_testing_authorized": False,
            "independent_validation_complete": False,
        },
        "next_bounded_action": (
            "Run the executable controller and synthetic fault sweep for AG-02; "
            "do not energize a garment on a person."
        ),
    }
    validate_public_projection(packet, packet["public_projection"])
    return packet


def _render_markdown(packet: dict[str, Any]) -> str:
    summary = packet["summary"]
    lines = [
        "# LumaSkin Protocol Status",
        "",
        f"- Generated UTC: `{packet['generated_at_utc']}`",
        f"- Protocol: `{packet['protocol_id']}` version `{packet['protocol_version']}`",
        f"- Protocol SHA-256: `{packet['protocol_sha256']}`",
        f"- Artifact manifest SHA-256: `{packet['artifact_manifest']['manifest_sha256']}`",
        f"- Status: **{packet['status']}**",
        f"- Test families defined: **{summary['test_family_count']}**",
        f"- Authority gates open: **{summary['authority_gate_count']} / {summary['authority_gate_count']}**",
        "- Human testing authorized: **No**",
        "- Independent validation complete: **No**",
        "",
        "## Test Families",
        "",
        "| ID | Test family | Stage | Current evidence |",
        "| --- | --- | --- | --- |",
    ]
    for item in packet["test_families"]:
        lines.append(
            f"| {item['id']} | {item['name']} | {item['stage']} | {item['status']} |"
        )

    lines.extend(
        [
            "",
            "## Authority Gates",
            "",
            "| ID | Gate | Status | Evidence items required |",
            "| --- | --- | --- | ---: |",
        ]
    )
    for item in packet["authority_gates"]:
        lines.append(
            f"| {item['id']} | {item['name']} | {item['status']} | "
            f"{item['required_evidence_count']} |"
        )

    lines.extend(
        [
            "",
            "## Next Bounded Action",
            "",
            packet["next_bounded_action"],
            "",
            "## Claim Boundary",
            "",
            packet["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    packet = build_packet(payload)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(_render_markdown(packet), encoding="utf-8")
    print(OUTPUT_JSON)
    print(OUTPUT_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
