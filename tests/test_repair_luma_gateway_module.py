from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy" / "REPAIR_LUMA_GATEWAY_MODULE.ps1"
MODULE = ROOT / "code" / "booth_public_contract.py"


def test_gateway_repair_script_is_bounded_and_human_gated() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "booth_public_contract.py" in text
    assert "This bounded repair accepts only booth_public_contract.py." in text
    assert "LUMA_HUMAN_UNLOCK_TOKEN" in text
    assert "ApprovedModuleSha256" in text
    assert "must exactly match the current module SHA-256" in text
    assert "sudo systemctl restart luma-gateway" in text
    assert "systemctl restart nginx" not in text
    assert "systemctl restart caddy" not in text
    assert "rm -rf" not in text
    assert "DRY RUN: no network call, upload, restart, or remote mutation was performed." in text


def test_gateway_repair_source_contract_is_present_and_hashable() -> None:
    assert MODULE.is_file()
    digest = hashlib.sha256(MODULE.read_bytes()).hexdigest()
    assert len(digest) == 64
    assert "public_booth_projection" in MODULE.read_text(encoding="utf-8")
