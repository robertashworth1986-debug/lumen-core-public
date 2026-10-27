"""Read-only MIME evidence must retain useful facts without leaking raw config."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code/ops/INSPECT_PUBLIC_MIME_MAPPING.py"
spec = importlib.util.spec_from_file_location("mime_inspector", SCRIPT)
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)


def test_active_mapping_reports_source_lines_and_existing_mime():
    dump = """# configuration file /etc/nginx/nginx.conf:
http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
}
# configuration file /etc/nginx/mime.types:
types {
    application/javascript js;
    text/css css;
}
"""
    result = inspector.inspect_dump(dump, metadata=False)
    rows = result["active_configuration_evidence"]
    assert rows[0]["active_file"] == "/etc/nginx/nginx.conf"
    mapping = next(fact for fact in rows[1]["facts"] if fact["kind"] == "javascript_mapping")
    assert mapping == {"line": 3, "kind": "javascript_mapping", "mime": "application/javascript", "extensions": ["js"]}
    assert result["scope_review_required"] is True


def test_conflicting_mjs_mapping_is_preserved_for_review():
    result = inspector.inspect_dump("# configuration file /etc/nginx/mime.types:\ntext/plain mjs;\n", metadata=False)
    fact = result["active_configuration_evidence"][0]["facts"][0]
    assert fact["kind"] == "other_mjs_mapping"
    assert fact["mime"] == "text/plain"


def test_private_directives_and_unknown_locations_are_not_emitted():
    dump = """# configuration file /etc/nginx/conf.d/public.conf:
server {
    server_name lumen-core.ai app.lumen-core.ai unrelated.example;
    root /opt/lumencore/dashboard;
    proxy_set_header Authorization "Bearer secret-fixture";
    ssl_certificate_key /private/secret-fixture.key;
    # secret-fixture comment
    location /portfolio/ {
    }
    location ~ secret-fixture.js {
    }
}
"""
    encoded = json.dumps(inspector.inspect_dump(dump, metadata=False))
    assert "secret-fixture" not in encoded
    assert "unrelated.example" not in encoded
    assert "proxy_set_header" not in encoded
    assert "ssl_certificate_key" not in encoded
    assert "/portfolio/" in encoded
    assert "lumen-core.ai" in encoded


@pytest.mark.parametrize("path", ["/tmp/private.conf", "/etc/nginx/../private.conf", "/etc/nginx/private token.conf"])
def test_nonallowlisted_section_paths_are_omitted(path):
    dump = f"# configuration file {path}:\napplication/javascript js;\n"
    assert inspector.inspect_dump(dump, metadata=False)["active_configuration_evidence"] == []


def test_failure_retains_bounded_receipt_without_raw_diagnostics(monkeypatch, capsys):
    monkeypatch.setattr(inspector.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="secret-fixture", stderr="secret-fixture"))
    assert inspector.main() == 1
    output = capsys.readouterr().out
    receipt = json.loads(output)
    assert receipt["status"] == "INSPECTION_FAILED"
    assert receipt["configuration_modified"] is False
    assert receipt["service_reloaded"] is False
    assert "secret-fixture" not in output


def test_success_only_runs_nginx_inspection_and_hashes_known_modules(monkeypatch, capsys, tmp_path):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(inspector.subprocess, "run", run)
    monkeypatch.setattr(inspector, "ROOT", tmp_path)
    for relative in inspector.EXPECTED:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    assert inspector.main() == 0
    receipt = json.loads(capsys.readouterr().out)
    assert [call[0] for call in calls] == [["nginx", "-T"]]
    assert calls[0][1]["timeout"] == 25
    assert len(receipt["module_files"]) == 3
    assert all(not item["matches_release"] for item in receipt["module_files"])
    assert receipt["status"] == "INSPECTED_REVIEW_REQUIRED"


def test_symlinked_module_fails_without_disclosing_target(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(inspector.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(inspector, "ROOT", tmp_path)
    first = tmp_path / next(iter(inspector.EXPECTED))
    first.parent.mkdir(parents=True)
    # Patch the boundary decision without relying on Windows symlink privileges.
    monkeypatch.setattr(Path, "resolve", lambda self, strict=False: self)
    monkeypatch.setattr(Path, "is_symlink", lambda self: True)
    assert inspector.main() == 1
    assert json.loads(capsys.readouterr().out)["status"] == "INSPECTION_FAILED"


def test_workflow_inspection_preserves_gates_and_retains_receipt_early():
    text = (ROOT / ".github/workflows/vps-storage-diagnostic.yml").read_text()
    assert "if: github.event_name != 'pull_request'" in text
    assert "environment: production" in text
    assert "needs: validate" in text
    assert "ref: ${{ github.sha }}" in text
    assert "group: lumencore-vps-runtime-diagnostic" in text
    assert "< code/ops/INSPECT_PUBLIC_MIME_MAPPING.py" in text
    assert "StrictHostKeyChecking=yes" in text
    assert "'sudo -n python3 -'" in text
    assert "inspection_sha256" in text and "inspector_sha256" in text
    assert "retention-days: 30" in text
    assert text.index("Retain bounded MIME inspection evidence") < text.index("Capture runtime, gateway, and capacity evidence")
