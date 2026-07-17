from __future__ import annotations

import argparse
import getpass
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = Path(__file__).with_name("VALIDATE_NASHVILLE_EC_PRIVATE_FACTS.py")
PRIVATE_DIR = ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026" / "private"
DEFAULT_OUTPUT = PRIVATE_DIR / "nashville_ec_portal_fill_map.private.json"

BUSINESS_AGE_OPTIONS = (
    "Not yet started",
    "Less than 6 months",
    "6 to 12 months",
    "1 to 3 years",
    "3+ years",
)
WEEKLY_HOURS_OPTIONS = ("Less than 10", "10-20", "20-30", "30+")
CONVERSATION_OPTIONS = ("0", "1 to 10", "11 to 25", "26 to 50", "50+")
FINANCIAL_PROMPTS = (
    ("previous_year_revenue_usd", "Previous-year revenue"),
    ("trailing_12_month_revenue_usd", "Trailing-12-month revenue"),
    ("grant_funds_received_usd", "Grant funds received"),
    ("investor_capital_received_usd", "Investor capital received"),
)


class CaptureError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "nashville_ec_private_fact_validator", VALIDATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Nashville EC private-fact validator could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator()


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def git_ignored(path: Path, *, root: Path = ROOT) -> bool:
    if not path_is_within(path, root):
        return False
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", relative],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def validate_private_target(
    target: Path,
    *,
    root: Path = ROOT,
    private_dir: Path = PRIVATE_DIR,
    ignored_checker: Callable[[Path], bool] | None = None,
) -> Path:
    if target.is_symlink():
        raise CaptureError("SYMLINK_TARGET_REJECTED")
    resolved = target.resolve()
    if not path_is_within(resolved, root):
        raise CaptureError("TARGET_OUTSIDE_REPOSITORY")
    if not path_is_within(resolved, private_dir):
        raise CaptureError("TARGET_OUTSIDE_PRIVATE_DIRECTORY")
    if resolved.exists() and not resolved.is_file():
        raise CaptureError("TARGET_NOT_REGULAR_FILE")
    checker = ignored_checker or (lambda path: git_ignored(path, root=root))
    if not checker(resolved):
        raise CaptureError("TARGET_NOT_GIT_IGNORED")
    return resolved


