from __future__ import annotations

from email.message import Message
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "code" / "deploy" / "BOOTSTRAP_PUBLIC_SITE_ORIGIN.sh"
CLOUD_INIT = (
    ROOT
    / "code"
    / "deploy"
    / "cloud-init"
    / "lumencore-public-origin-cloud-config.yml"
)
NGINX = ROOT / "code" / "deploy" / "nginx" / "lumencore-public-origin.conf"
VERIFIER = ROOT / "code" / "ops" / "VERIFY_PUBLIC_SITE_LIVE_RELEASE.py"
WORKFLOW = ROOT / ".github" / "workflows" / "stage-public-site-origin.yml"


def load_verifier():
    spec = importlib.util.spec_from_file_location("candidate_origin_verifier", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_static_origin_configuration_has_no_private_runtime_routes():
    config = NGINX.read_text(encoding="utf-8")

    assert "root /opt/lumencore/dashboard;" in config
    assert "location = /nginx-health" in config
    assert "try_files /operator_home.html =404;" in config
    assert "try_files /evidence/index_bounded.html =404;" in config
    assert "try_files /build_week/prooflock_console/index.html =404;" in config
    assert "return 302 https://lumen-core.ai/proof_to_pilot.html;" in config
    assert "return 302 https://lumen-core.ai/quant_lab.html;" in config
    assert "ssl_certificate /etc/letsencrypt/live/lumen-core.ai/fullchain.pem;" in config
    assert "limit_except GET HEAD { deny all; }" in config
    assert "autoindex off;" in config

    for forbidden in (
        "proxy_pass",
        "upstream ",
        "autoindex on",
        "127.0.0.1:8787",
        "127.0.0.1:5016",
        "127.0.0.1:5017",
        "127.0.0.1:7700",
        "location /api",
        "location /trading",
        "location /out",
    ):
        assert forbidden not in config


def test_bootstrap_is_candidate_gated_bounded_and_provider_neutral():
    script = BOOTSTRAP.read_text(encoding="utf-8")

    gate = '[[ "$approval" == "$REQUIRED_APPROVAL" ]]'
    assert 'readonly REQUIRED_APPROVAL="BOOTSTRAP_PUBLIC_SITE_CANDIDATE"' in script
    assert gate in script
    assert script.index(gate) < script.index("apt-get update")
    assert '[[ "${ID:-}" == "ubuntu" ]]' in script
    assert "22.04|24.04" in script
    assert '[[ "$actual_config_sha256" == "$nginx_config_sha256" ]]' in script
    assert "lumencore-reviewed-origin." in script
    assert '[[ "$reviewed_copy_sha256" == "$nginx_config_sha256" ]]' in script
    assert 'install -o root -g root -m 0644 -- "$reviewed_config_copy"' in script
    assert "/usr/sbin/policy-rc.d" in script
    assert "exposing Ubuntu's default Nginx" in script
    assert 'readonly DASHBOARD_ROOT="/opt/lumencore/dashboard"' in script
    assert 'readonly PUBLIC_RELEASE_ROLLBACK_ROOT="$ROLLBACK_ROOT/public-site"' in script
    assert "http_acme_hold" in script
    assert "canonical_https" in script
    assert "nginx -t" in script
    assert "PUBLIC_ORIGIN_TLS_READY=" in script
    assert "lumencore.public_origin_bootstrap_receipt.v1" in script

    for forbidden in (
        "git clone",
        "git pull",
        "api.digitalocean.com",
        "api.vultr.com",
        "api.linode.com",
        "terraform apply",
        "certbot certonly",
        "certbot --nginx",
        "DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT",
    ):
        assert forbidden not in script


def test_cloud_init_creates_only_a_locked_non_root_candidate_identity():
    cloud_init = CLOUD_INIT.read_text(encoding="utf-8")

    assert cloud_init.startswith("#cloud-config\n")
    assert "package_update: true" in cloud_init
    assert "package_upgrade: true" in cloud_init
    assert "disable_root: true" in cloud_init
    assert "ssh_pwauth: false" in cloud_init
    assert "name: lumencore-deploy" in cloud_init
    assert "lock_passwd: true" in cloud_init
    assert "__LUMENCORE_DEPLOY_SSH_PUBLIC_KEY__" in cloud_init
    assert "PermitRootLogin no" in cloud_init
    assert "PasswordAuthentication no" in cloud_init
    assert "KbdInteractiveAuthentication no" in cloud_init
    assert "sshd, -t" in cloud_init

    for forbidden in (
        "BEGIN OPENSSH PRIVATE KEY",
        "BEGIN RSA PRIVATE KEY",
        "api.digitalocean.com",
        "api.vultr.com",
        "api.linode.com",
        "lumen-core.ai A ",
        "certbot certonly",
    ):
        assert forbidden not in cloud_init


def test_candidate_workflow_is_manual_commit_pinned_and_not_a_promotion_lane():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    trigger = workflow.split("permissions:", maxsplit=1)[0]

    assert "workflow_dispatch:" in trigger
    assert "push:" not in trigger
    assert "schedule:" not in trigger
    assert "STAGE_PUBLIC_SITE_CANDIDATE" in trigger
    assert '[[ "$RELEASE_COMMIT" == "$WORKFLOW_COMMIT" ]]' in workflow
    assert '[[ "$CANDIDATE_SSH_USER" != "root" ]]' in workflow
    assert "candidate.version != 4 or not candidate.is_global" in workflow
    assert "candidate workflow refuses an address currently serving lumen-core.ai" in workflow
    assert "environment:\n      name: production-candidate" in workflow
    assert workflow.index('[[ "$APPROVAL" == "STAGE_PUBLIC_SITE_CANDIDATE" ]]') < workflow.index(
        "Install candidate-only SSH key"
    )
    assert "CANDIDATE_ORIGIN_SSH_PRIVATE_KEY" in workflow
    assert "CANDIDATE_ORIGIN_KNOWN_HOSTS" in workflow
    assert "StrictHostKeyChecking=yes" in workflow
    assert "cloud-init status --wait" in workflow
    assert "BOOTSTRAP_PUBLIC_SITE_ORIGIN.sh" in workflow
    assert "APPLY_PUBLIC_SITE_RELEASE_ON_VPS.sh" in workflow
    assert "--resolve-address \"$CANDIDATE_ADDRESS\"" in workflow
    assert "openssl x509 -in \"$candidate_certificate\" -checkend 604800 -noout" in workflow
    assert "CLASSIFY_PUBLIC_RELEASE_INCIDENT.py" in workflow
    assert "candidate-target-receipt.json" in workflow
    assert "cannot create or purchase infrastructure" in workflow
    assert "cannot" in workflow and "mutate DNS" in workflow

    for forbidden in (
        "VPS_SSH_PRIVATE_KEY",
        "VPS_HOST",
        "StrictHostKeyChecking=no",
        "api.digitalocean.com",
        "api.vultr.com",
        "api.linode.com",
        "api.godaddy.com",
        "doctl ",
        "terraform apply",
    ):
        assert forbidden not in workflow


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("203.0.113.7", "203.0.113.7"),
        ("2001:db8::7", "2001:db8::7"),
        (None, None),
    ],
)
def test_resolve_address_accepts_only_normalized_literal_ips(value, expected):
    verifier = load_verifier()
    assert verifier.normalize_resolve_address(value) == expected


