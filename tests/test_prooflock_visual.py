from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "build_week" / "prooflock_console"
SAMPLE = APP_DIR / "sample_receipt.json"
CORE = APP_DIR / "prooflock_core.js"
LATTICE = APP_DIR / "prooflock_lattice.js"
PYTHON_VERIFIER = APP_DIR / "verify_receipt.py"
RELEASE_VERSION = "20260718.1"


def run_node(source: str) -> str:
    completed = subprocess.run(
        ["node", "-e", source],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return completed.stdout.strip()


def load_python_verifier():
    spec = importlib.util.spec_from_file_location("prooflock_visual_python_verifier", PYTHON_VERIFIER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def js_path(path: Path) -> str:
    return path.resolve().as_posix()


def test_visual_seed_is_deterministic_from_receipt_hash():
    output = run_node(
        f"""
        const lattice = require({json.dumps(js_path(LATTICE))});
        const hash = "07f4d143210c5d0a175c480228273c6b3d4c5b01da5a12a5daeb38fcdfb0d961";
        const changed = `a${{hash.slice(1)}}`;
        console.log(JSON.stringify([lattice.deriveSeed(hash), lattice.deriveSeed(hash), lattice.deriveSeed(changed)]));
        """
    )
    first, second, changed = json.loads(output)
    assert first == second
    assert first != changed


def test_browser_editor_normalization_is_stable_on_windows_line_endings():
    output = run_node(
        f"""
        const core = require({json.dumps(js_path(CORE))});
        console.log(JSON.stringify([
          core.normalizeEditorText("alpha\\r\\nbeta\\rcharlie"),
          core.normalizeEditorText("alpha\\nbeta\\ncharlie")
        ]));
        """
    )
    windows, unix = json.loads(output)
    assert windows == unix == "alpha\nbeta\ncharlie"


def test_visual_state_comes_only_from_verifier_report():
    output = run_node(
        f"""
        const lattice = require({json.dumps(js_path(LATTICE))});
        console.log(JSON.stringify([
          lattice.deriveVisualState({{integrity_valid:false,promotion_allowed:false}}),
          lattice.deriveVisualState({{integrity_valid:true,promotion_allowed:false}}),
          lattice.deriveVisualState({{integrity_valid:true,promotion_allowed:true}})
        ]));
        """
    )
    assert json.loads(output) == ["FAIL", "HOLD", "PROMOTE"]


def test_guided_proof_restores_exact_sample_text():
    output = run_node(
        f"""
        const fs = require("node:fs");
        const lattice = require({json.dumps(js_path(LATTICE))});
        const text = fs.readFileSync({json.dumps(js_path(SAMPLE))}, "utf8");
        const receipt = JSON.parse(text);
        let current = "";
        const stages = [];
        (async () => {{
          const result = await lattice.runGuidedProof({{
            delayMs: 0,
            loadSample: async () => ({{text, receipt}}),
            verify: async (bundle) => {{ current = bundle.text; stages.push(bundle.stage); return {{}}; }}
          }});
          console.log(JSON.stringify({{status: result.status, exact: current === text, stages}}));
        }})().catch((error) => {{ console.error(error); process.exitCode = 1; }});
        """
    )
    result = json.loads(output)
    assert result["status"] == "restored"
    assert result["exact"] is True
    assert result["stages"] == ["custody", "tamper", "restored"]


def test_reduced_motion_disables_continuous_animation():
    output = run_node(
        f"""
        const lattice = require({json.dumps(js_path(LATTICE))});
        console.log(JSON.stringify(lattice.resolveQualityProfile({{reducedMotion:true,saveData:false,width:1200}})));
        """
    )
    profile = json.loads(output)
    assert profile["reducedMotion"] is True
    assert profile["animate"] is False


def test_python_and_browser_canonical_hashes_match():
    verifier = load_python_verifier()
    receipt = json.loads(SAMPLE.read_text(encoding="utf-8"))
    python_hash = verifier.stable_hash(verifier.receipt_payload(receipt))
    output = run_node(
        f"""
        const fs = require("node:fs");
        const core = require({json.dumps(js_path(CORE))});
        const receipt = JSON.parse(fs.readFileSync({json.dumps(js_path(SAMPLE))}, "utf8"));
        (async () => {{
          console.log(await core.sha256Text(core.canonicalize(core.receiptPayload(receipt))));
        }})().catch((error) => {{ console.error(error); process.exitCode = 1; }});
        """
    )
    assert output == python_hash == receipt["receipt_sha256"]


def test_python_and_browser_reports_match_on_canonical_fixture():
    verifier = load_python_verifier()
    receipt = json.loads(SAMPLE.read_text(encoding="utf-8"))
    python_report = verifier.verify_receipt(receipt)
    output = run_node(
        f"""
        const fs = require("node:fs");
        const path = require("node:path");
        const core = require({json.dumps(js_path(CORE))});
        const root = {json.dumps(js_path(ROOT))};
        const receipt = JSON.parse(fs.readFileSync({json.dumps(js_path(SAMPLE))}, "utf8"));
        (async () => {{
          const report = await core.verifyReceipt(receipt, {{loadArtifact: async (relative) => fs.readFileSync(path.join(root, relative))}});
          console.log(JSON.stringify({{
            integrity_valid: report.integrity_valid,
            promotion_allowed: report.promotion_allowed,
            artifact_count: report.artifact_count,
            artifact_hash_match_count: report.artifact_hash_match_count,
            required_open_or_failed_gates: report.required_open_or_failed_gates,
            receipt_hash: report.receipt_hash
          }}));
        }})().catch((error) => {{ console.error(error); process.exitCode = 1; }});
        """
    )
    browser_report = json.loads(output)
    for key in (
        "integrity_valid",
        "promotion_allowed",
        "artifact_count",
        "artifact_hash_match_count",
        "required_open_or_failed_gates",
        "receipt_hash",
    ):
        assert browser_report[key] == python_report[key]


def test_python_and_browser_fail_closed_parity_for_non_object_receipts_and_rows():
    verifier = load_python_verifier()
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    malformed_artifacts = copy.deepcopy(sample)
    malformed_artifacts["artifacts"] = [None, "invalid", []]
    malformed_artifacts["receipt_sha256"] = verifier.stable_hash(
        verifier.receipt_payload(malformed_artifacts)
    )
    malformed_gates = copy.deepcopy(sample)
    malformed_gates["gates"] = [None, "invalid", []]
    malformed_gates["receipt_sha256"] = verifier.stable_hash(
        verifier.receipt_payload(malformed_gates)
    )
    receipts = [None, "invalid", [], malformed_artifacts, malformed_gates]

    comparable_keys = (
        "integrity_valid",
        "promotion_allowed",
        "artifact_count",
        "artifact_hash_match_count",
        "gate_counts",
        "required_open_or_failed_gates",
        "errors",
    )
    python_reports = [
        {key: verifier.verify_receipt(receipt)[key] for key in comparable_keys}
        for receipt in receipts
    ]

    output = run_node(
        f"""
        const fs = require("node:fs");
        const path = require("node:path");
        const core = require({json.dumps(js_path(CORE))});
        const root = {json.dumps(js_path(ROOT))};
        const receipts = {json.dumps(receipts)};
        const keys = {json.dumps(comparable_keys)};
        (async () => {{
          const reports = [];
          for (const receipt of receipts) {{
            const report = await core.verifyReceipt(receipt, {{
              loadArtifact: async (relative) => fs.readFileSync(path.join(root, relative))
            }});
            reports.push(Object.fromEntries(keys.map((key) => [key, report[key]])));
          }}
          console.log(JSON.stringify(reports));
        }})().catch((error) => {{ console.error(error); process.exitCode = 1; }});
        """
    )
    browser_reports = json.loads(output)

    assert browser_reports == python_reports
    assert all(report["integrity_valid"] is False for report in browser_reports)
    assert all(report["promotion_allowed"] is False for report in browser_reports)
    assert "receipt must be an object" in browser_reports[0]["errors"]
    assert "artifact row 0 must be an object" in browser_reports[3]["errors"]
    assert "gate row 0 must be an object" in browser_reports[4]["errors"]


def test_python_and_browser_promotion_decision_parity_with_all_required_gates_passed():
    verifier = load_python_verifier()
    receipts = []
    python_reports = []
    for decision in ("HOLD", "REJECT", "PROMOTE"):
        receipt = copy.deepcopy(json.loads(SAMPLE.read_text(encoding="utf-8")))
        for gate in receipt["gates"]:
            if gate.get("required_for_promotion"):
                gate["status"] = "PASS"
        receipt["decision"] = decision
        receipt["receipt_sha256"] = verifier.stable_hash(
            verifier.receipt_payload(receipt)
        )
        receipts.append(receipt)
        report = verifier.verify_receipt(receipt)
        python_reports.append(
            {
                "integrity_valid": report["integrity_valid"],
                "promotion_allowed": report["promotion_allowed"],
                "recorded_decision": report["recorded_decision"],
                "required_open_or_failed_gates": report[
                    "required_open_or_failed_gates"
                ],
            }
        )

    output = run_node(
        f"""
        const fs = require("node:fs");
        const path = require("node:path");
        const core = require({json.dumps(js_path(CORE))});
        const root = {json.dumps(js_path(ROOT))};
        const receipts = {json.dumps(receipts)};
        (async () => {{
          const reports = [];
          for (const receipt of receipts) {{
            const report = await core.verifyReceipt(receipt, {{
              loadArtifact: async (relative) => fs.readFileSync(path.join(root, relative))
            }});
            reports.push({{
              integrity_valid: report.integrity_valid,
              promotion_allowed: report.promotion_allowed,
              recorded_decision: report.recorded_decision,
              required_open_or_failed_gates: report.required_open_or_failed_gates
            }});
          }}
          console.log(JSON.stringify(reports));
        }})().catch((error) => {{ console.error(error); process.exitCode = 1; }});
        """
    )
    browser_reports = json.loads(output)

    assert browser_reports == python_reports
    assert [row["promotion_allowed"] for row in browser_reports] == [
        False,
        False,
        True,
    ]


def test_browser_path_allowlist_rejects_escape_forms():
    unsafe = [
        "../private.txt",
        "/private.txt",
        "C:/private.txt",
        "https://example.invalid/private.txt",
        "assets/%2e%2e/private.txt",
        "assets\\..\\private.txt",
    ]
    output = run_node(
        f"""
        const core = require({json.dumps(js_path(CORE))});
        const paths = {json.dumps(unsafe)};
        console.log(JSON.stringify(paths.map((value) => {{
          try {{ core.normalizeArtifactPath(value); return false; }} catch (_error) {{ return true; }}
        }})));
        """
    )
    assert all(json.loads(output))


def test_browser_artifact_urls_are_same_origin_and_allowlisted():
    output = run_node(
        f"""
        const core = require({json.dumps(js_path(CORE))});
        const target = core.resolveArtifactUrl("assets/hardware/example.json", "http://127.0.0.1:8088/build_week/prooflock_console/");
        console.log(JSON.stringify({{origin: target.origin, pathname: target.pathname}}));
        """
    )
    target = json.loads(output)
    assert target["origin"] == "http://127.0.0.1:8088"
    assert target["pathname"] == "/assets/hardware/example.json"


def test_console_has_no_remote_runtime_dependency():
    runtime_files = [
        APP_DIR / "index.html",
        APP_DIR / "bootstrap.js",
        APP_DIR / "app.js",
        APP_DIR / "prooflock_core.js",
        APP_DIR / "prooflock_lattice.js",
        APP_DIR / "styles.css",
        APP_DIR / "prooflock_lattice.css",
    ]
    remote_pattern = re.compile(r"\b(?:https?|wss?)://|[\"']\s*//|fonts\.googleapis|analytics", re.IGNORECASE)
    for path in runtime_files:
        assert not remote_pattern.search(path.read_text(encoding="utf-8")), path


def test_deployable_module_graph_is_self_contained():
    import_pattern = re.compile(r"(?:from|import\s*\()\s*[\"']([^\"']+)[\"']")
    pending = [APP_DIR / "bootstrap.js"]
    visited: set[Path] = set()

    while pending:
        source = pending.pop()
        assert source.is_file(), source
        if source in visited:
            continue
        visited.add(source)

        for specifier in import_pattern.findall(source.read_text(encoding="utf-8")):
            assert specifier.startswith("./"), (source, specifier)
            parsed = urlsplit(specifier)
            assert not parsed.scheme and not parsed.netloc and not parsed.fragment, (source, specifier)
            assert parsed.query == f"v={RELEASE_VERSION}", (source, specifier)
            dependency = (source.parent / parsed.path).resolve()
            assert dependency.is_relative_to(APP_DIR.resolve()), (source, specifier)
            assert dependency.is_file(), (source, specifier)
            if dependency.suffix == ".js":
                pending.append(dependency)

    assert APP_DIR / "three.module.min.js" in visited
    assert APP_DIR / "three.core.min.js" in visited
    assert (APP_DIR / "THREE_LICENSE.txt").is_file()
    canonical_three_module = (ROOT / "dashboard" / "assets" / "vendor" / "three.module.min.js").read_bytes()
    expected_three_module = canonical_three_module.replace(
        b'./three.core.min.js',
        f'./three.core.min.js?v={RELEASE_VERSION}'.encode("ascii"),
    )
    assert expected_three_module != canonical_three_module
    assert (APP_DIR / "three.module.min.js").read_bytes() == expected_three_module
    assert (APP_DIR / "three.core.min.js").read_bytes() == (
        ROOT / "dashboard" / "assets" / "vendor" / "three.core.min.js"
    ).read_bytes()


def test_accessibility_and_mobile_contract_is_present():
    html = (APP_DIR / "index.html").read_text(encoding="utf-8")
    styles = (APP_DIR / "styles.css").read_text(encoding="utf-8")
    lattice_styles = (APP_DIR / "prooflock_lattice.css").read_text(encoding="utf-8")
    assert 'aria-live="polite"' in html
    assert 'aria-hidden="true"' in html
    assert f'src="bootstrap.js?v={RELEASE_VERSION}" type="module"' in html
    assert ":focus-visible" in styles
    assert "overflow-x: clip" in styles
    assert "@media (max-width: 420px)" in lattice_styles
    assert "prefers-reduced-motion" in lattice_styles


def test_dynamic_display_strings_are_inserted_as_text():
    app = (APP_DIR / "app.js").read_text(encoding="utf-8")
    lattice = LATTICE.read_text(encoding="utf-8")
    assert ".innerHTML" not in app
    assert "insertAdjacentHTML" not in app
    assert ".innerHTML" not in lattice
    assert "textContent" in app


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"script", "img"} and values.get("src"):
            self.paths.append(values["src"])
        if tag == "link" and values.get("href"):
            self.paths.append(values["href"])


def test_html_script_style_and_image_paths_resolve_from_http_server_root():
    parser = AssetParser()
    parser.feed((APP_DIR / "index.html").read_text(encoding="utf-8"))
    assert parser.paths
    for relative in parser.paths:
        assert not relative.startswith(("http://", "https://", "//"))
        parsed = urlsplit(relative)
        assert not parsed.scheme and not parsed.netloc and not parsed.fragment, relative
        assert (APP_DIR / parsed.path).resolve().is_file(), relative