def choose_option(
    label: str,
    options: tuple[str, ...],
    *,
    prompt: Callable[[str], str],
) -> str:
    menu = "\n".join(f"  {index}. {option}" for index, option in enumerate(options, 1))
    while True:
        raw = prompt(f"{label}\n{menu}\nSelection number (hidden): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print(f"Invalid selection. Enter a number from 1 to {len(options)}.")


def choose_bool(label: str, *, prompt: Callable[[str], str]) -> bool:
    while True:
        raw = prompt(f"{label} [Y/N] (hidden): ").strip().lower()
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Invalid selection. Enter Y or N.")


def choose_usd(label: str, *, prompt: Callable[[str], str]) -> str:
    while True:
        raw = prompt(f"{label} in USD (hidden; 0 is allowed): ").strip()
        try:
            amount = VALIDATOR.parse_usd(raw, label)
        except ValueError:
            print("Invalid amount. Enter a nonnegative USD amount with at most two decimals.")
            continue
        return format(amount, "f")


def collect_private_facts(
    *, prompt: Callable[[str], str] = getpass.getpass
) -> dict[str, Any]:
    first_time = choose_bool("Are you a first-time founder?", prompt=prompt)
    business_age = choose_option(
        "How long have you been working on this business?",
        BUSINESS_AGE_OPTIONS,
        prompt=prompt,
    )
    full_time = choose_bool("Are you working on LumenCore full-time?", prompt=prompt)
    weekly_hours = choose_option(
        "Hours per week actively working on LumenCore",
        WEEKLY_HOURS_OPTIONS,
        prompt=prompt,
    )
    conversations = choose_option(
        "Genuine customer-discovery or sales conversations completed",
        CONVERSATION_OPTIONS,
        prompt=prompt,
    )
    zero_financials = choose_bool(
        "Are previous-year revenue, trailing-12-month revenue, grants received, and investor capital all $0?",
        prompt=prompt,
    )
    financials = None
    if not zero_financials:
        financials = {
            key: choose_usd(label, prompt=prompt)
            for key, label in FINANCIAL_PROMPTS
        }
    founder_cash = choose_usd(
        "Total founder cash invested in the business", prompt=prompt
    )
    business_debt = choose_usd("Business debt leveraged to date", prompt=prompt)

    return {
        "schema": VALIDATOR.SCHEMA,
        "first_time_founder": first_time,
        "business_age": business_age,
        "full_time_on_lumencore": full_time,
        "weekly_hours_bracket": weekly_hours,
        "conversation_bracket": conversations,
        "zero_financials_confirmed": zero_financials,
        "financial_amounts_usd": financials,
        "founder_cash_invested_usd": founder_cash,
        "business_debt_usd": business_debt,
    }


def atomic_write_json(
    target: Path,
    payload: dict[str, Any],
    *,
    replacer: Callable[[str | bytes | os.PathLike[str], str | bytes | os.PathLike[str]], None]
    | None = None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    replace = replacer or os.replace
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=".nashville-ec-private-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        replace(temporary_path, target)
        temporary_path = None
    except OSError as exc:
        raise CaptureError("ATOMIC_PRIVATE_WRITE_FAILED") from exc
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def capture_private_fill_map(
    *,
    prompt: Callable[[str], str] = getpass.getpass,
    target: Path = DEFAULT_OUTPUT,
    root: Path = ROOT,
    private_dir: Path = PRIVATE_DIR,
    ignored_checker: Callable[[Path], bool] | None = None,
    replacer: Callable[[str | bytes | os.PathLike[str], str | bytes | os.PathLike[str]], None]
    | None = None,
    replace_existing: bool = False,
) -> dict[str, Any]:
    destination = validate_private_target(
        target,
        root=root,
        private_dir=private_dir,
        ignored_checker=ignored_checker,
    )
    if destination.exists() and not replace_existing:
        raise CaptureError("PRIVATE_FILL_MAP_ALREADY_EXISTS")
    private_facts = collect_private_facts(prompt=prompt)
    fill_map = VALIDATOR.validate_private_facts(private_facts)
    atomic_write_json(destination, fill_map, replacer=replacer)

    return {
        "schema": "lumencore.nashville_ec_private_capture_receipt.v1",
        "status": "PRIVATE_PORTAL_FILL_MAP_CAPTURED",
        "question_answer_count": fill_map["question_answer_count"],
        "output": destination.relative_to(root.resolve()).as_posix(),
        "target_git_ignored": True,
        "atomic_write_completed": True,
        "source_fact_file_created": False,
        "private_values_returned_or_printed": False,
        "private_values_written_to_public_artifact": False,
        "browser_navigation_performed": False,
        "portal_submission_performed": False,
        "final_submission_authorized": False,
        "next_action": (
            "Use the private eleven-answer map in the live Nashville EC portal, review the complete "
            "preview plus any fee or terms, and obtain action-time approval before final submission."
        ),
    }


def inspect_readiness(
    target: Path = DEFAULT_OUTPUT,
    *,
    root: Path = ROOT,
    private_dir: Path = PRIVATE_DIR,
    ignored_checker: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    destination = validate_private_target(
        target,
        root=root,
        private_dir=private_dir,
        ignored_checker=ignored_checker,
    )
    return {
        "schema": "lumencore.nashville_ec_private_capture_readiness.v1",
        "status": "READY_FOR_HIDDEN_FOUNDER_INPUT",
        "output": destination.relative_to(root.resolve()).as_posix(),
        "output_exists": destination.exists(),
        "target_git_ignored": True,
        "answer_values_read_or_printed": False,
        "browser_navigation_performed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture Nashville EC founder facts through hidden prompts and write one private fill map."
    )
    parser.add_argument(
        "--check-target",
        action="store_true",
        help="Validate the ignored private output without requesting or writing founder facts",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace an existing private fill map after collecting all answers again",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.check_target:
            receipt = inspect_readiness()
        else:
            receipt = capture_private_fill_map(
                replace_existing=args.replace_existing
            )
        print(json.dumps(receipt, indent=2, sort_keys=True))
    except CaptureError as exc:
        print(
            json.dumps(
                {
                    "status": "PRIVATE_CAPTURE_NOT_COMPLETED",
                    "error_code": exc.code,
                    "private_values_returned_or_printed": False,
                    "browser_navigation_performed": False,
                    "portal_submission_performed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