@pytest.mark.parametrize(
    "value",
    ["lumen-core.ai", "127.0.0.1:443", "2001:db8::1%eth0", "", "1.2.3.999"],
)
def test_resolve_address_rejects_names_ports_zones_and_invalid_ips(value):
    verifier = load_verifier()
    with pytest.raises(ValueError, match="literal IPv4 or IPv6"):
        verifier.normalize_resolve_address(value)


def test_ip_pinned_fetch_preserves_canonical_host_and_request_target(monkeypatch):
    verifier = load_verifier()
    observed: dict[str, object] = {}

    headers = Message()
    headers["Content-Type"] = "application/json"

    class FakeResponse:
        status = 200
        reason = "OK"

        def __init__(self):
            self.headers = headers

        @staticmethod
        def read():
            return b"{}\n"

    class FakeConnection:
        def __init__(self, host, **kwargs):
            observed["host"] = host
            observed["connection"] = kwargs

        def request(self, method, target, headers):
            observed["method"] = method
            observed["target"] = target
            observed["headers"] = headers

        @staticmethod
        def getresponse():
            return FakeResponse()

        @staticmethod
        def close():
            observed["closed"] = True

    monkeypatch.setattr(verifier, "ResolvedHTTPSConnection", FakeConnection)
    body, status, content_type = verifier.fetch_url(
        "https://lumen-core.ai/evidence/?release=" + "a" * 40,
        timeout=5.0,
        resolve_address="203.0.113.7",
    )

    assert body == b"{}\n"
    assert status == 200
    assert content_type == "application/json"
    assert observed["host"] == "lumen-core.ai"
    assert observed["connection"]["resolve_address"] == "203.0.113.7"
    assert observed["headers"]["Host"] == "lumen-core.ai"
    assert observed["headers"]["Accept-Encoding"] == "identity"
    assert observed["target"] == "/evidence/?release=" + "a" * 40
    assert observed["closed"] is True


def test_resolved_connection_uses_logical_host_for_tls_sni():
    source = VERIFIER.read_text(encoding="utf-8")
    assert "socket.create_connection(" in source
    assert "(str(self.resolve_address), self.port)" in source
    assert "server_hostname=self.host" in source
    assert "ssl.create_default_context()" in source
