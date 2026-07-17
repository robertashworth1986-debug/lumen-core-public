from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "INSTALL_SAM_PUBLIC_CREDENTIAL.py"


def load_module():
    spec = importlib.util.spec_from_file_location("install_sam_public_api_key", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rewrite_normalizes_all_aliases_and_preserves_unrelated_content():
    module = load_module()
    replacement = "A1b2C3d4E5f6G7h8I9j0-K_l.M~n"
    original = (
        "# private provider keys\n"
        "UNRELATED_TOKEN=keep-me\n"
        "SAM_API_KEY=old-value-one\n"
        "SAM_API_KEY=stale-duplicate\n"
        "export SAM_GOV_API_KEY =old-value-two\n"
    )

    rewritten, details = module.rewrite_env_text(original, replacement)

    assert "# private provider keys" in rewritten
    assert "UNRELATED_TOKEN=keep-me" in rewritten
    assert rewritten.count(f"SAM_API_KEY={replacement}") == 1
    assert rewritten.count(f"export SAM_GOV_API_KEY ={replacement}") == 1
    assert rewritten.count(f"DATA_GOV_API_KEY_PRIMARY={replacement}") == 1
    assert "old-value" not in rewritten
    assert "stale-duplicate" not in rewritten
    assert details["previous_alias_occurrences"] == 3
    assert details["final_alias_occurrences"] == 3
    assert details["duplicate_aliases_removed"] == 1


@pytest.mark.parametrize(
    "replacement,error_code",
    [
        ("", "EMPTY_REPLACEMENT"),
        (" short-key ", "REPLACEMENT_CONTAINS_WHITESPACE"),
        ("short-key", "REPLACEMENT_FORMAT_REJECTED"),
        ("your-sam-api-key-placeholder", "PLACEHOLDER_REPLACEMENT_REJECTED"),
        ("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "PLACEHOLDER_REPLACEMENT_REJECTED"),
    ],
)
def test_rejects_unsafe_or_placeholder_replacements(replacement: str, error_code: str):
    module = load_module()

    with pytest.raises(module.InstallError) as error:
        module.validate_replacement(replacement)

    assert error.value.code == error_code
    if replacement:
        assert replacement not in str(error.value)


def test_install_is_atomic_secret_safe_and_updates_all_aliases(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    target = root / "private" / "luma_live_keys.env"
    target.parent.mkdir(parents=True)
    target.write_text("# keep\nOTHER=value\nSAM_API_KEY=old-old-old-old\n", encoding="utf-8")
    replacement = "9F8e7D6c5B4a3Z2y1X0w-V_u.T~s"

    receipt = module.install_replacement(
        replacement,
        target=target,
        root=root,
        ignored_checker=lambda _path: True,
    )

    persisted = target.read_text(encoding="utf-8")
    assert persisted.startswith("# keep\nOTHER=value\n")
    assert persisted.count(replacement) == 3
    assert module.assignment_counts(persisted) == {
        "SAM_API_KEY": 1,
        "SAM_GOV_API_KEY": 1,
        "DATA_GOV_API_KEY_PRIMARY": 1,
    }
    public_receipt = json.dumps(receipt, sort_keys=True)
    assert replacement not in public_receipt
    assert receipt["target_git_ignored"] is True
    assert receipt["atomic_replace_completed"] is True
    assert receipt["plaintext_backup_created"] is False
    assert receipt["aliases_consistent"] is True
    assert receipt["secret_value_printed"] is False
    assert receipt["secret_hash_printed"] is False


def test_refuses_nonignored_target_before_read_or_write(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    target = root / "tracked.env"
    root.mkdir()
    target.write_text("SAM_API_KEY=original-original\n", encoding="utf-8")

    with pytest.raises(module.InstallError) as error:
        module.install_replacement(
            "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6",
            target=target,
            root=root,
            ignored_checker=lambda _path: False,
        )

    assert error.value.code == "TARGET_NOT_GIT_IGNORED"
    assert target.read_text(encoding="utf-8") == "SAM_API_KEY=original-original\n"


def test_atomic_replace_failure_leaves_original_unchanged(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    target = root / "private" / "keys.env"
    target.parent.mkdir(parents=True)
    original = "SAM_API_KEY=original-original\n"
    target.write_text(original, encoding="utf-8")

    def fail_replace(_source, _destination):
        raise OSError("simulated replace failure")

    with pytest.raises(module.InstallError) as error:
        module.install_replacement(
            "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6",
            target=target,
            root=root,
            ignored_checker=lambda _path: True,
            replacer=fail_replace,
        )

    assert error.value.code == "ATOMIC_REPLACE_FAILED"
    assert target.read_text(encoding="utf-8") == original
    assert list(target.parent.glob(".sam-key-install-*.tmp")) == []


def test_target_readiness_contains_metadata_only(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    target = root / "private" / "keys.env"
    target.parent.mkdir(parents=True)
    secret = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"
    target.write_text(f"SAM_API_KEY={secret}\n", encoding="utf-8")

    readiness = module.inspect_target(
        target,
        root=root,
        ignored_checker=lambda _path: True,
    )

    assert readiness["status"] == "READY_FOR_HIDDEN_REPLACEMENT_INPUT"
    assert readiness["configured_alias_occurrences"] == 1
    assert readiness["private_file_content_parsed_locally"] is True
    assert readiness["secret_value_returned_or_printed"] is False
    assert secret not in json.dumps(readiness, sort_keys=True)
