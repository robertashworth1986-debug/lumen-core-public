from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "capture_nashville_ec_private_facts", SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prompt_from(values: list[str]):
    remaining = list(values)

    def prompt(_message: str) -> str:
        assert remaining, "collector requested an unexpected extra answer"
        return remaining.pop(0)

    prompt.remaining = remaining
    return prompt


def zero_fact_answers() -> list[str]:
    return [
        "y",  # first-time founder
        "4",  # 1 to 3 years
        "y",  # full-time
        "4",  # 30+
        "2",  # 1 to 10 conversations
        "y",  # all four financial fields are zero
        "40",  # founder cash
        "0",  # business debt
    ]


def test_hidden_collector_builds_validator_compatible_zero_fact_payload():
    module = load_module()
    prompt = prompt_from(zero_fact_answers())

    private_facts = module.collect_private_facts(prompt=prompt)
    fill_map = module.VALIDATOR.validate_private_facts(private_facts)
    answers = {row["question_id"]: row["value"] for row in fill_map["question_answers"]}

    assert prompt.remaining == []
    assert private_facts["schema"] == module.VALIDATOR.SCHEMA
    assert private_facts["financial_amounts_usd"] is None
    assert answers[38] == "Yes"
    assert answers[31] == "1 to 3 years"
    assert answers[29] == "30+"
    assert answers[84] == "1 to 10"
    assert answers[62] == "$40"
    assert all(answers[question_id] == "$0" for question_id in (36, 63, 64, 65, 66))


def test_nonzero_path_collects_exactly_four_financial_amounts():
    module = load_module()
    prompt = prompt_from(
        [
            "n",
            "4",
            "n",
            "3",
            "3",
            "n",
            "1250.50",
            "0",
            "500",
            "0",
            "40",
            "25",
        ]
    )

    private_facts = module.collect_private_facts(prompt=prompt)
    fill_map = module.VALIDATOR.validate_private_facts(private_facts)
    answers = {row["question_id"]: row["value"] for row in fill_map["question_answers"]}

    assert prompt.remaining == []
    assert private_facts["zero_financials_confirmed"] is False
    assert set(private_facts["financial_amounts_usd"]) == {
        "previous_year_revenue_usd",
        "trailing_12_month_revenue_usd",
        "grant_funds_received_usd",
        "investor_capital_received_usd",
    }
    assert answers[66] == "$1250.50"
    assert answers[63] == "$500"
    assert answers[65] == "$25"


def test_invalid_hidden_answers_retry_without_entering_the_payload(capsys):
    module = load_module()
    prompt = prompt_from(
        [
            "maybe",
            "y",
            "99",
            "4",
            "y",
            "4",
            "2",
            "y",
            "-5",
            "40",
            "0",
        ]
    )

    private_facts = module.collect_private_facts(prompt=prompt)
    output = capsys.readouterr().out

    assert prompt.remaining == []
    assert private_facts["first_time_founder"] is True
    assert private_facts["business_age"] == "1 to 3 years"
    assert private_facts["founder_cash_invested_usd"] == "40"
    assert "Invalid selection" in output
    assert "Invalid amount" in output
    assert "-5" not in output


def test_capture_writes_one_ignored_private_map_and_returns_metadata_only(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "grant_submissions" / "NASHVILLE_EC_FALL_2026" / "private"
    target = private_dir / "nashville_ec_portal_fill_map.private.json"
    prompt = prompt_from(zero_fact_answers())

    receipt = module.capture_private_fill_map(
        prompt=prompt,
        target=target,
        root=root,
        private_dir=private_dir,
        ignored_checker=lambda _path: True,
    )

    private_map = json.loads(target.read_text(encoding="utf-8"))
    answers = {row["question_id"]: row["value"] for row in private_map["question_answers"]}
    serialized_receipt = json.dumps(receipt, sort_keys=True)
    assert private_map["status"] == "VALIDATED_PRIVATE_PORTAL_FILL_MAP"
    assert answers[62] == "$40"
    assert receipt["status"] == "PRIVATE_PORTAL_FILL_MAP_CAPTURED"
    assert receipt["question_answer_count"] == 11
    assert receipt["target_git_ignored"] is True
    assert receipt["atomic_write_completed"] is True
    assert receipt["source_fact_file_created"] is False
    assert receipt["private_values_returned_or_printed"] is False
    assert receipt["portal_submission_performed"] is False
    assert "$40" not in serialized_receipt
    assert module.VALIDATOR.stable_hash(private_map) not in serialized_receipt


def test_existing_private_map_fails_before_requesting_answers(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "private"
    private_dir.mkdir(parents=True)
    target = private_dir / "fill.private.json"
    target.write_text('{"existing":true}\n', encoding="utf-8")

    def unexpected_prompt(_message: str) -> str:
        raise AssertionError("answers must not be requested before the overwrite gate")

    with pytest.raises(module.CaptureError) as error:
        module.capture_private_fill_map(
            prompt=unexpected_prompt,
            target=target,
            root=root,
            private_dir=private_dir,
            ignored_checker=lambda _path: True,
        )

    assert error.value.code == "PRIVATE_FILL_MAP_ALREADY_EXISTS"
    assert target.read_text(encoding="utf-8") == '{"existing":true}\n'


def test_atomic_failure_leaves_no_partial_private_map(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "private"
    target = private_dir / "fill.private.json"

    def fail_replace(_source, _destination):
        raise OSError("simulated replace failure")

    with pytest.raises(module.CaptureError) as error:
        module.capture_private_fill_map(
            prompt=prompt_from(zero_fact_answers()),
            target=target,
            root=root,
            private_dir=private_dir,
            ignored_checker=lambda _path: True,
            replacer=fail_replace,
        )

    assert error.value.code == "ATOMIC_PRIVATE_WRITE_FAILED"
    assert not target.exists()
    assert list(private_dir.glob(".nashville-ec-private-*.tmp")) == []


def test_public_or_nonignored_targets_fail_closed(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "private"
    public_target = root / "public" / "facts.json"
    private_target = private_dir / "facts.private.json"

    with pytest.raises(module.CaptureError) as outside_private:
        module.validate_private_target(
            public_target,
            root=root,
            private_dir=private_dir,
            ignored_checker=lambda _path: True,
        )
    with pytest.raises(module.CaptureError) as not_ignored:
        module.validate_private_target(
            private_target,
            root=root,
            private_dir=private_dir,
            ignored_checker=lambda _path: False,
        )

    assert outside_private.value.code == "TARGET_OUTSIDE_PRIVATE_DIRECTORY"
    assert not_ignored.value.code == "TARGET_NOT_GIT_IGNORED"


def test_readiness_is_metadata_only_even_when_private_map_exists(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "private"
    private_dir.mkdir(parents=True)
    target = private_dir / "fill.private.json"
    marker = "private-founder-value-marker"
    target.write_text(marker, encoding="utf-8")

    readiness = module.inspect_readiness(
        target,
        root=root,
        private_dir=private_dir,
        ignored_checker=lambda _path: True,
    )

    assert readiness["status"] == "READY_FOR_HIDDEN_FOUNDER_INPUT"
    assert readiness["output_exists"] is True
    assert readiness["answer_values_read_or_printed"] is False
    assert marker not in json.dumps(readiness, sort_keys=True)
