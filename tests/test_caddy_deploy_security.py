from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CADDY_CONFIGS = (
    ROOT / "deploy" / "Caddyfile",
    ROOT / "code" / "deploy" / "Caddyfile.lumen-core.autofull",
)
CANONICAL_PUBLIC_WEB_ROOT = "/opt/lumencore/dashboard"


def test_tracked_caddy_configs_do_not_embed_basic_auth_material() -> None:
    bcrypt_verifier = re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}")

    for path in CADDY_CONFIGS:
        text = path.read_text(encoding="utf-8")
        assert not bcrypt_verifier.search(text), path
        assert "Default credentials" not in text, path
        assert "import /etc/caddy/lumencore-auth.caddy" in text, path


def test_caddy_setup_installs_auth_material_outside_source_and_validates() -> None:
    setup = (ROOT / "deploy" / "setup_vps.sh").read_text(encoding="utf-8")

    assert "LUMA_CADDY_AUTH_USER" in setup
    assert "LUMA_CADDY_AUTH_HASH" in setup
    assert "must be a bcrypt verifier" in setup
    assert "-o root -g caddy -m 0640" in setup
    assert "/etc/caddy/lumencore-auth.caddy" in setup
    assert "caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile" in setup

    validate_at = setup.index(
        "caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile"
    )
    restart_at = setup.index("systemctl restart caddy")
    assert validate_at < restart_at


def test_caddy_and_setup_use_the_governed_release_destination() -> None:
    for path in CADDY_CONFIGS:
        text = path.read_text(encoding="utf-8")
        assert f"root * {CANONICAL_PUBLIC_WEB_ROOT}" in text, path
        assert "root * /var/www/lumen-core" not in text, path
        assert "root * /var/www/lumatrader" not in text, path

    setup = (ROOT / "deploy" / "setup_vps.sh").read_text(encoding="utf-8")
    assert f"LUMA_PUBLIC_WEB_ROOT:-{CANONICAL_PUBLIC_WEB_ROOT}" in setup
    assert "/var/www/lumen-core" not in setup
