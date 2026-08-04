from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    ROOT / "deploy" / "PUSH_TO_VPS.ps1",
    ROOT / "deploy" / "PUSH_PROOF_FEEDS_TO_VPS.ps1",
    ROOT / "deploy" / "REPAIR_LUMA_GATEWAY_MODULE.ps1",
    ROOT / "code" / "ops" / "UPLOAD_TO_ORACLE.ps1",
)


def test_all_vps_mutation_scripts_require_strict_pinned_host_verification():
    for path in SCRIPTS:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()

        assert "stricthostkeychecking=yes" in lowered, path
        assert "stricthostkeychecking=no" not in lowered, path
        assert "userknownhostsfile=" in lowered, path
        assert "luma_ssh_known_hosts" in lowered, path
        assert "luma_human_unlock_token" in lowered, path
        assert "[switch]$apply" in lowered, path
        assert "if (-not $apply)" in lowered, path


def test_deployment_scripts_do_not_embed_hosts_or_named_private_key_candidates():
    ipv4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
    for path in SCRIPTS:
        text = path.read_text(encoding="utf-8")

        assert set(ipv4.findall(text)) <= {"127.0.0.1", "0.0.0.0"}, path
        assert "Downloads\\" not in text, path
        assert "ssh-key-" not in text.lower(), path
        assert "oracle_new" not in text.lower(), path


def test_legacy_oracle_uploader_is_default_no_mutation():
    text = (ROOT / "code" / "ops" / "UPLOAD_TO_ORACLE.ps1").read_text(
        encoding="utf-8"
    )

    guard_index = text.index("if (-not $Apply)")
    zip_index = text.index("[1/3] Zipping stack")
    scp_index = text.index("& scp @sshSecurityArgs")
    bootstrap_index = text.index("& ssh @sshSecurityArgs")

    assert guard_index < zip_index
    assert guard_index < scp_index
    assert guard_index < bootstrap_index
    assert "no archive, key-permission change, network call" in text
