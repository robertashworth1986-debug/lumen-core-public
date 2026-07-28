from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "lumencore.bounded_deployment_scope.v1"
SCOPE_NAMES = ("site", "gateway", "evidence")

GATEWAY_PATHS = {
    "code/booth_public_contract.py",
    "code/luma_experience_gateway.py",
    "code/luma_experience_gateway_legacy.py",
    "code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh",
}
EVIDENCE_PATHS = {
    "code/deploy/nginx/lumatrader.conf",
    "code/ops/REPAIR_PUBLIC_EDGE_ON_VPS.sh",
    "code/ops/REPAIR_EVIDENCE_ROUTE_ON_VPS.sh",
    "code/ops/repair_public_edge.py",
    "code/ops/repair_evidence_route.py",
}
CONTROL_PATHS = {
    ".github/workflows/deploy.yml",
    "code/ops/classify_bounded_deployment_scope.py",
}

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


def normalize_repo_path(value: str) -> str:
    path = str(value or "").strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    parts = path.split("/")
    if (
        not path
        or path.startswith("/")
        or _WINDOWS_DRIVE.match(path)
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise ValueError(f"path must be a normalized repository-relative path: {value!r}")
    return path


def _is_site_path(path: str) -> bool:
    if path.startswith("dashboard/") and path.endswith((".html", ".js", ".css")):
        return True
    if path.startswith("dashboard/") and path.count("/") == 1 and path.endswith(".json"):
        return True
    if path.startswith("data/") and path.count("/") == 1 and path.endswith(".json"):
        return True
    return False


def classify_deployment_scope(
    *,
    mode: str,
    changed_paths: Iterable[str] = (),
    manual_scopes: Iterable[str] = (),
) -> dict[str, Any]:
    if mode not in {"push", "manual"}:
        raise ValueError("mode must be push or manual")

    normalized_paths = sorted({normalize_repo_path(path) for path in changed_paths})
    normalized_manual = sorted({str(scope).strip().lower() for scope in manual_scopes})
    invalid_scopes = [scope for scope in normalized_manual if scope not in SCOPE_NAMES]
    if invalid_scopes:
        raise ValueError(f"unsupported manual scope: {invalid_scopes[0]}")
    if mode == "push" and normalized_manual:
        raise ValueError("push mode cannot declare manual scopes")
    if mode == "manual" and normalized_paths:
        raise ValueError("manual mode cannot declare changed paths")

    selected = {scope: False for scope in SCOPE_NAMES}
    control_paths: list[str] = []
    ignored_paths: list[str] = []

    if mode == "manual":
        for scope in normalized_manual:
            selected[scope] = True
    else:
        for path in normalized_paths:
            if _is_site_path(path):
                selected["site"] = True
            elif path in GATEWAY_PATHS:
                selected["gateway"] = True
            elif path in EVIDENCE_PATHS:
                selected["evidence"] = True
            elif path in CONTROL_PATHS:
                control_paths.append(path)
            else:
                ignored_paths.append(path)

    selected_names = [scope for scope in SCOPE_NAMES if selected[scope]]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": mode,
        "changed_paths": normalized_paths,
        "manual_scopes": normalized_manual,
        "control_paths": control_paths,
        "ignored_paths": ignored_paths,
        "site_changed": selected["site"],
        "gateway_changed": selected["gateway"],
        "evidence_changed": selected["evidence"],
        "mutation_requested": bool(selected_names),
        "scope_summary": ",".join(selected_names) if selected_names else "inspect_only",
    }
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    payload["classification_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def _read_changed_paths(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_github_output(path: Path, payload: dict[str, Any]) -> None:
    keys = ("site_changed", "gateway_changed", "evidence_changed", "mutation_requested")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key in keys:
            handle.write(f"{key}={str(bool(payload[key])).lower()}\n")
        handle.write(f"scope_summary={payload['scope_summary']}\n")
        handle.write(f"classification_sha256={payload['classification_sha256']}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify a bounded LumenCore production deployment scope."
    )
    parser.add_argument("--mode", choices=("push", "manual"), required=True)
    parser.add_argument("--changed-path-file", type=Path)
    parser.add_argument("--manual-scope", action="append", default=[], choices=SCOPE_NAMES)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--github-output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "push" and args.changed_path_file is None:
        raise SystemExit("push mode requires --changed-path-file")
    if args.mode == "manual" and args.changed_path_file is not None:
        raise SystemExit("manual mode does not accept --changed-path-file")

    changed_paths = _read_changed_paths(args.changed_path_file) if args.changed_path_file else []
    payload = classify_deployment_scope(
        mode=args.mode,
        changed_paths=changed_paths,
        manual_scopes=args.manual_scope,
    )
    rendered = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    if args.github_output:
        _write_github_output(args.github_output, payload)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
