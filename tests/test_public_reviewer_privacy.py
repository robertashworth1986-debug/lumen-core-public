from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PRIVATE_ENV_BY_FIELD = {
    "founder": "LUMENCORE_PRIVATE_FOUNDER_DISPLAY_NAME",
    "uei": "LUMENCORE_PRIVATE_UEI",
    "cage": "LUMENCORE_PRIVATE_CAGE",
    "ein": "LUMENCORE_PRIVATE_EIN",
    "uspto_non_provisional_application": (
        "LUMENCORE_PRIVATE_PATENT_APPLICATION"
    ),
    "patent_title": "LUMENCORE_PRIVATE_PATENT_TITLE",
}


def _default_founder_profile() -> dict[str, ast.expr]:
    source = (
        ROOT / "code" / "luma_experience_gateway_legacy.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name)
            and target.id == "default_founder_profile"
            for target in node.targets
        ):
            continue
        assert isinstance(node.value, ast.Dict)
        profile: dict[str, ast.expr] = {}
        for key, value in zip(node.value.keys, node.value.values):
            assert isinstance(key, ast.Constant)
            assert isinstance(key.value, str)
            profile[key.value] = value
        return profile
    raise AssertionError("default_founder_profile assignment not found")


def _assert_empty_default_getenv(
    node: ast.expr,
    expected_env: str,
) -> None:
    assert isinstance(node, ast.Call)
    assert isinstance(node.func, ast.Attribute)
    assert isinstance(node.func.value, ast.Name)
    assert node.func.value.id == "os"
    assert node.func.attr == "getenv"
    assert len(node.args) == 2
    assert isinstance(node.args[0], ast.Constant)
    assert node.args[0].value == expected_env
    assert isinstance(node.args[1], ast.Constant)
    assert node.args[1].value == ""
    assert not node.keywords


def test_private_founder_identifiers_are_runtime_only() -> None:
    profile = _default_founder_profile()
    assert set(profile) == {
        "founder",
        "company_system",
        "uei",
        "cage",
        "ein",
        "uspto_non_provisional_application",
        "patent_title",
    }
    for field, env_name in PRIVATE_ENV_BY_FIELD.items():
        _assert_empty_default_getenv(profile[field], env_name)

    company = profile["company_system"]
    assert isinstance(company, ast.Constant)
    assert company.value == "LumenCore"


def test_runtime_identifier_example_contains_names_only() -> None:
    path = ROOT / "config" / "private_runtime_identifiers.example"
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert lines == [f"{name}=" for name in PRIVATE_ENV_BY_FIELD.values()]


def test_public_reviewer_home_has_one_bounded_data_dependency() -> None:
    home = (
        ROOT / "dashboard" / "operator_home.html"
    ).read_text(encoding="utf-8")
    lowered = home.lower()
    for forbidden in (
        "mailto:",
        "fonts.googleapis.com",
        "/api/snapshot",
        "/mission_control.html",
        "/agent_approval_hub.html",
        "/kraken_execution_dashboard.html",
    ):
        assert forbidden not in lowered
    assert lowered.count("fetch(") == 1
    assert "fetch('/api/master/booth-brief'" in home
    assert "github.com/robertashworth1986-debug/lumen-core-public/issues/new" in home


def test_public_evidence_page_uses_review_route_not_direct_contact() -> None:
    page = (
        ROOT / "dashboard" / "evidence" / "index_bounded.html"
    ).read_text(encoding="utf-8")
    assert "mailto:" not in page.lower()
    assert "github.com/robertashworth1986-debug/lumen-core-public/issues/new" in page


def test_public_edge_blocks_known_operator_pages() -> None:
    config = (
        ROOT / "code" / "deploy" / "nginx" / "lumatrader.conf"
    ).read_text(encoding="utf-8")
    assert "BEGIN LUMENCORE PUBLIC EDGE MAP V1" in config
    assert "BEGIN LUMENCORE PUBLIC EDGE GUARD V1" in config
    assert "if ($lumencore_public_route_denied)" in config
    assert "    default 1;" in config
    assert "location = /dashboard {\n        return 404;" in config
    assert "location = /dashboard/ {\n        return 404;" in config
    assert "location / {\n        return 404;" in config
    assert "index operator_home.html index.html mission_control.html;" not in config
