import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_RELEASE_STEWARD_PLAN.py"


def load_module():
    spec = importlib.util.spec_from_file_location("release_steward_plan", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_parse_porcelain_z_handles_untracked_and_rename_entries():
    module = load_module()
    raw = b" M code/example.py\x00?? tests/new_test.py\x00R  docs/new.md\x00docs/old.md\x00"

    changes = module.parse_porcelain_v1_z(raw)

    assert [change.path for change in changes] == ["code/example.py", "tests/new_test.py", "docs/new.md"]
    assert changes[1].is_untracked is True
    assert changes[2].original_path == "docs/old.md"


def test_classification_keeps_private_and_generated_paths_out_of_auto_release():
    module = load_module()

    assert "PRIVATE_OR_CONTROLLED" in module.classify_path("grant_submissions/packet.docx")
    assert "GENERATED_ARTIFACT" in module.classify_path("out/ops/report.json")
    assert "TEMPORARY_OR_CACHE" in module.classify_path("tmp/vendor/node_modules/module.js")
    assert "SECRET_LIKE_FILENAME" in module.classify_path("config/service.pem")
    assert module.normalize_path(".github/workflows/check.yml") == ".github/workflows/check.yml"
    assert "DEPLOYMENT_OR_WORKFLOW" in module.classify_path(".github/workflows/check.yml")


def test_plan_groups_bounded_source_separately_from_private_and_deploy_paths(tmp_path: Path):
    module = load_module()
    (tmp_path / "code").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "deploy").mkdir()
    (tmp_path / "grant_submissions").mkdir()
    (tmp_path / "code" / "feature.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "code" / "recipient.py").write_text(
        "RECIPIENT = 'reviewer@example.org'\n", encoding="utf-8"
    )
    (tmp_path / "tests" / "test_feature.py").write_text("def test_value():\n    assert True\n", encoding="utf-8")
    (tmp_path / "deploy" / "service.conf").write_text("server {}\n", encoding="utf-8")
    (tmp_path / "grant_submissions" / "draft.md").write_text("private scope\n", encoding="utf-8")
    changes = [
        module.WorktreeChange(" ", "M", "code/feature.py"),
        module.WorktreeChange(" ", "M", "code/recipient.py"),
        module.WorktreeChange("?", "?", "tests/test_feature.py"),
        module.WorktreeChange(" ", "M", "deploy/service.conf"),
        module.WorktreeChange("?", "?", "grant_submissions/draft.md"),
    ]

    plan = module.build_plan_from_changes(
        tmp_path,
        changes,
        generated_utc="2026-08-03T20:00:00Z",
        diff_check_passed=True,
    )

    states = {row["path"]: row["review_state"] for row in plan["changes"]}
    assert states["code/feature.py"] == "BOUNDED_COMMIT_CANDIDATE"
    assert states["code/recipient.py"] == "HUMAN_SCOPE_REVIEW_REQUIRED"
    assert states["tests/test_feature.py"] == "BOUNDED_COMMIT_CANDIDATE"
    assert states["deploy/service.conf"] == "HUMAN_SCOPE_REVIEW_REQUIRED"
    assert states["grant_submissions/draft.md"] == "EXCLUDE_FROM_AUTOMATIC_RELEASE"
    assert plan["authority"]["commit_authorized_by_plan"] is False
    assert len(plan["plan_sha256"]) == 64
