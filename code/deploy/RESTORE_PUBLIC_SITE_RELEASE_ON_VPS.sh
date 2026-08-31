#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

readonly REQUIRED_APPROVAL="DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT"
readonly PRODUCTION_TARGET="/opt/lumencore/dashboard"
readonly PRODUCTION_ROLLBACK_BASE="/opt/lumencore/rollbacks/public-site"
readonly EXPECTED_TARGET_DIRECTORY="/opt/lumencore/dashboard"
readonly MANIFEST_SCHEMA="lumencore.public_site_release_manifest.v1"
readonly ROLLBACK_AUTHORITY_SCHEMA="lumencore.public_site_same_run_rollback_authority.v1"
readonly COMPENSATION_RECEIPT_SCHEMA="lumencore.public_site_same_run_compensation.v1"
readonly LIVE_GATE_SCHEMA="lumencore.public_site_live_verification.v1"
readonly REPOSITORY="robertashworth1986-debug/lumen-core-public"
readonly WORKFLOW=".github/workflows/deploy-public-site-release.yml"
readonly AUTHORITY_SCOPE="FAILED_EXTERNAL_LIVE_GATE_COMPENSATION_IN_SAME_WORKFLOW_RUN_ONLY"
readonly -a RELEASE_FILES=(
  "operator_home.html"
  "opportunity_sprint.html"
  "proof_to_pilot.html"
  "external_review.html"
  "reviewer_docket.json"
  "mission_control.html"
  "quant_lab.html"
  "grants.html"
  "kraken_execution_dashboard.html"
  "forecast.html"
  "anomalies.html"
  "explain.html"
  "lab.html"
  "evidence/index_bounded.html"
  "robots.txt"
  "sitemap.xml"
  "site.webmanifest"
  "manifest.json"
  "assets/lumaarc_arc_seal_v1.png"
  "assets/lumencore.css"
  "assets/lumencore.js"
  "assets/luma_command_fabric.css"
  "assets/luma_command_fabric.js"
  "assets/luma_institutional_surface.css"
  "assets/luma_institutional_surface.js"
  "assets/vendor/three.min.js"
  "js/alpha_globe_3d.js"
  "js/cinematic_telemetry_layer.js"
  "js/luma_design_system.js"
  "js/luma_path_resolver.js"
  "assets/prooflock/bounded_validation_protocol_v1.json"
  "assets/prooflock/bounded_validation_protocol_v2.json"
  "build_week/prooflock_console/app.js"
  "build_week/prooflock_console/bootstrap.js"
  "build_week/prooflock_console/index.html"
  "build_week/prooflock_console/prooflock_core.js"
  "build_week/prooflock_console/prooflock_favicon.svg"
  "build_week/prooflock_console/prooflock_lattice.css"
  "build_week/prooflock_console/prooflock_lattice.js"
  "build_week/prooflock_console/sample_receipt.json"
  "build_week/prooflock_console/styles.css"
  "build_week/prooflock_console/three.core.min.js"
  "build_week/prooflock_console/three.module.min.js"
)
readonly -a RELEASE_DIRECTORIES=(
  "assets"
  "assets/vendor"
  "assets/prooflock"
  "js"
  "evidence"
  "build_week"
  "build_week/prooflock_console"
)
readonly EXPECTED_FILE_COUNT="${#RELEASE_FILES[@]}"

rollback_dir=""
source_commit=""
run_id=""
run_attempt=""
approval=""
capability_stdin=0
trigger=""
live_gate_receipt=""

die() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

usage() {
  cat >&2 <<'EOF'
Usage: RESTORE_PUBLIC_SITE_RELEASE_ON_VPS.sh \
  --rollback-dir PATH --source-commit FULL_SHA \
  --run-id POSITIVE_INTEGER --run-attempt POSITIVE_INTEGER \
  --rollback-capability-stdin \
  --trigger LIVE_GATE_REJECTED|LIVE_GATE_ERROR_OR_MISSING \
  [--live-gate-receipt PATH] \
  --approval DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT
EOF
  return 2
}

while (($#)); do
  case "$1" in
    --rollback-dir)
      (($# >= 2)) || usage
      rollback_dir="$2"
      shift 2
      ;;
    --source-commit)
      (($# >= 2)) || usage
      source_commit="$2"
      shift 2
      ;;
    --run-id)
      (($# >= 2)) || usage
      run_id="$2"
      shift 2
      ;;
    --run-attempt)
      (($# >= 2)) || usage
      run_attempt="$2"
      shift 2
      ;;
    --rollback-capability-stdin)
      capability_stdin=1
      shift
      ;;
    --trigger)
      (($# >= 2)) || usage
      trigger="$2"
      shift 2
      ;;
    --live-gate-receipt)
      (($# >= 2)) || usage
      live_gate_receipt="$2"
      shift 2
      ;;
    --approval)
      (($# >= 2)) || usage
      approval="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

[[ "$approval" == "$REQUIRED_APPROVAL" ]] || die "exact-snapshot approval is required for same-transaction compensation"
[[ "$source_commit" =~ ^[0-9a-f]{40}$ ]] || die "source commit must be a full lowercase SHA-1"
[[ "$run_id" =~ ^[1-9][0-9]*$ ]] || die "run ID must be a positive integer"
[[ "$run_attempt" =~ ^[1-9][0-9]*$ ]] || die "run attempt must be a positive integer"
[[ "$capability_stdin" -eq 1 ]] || die "rollback capability must be supplied through standard input"
[[ "$trigger" == "LIVE_GATE_REJECTED" || "$trigger" == "LIVE_GATE_ERROR_OR_MISSING" ]] || \
  die "compensation trigger is invalid"
if [[ "$trigger" == "LIVE_GATE_REJECTED" ]]; then
  [[ -n "$live_gate_receipt" && -f "$live_gate_receipt" && ! -L "$live_gate_receipt" ]] || \
    die "a regular live-gate receipt is required for a rejected gate"
else
  [[ -z "$live_gate_receipt" ]] || die "a live-gate receipt is forbidden when the gate receipt is absent"
fi
[[ "$rollback_dir" == /* && "$rollback_dir" != "/" ]] || die "rollback directory must be a non-root absolute path"

test_mode=0
before_target_hook="${PUBLIC_SITE_DEPLOY_TEST_BEFORE_TARGET_HOOK:-}"
if [[ "${PUBLIC_SITE_DEPLOY_TEST_MODE:-}" == "1" ]]; then
  [[ "$EUID" -ne 0 ]] || die "test mode is forbidden for root"
  [[ -n "${PUBLIC_SITE_DEPLOY_TEST_ROOT:-}" ]] || die "test mode requires PUBLIC_SITE_DEPLOY_TEST_ROOT"
  [[ "$PUBLIC_SITE_DEPLOY_TEST_ROOT" == /* && "$PUBLIC_SITE_DEPLOY_TEST_ROOT" != "/" ]] || \
    die "test root must be a non-root absolute path"
  target_root="$PUBLIC_SITE_DEPLOY_TEST_ROOT/opt/lumencore/dashboard"
  rollback_base="$PUBLIC_SITE_DEPLOY_TEST_ROOT/opt/lumencore/rollbacks/public-site"
  if [[ -n "$before_target_hook" ]]; then
    [[ "$before_target_hook" == /* && -f "$before_target_hook" && ! -L "$before_target_hook" && -x "$before_target_hook" ]] || \
      die "test hook must be an absolute executable regular file"
    [[ "$(stat -c '%u' -- "$before_target_hook")" == "$EUID" ]] || die "test hook owner is invalid"
  fi
  test_mode=1
else
  [[ -z "${PUBLIC_SITE_DEPLOY_TEST_ROOT:-}" ]] || die "test root is forbidden outside test mode"
  [[ -z "$before_target_hook" ]] || die "test hook is forbidden outside test mode"
  [[ "$EUID" -eq 0 ]] || die "production restore must run as root"
  target_root="$PRODUCTION_TARGET"
  rollback_base="$PRODUCTION_ROLLBACK_BASE"
fi

for command_name in python3 sha256sum stat cp chmod chown mv rm rmdir mktemp realpath dirname basename flock; do
  command -v "$command_name" >/dev/null 2>&1 || die "missing required command: $command_name"
done
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' || \
  die "python3 3.9 or newer is required"

rollback_capability=""
IFS= read -r rollback_capability || [[ -n "$rollback_capability" ]] || \
  die "rollback capability could not be read from standard input"
[[ "$rollback_capability" =~ ^[0-9a-f]{64}$ ]] || die "rollback capability must be 256 bits encoded as lowercase hex"
rollback_capability_sha256="$(printf '%s' "$rollback_capability" | sha256sum)"
rollback_capability_sha256="${rollback_capability_sha256%% *}"
rollback_capability=""
[[ "$rollback_capability_sha256" =~ ^[0-9a-f]{64}$ ]] || die "rollback capability digest is invalid"

[[ -d "$target_root" && ! -L "$target_root" ]] || die "dashboard root must be a real directory"
[[ "$(realpath -m -- "$target_root")" == "$target_root" ]] || die "dashboard root cannot traverse a symlink"
[[ -d "$rollback_base" && ! -L "$rollback_base" ]] || die "rollback base must be a real directory"
[[ "$(realpath -m -- "$rollback_base")" == "$rollback_base" ]] || die "rollback base cannot traverse a symlink"
read -r rollback_base_uid rollback_base_mode < <(stat -c '%u %a' -- "$rollback_base")
[[ "$rollback_base_uid" == "$EUID" && "$rollback_base_mode" == "750" ]] || \
  die "rollback base identity is invalid"
lock_path="$rollback_base/.deployment.lock"
[[ "$(realpath -m -- "$lock_path")" == "$lock_path" ]] || die "deployment lock path cannot traverse a symlink"
[[ -f "$lock_path" && ! -L "$lock_path" ]] || die "deployment lock must be a regular file"
read -r lock_uid lock_mode lock_links < <(stat -c '%u %a %h' -- "$lock_path")
[[ "$lock_uid" == "$EUID" && "$lock_mode" == "600" && "$lock_links" == "1" ]] || \
  die "deployment lock identity is invalid"
exec 9>>"$lock_path"
flock -n 9 || die "another public-site mutation holds the deployment lock"
[[ "$(dirname -- "$rollback_dir")" == "$rollback_base" ]] || die "rollback directory is outside the bounded rollback base"
rollback_name="$(basename -- "$rollback_dir")"
[[ "$rollback_name" =~ ^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$ ]] || die "rollback directory name is invalid"
[[ "${rollback_name##*-}" == "${source_commit:0:12}" ]] || die "rollback directory is not bound to the source commit"
[[ -d "$rollback_dir" && ! -L "$rollback_dir" ]] || die "rollback directory must be a real directory"
[[ "$(realpath -m -- "$rollback_dir")" == "$rollback_dir" ]] || die "rollback directory cannot traverse a symlink"

for state_name in rollback-authority.json release-manifest.json pre-deploy.tsv directory-state.tsv post-deploy.tsv; do
  state_path="$rollback_dir/$state_name"
  [[ -f "$state_path" && ! -L "$state_path" ]] || die "required rollback state file is not regular: $state_name"
  read -r state_uid state_mode state_links < <(stat -c '%u %a %h' -- "$state_path")
  [[ "$state_uid" == "$EUID" && "$state_mode" == "600" && "$state_links" == "1" ]] || \
    die "rollback state file identity is invalid: $state_name"
done
[[ -d "$rollback_dir/files" && ! -L "$rollback_dir/files" ]] || die "rollback backup root is not a real directory"
read -r rollback_uid rollback_mode < <(stat -c '%u %a' -- "$rollback_dir")
read -r backup_uid backup_mode < <(stat -c '%u %a' -- "$rollback_dir/files")
[[ "$rollback_uid" == "$EUID" && "$rollback_mode" == "700" ]] || die "rollback directory identity is invalid"
[[ "$backup_uid" == "$EUID" && "$backup_mode" == "700" ]] || die "rollback backup root identity is invalid"
receipt_path="$rollback_dir/rollback-receipt.json"
[[ ! -e "$receipt_path" && ! -L "$receipt_path" ]] || die "rollback receipt already exists; replay is forbidden"

plan_root="$(mktemp -d /tmp/lumencore-public-site-restore.XXXXXXXX)"
declare -a temporary_targets=()
restore_started=0
restored_file_count=0
rollback_authority_sha256=""
manifest_sha256=""
live_gate_receipt_sha256=""
restored_pre_deploy_sha256=""
previously_present_file_count=0
previously_missing_file_count=0

cleanup() {
  local temporary_target
  for temporary_target in "${temporary_targets[@]}"; do
    if [[ -n "$temporary_target" && "$temporary_target" == "$target_root/"* ]]; then
      rm -f -- "$temporary_target" || true
    fi
  done
  if [[ -n "$plan_root" && "$plan_root" == /tmp/lumencore-public-site-restore.* ]]; then
    rm -rf -- "$plan_root"
  fi
}

write_receipt() {
  python3 - \
    "$receipt_path" \
    "$COMPENSATION_RECEIPT_SCHEMA" \
    "$REPOSITORY" \
    "$WORKFLOW" \
    "$run_id" \
    "$run_attempt" \
    "$source_commit" \
    "$rollback_authority_sha256" \
    "$trigger" \
    "$live_gate_receipt_sha256" \
    "$manifest_sha256" \
    "$restored_pre_deploy_sha256" \
    "$restored_file_count" \
    "${#RELEASE_DIRECTORIES[@]}" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import re
import sys


(
    receipt_path_raw,
    schema,
    repository,
    workflow,
    run_id_raw,
    run_attempt_raw,
    source_commit,
    authority_receipt_sha256,
    trigger,
    live_gate_receipt_sha256_raw,
    manifest_sha256,
    restored_pre_deploy_sha256,
    restored_count_raw,
    directory_count_raw,
) = sys.argv[1:]
sha_pattern = re.compile(r"[0-9a-f]{64}")
if sha_pattern.fullmatch(manifest_sha256) is None:
    raise SystemExit("ERROR: rollback receipt manifest digest is invalid")
if sha_pattern.fullmatch(authority_receipt_sha256) is None:
    raise SystemExit("ERROR: rollback authority digest is invalid")
if sha_pattern.fullmatch(restored_pre_deploy_sha256) is None:
    raise SystemExit("ERROR: restored pre-deploy digest is invalid")
live_gate_receipt_sha256 = None
if live_gate_receipt_sha256_raw:
    if sha_pattern.fullmatch(live_gate_receipt_sha256_raw) is None:
        raise SystemExit("ERROR: live-gate receipt digest is invalid")
    live_gate_receipt_sha256 = live_gate_receipt_sha256_raw
payload = {
    "authority_receipt_sha256": authority_receipt_sha256,
    "claim_boundary": "ALLOWLISTED_LOCAL_BYTES_UID_GID_MODE_ONLY",
    "completed_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "live_gate_receipt_sha256": live_gate_receipt_sha256,
    "release_manifest_sha256": manifest_sha256,
    "repository": repository,
    "restored_file_count": int(restored_count_raw),
    "restored_pre_deploy_sha256": restored_pre_deploy_sha256,
    "rollback_verified": True,
    "run_attempt": int(run_attempt_raw),
    "run_id": int(run_id_raw),
    "schema": schema,
    "source_commit": source_commit,
    "trigger": trigger,
    "verified_directory_count": int(directory_count_raw),
    "workflow": workflow,
}
canonical = json.dumps(
    payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=True,
).encode("ascii")
payload["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
receipt_path = Path(receipt_path_raw)
temporary_path = receipt_path.with_name(receipt_path.name + f".tmp-{os.getpid()}")
descriptor = os.open(temporary_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "w", encoding="ascii", newline="\n") as handle:
    handle.write(rendered)
os.replace(temporary_path, receipt_path)
PY
}

restore_on_error() {
  local exit_code=$?
  trap - ERR
  set +e
  if [[ "$restore_started" -eq 1 ]]; then
    printf 'ROLLBACK_INCOMPLETE_FAIL_CLOSED=%s:%s\n' "$run_id" "$run_attempt" >&2
  fi
  exit "$exit_code"
}

trap cleanup EXIT
trap restore_on_error ERR

python3 - \
  "$rollback_dir/rollback-authority.json" \
  "$rollback_dir/release-manifest.json" \
  "$rollback_dir/pre-deploy.tsv" \
  "$rollback_dir/directory-state.tsv" \
  "$rollback_dir/post-deploy.tsv" \
  "$rollback_dir/files" \
  "$target_root" \
  "$plan_root/files.tsv" \
  "$plan_root/directories.tsv" \
  "$plan_root/validated.env" \
  "$run_id" \
  "$run_attempt" \
  "$rollback_capability_sha256" \
  "$source_commit" \
  "$rollback_name" \
  "$ROLLBACK_AUTHORITY_SCHEMA" \
  "$MANIFEST_SCHEMA" \
  "$REPOSITORY" \
  "$WORKFLOW" \
  "$AUTHORITY_SCOPE" \
  "$REQUIRED_APPROVAL" \
  "$trigger" \
  "$live_gate_receipt" \
  "$LIVE_GATE_SCHEMA" \
  "$EXPECTED_TARGET_DIRECTORY" \
  "$EXPECTED_FILE_COUNT" \
  "${RELEASE_FILES[@]}" \
  --directories \
  "${RELEASE_DIRECTORIES[@]}" <<'PY'
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys


(
    state_path_raw,
    manifest_path_raw,
    pre_path_raw,
    directory_path_raw,
    post_path_raw,
    backup_root_raw,
    target_root_raw,
    file_plan_raw,
    directory_plan_raw,
    validated_env_raw,
    run_id_raw,
    run_attempt_raw,
    rollback_capability_sha256,
    source_commit,
    rollback_name,
    authority_schema,
    manifest_schema,
    repository,
    workflow,
    authority_scope,
    deployment_approval,
    trigger,
    live_gate_receipt_raw,
    live_gate_schema,
    target_directory,
    file_count_raw,
    *remaining,
) = sys.argv[1:]
try:
    separator = remaining.index("--directories")
except ValueError as exc:
    raise SystemExit("ERROR: restore allowlist separator is missing") from exc
expected_files = remaining[:separator]
expected_directories = remaining[separator + 1 :]
file_count = int(file_count_raw)
run_id = int(run_id_raw)
run_attempt = int(run_attempt_raw)
if file_count != len(expected_files):
    raise SystemExit("ERROR: restore file count is inconsistent")

state_path = Path(state_path_raw)
manifest_path = Path(manifest_path_raw)
pre_path = Path(pre_path_raw)
directory_path = Path(directory_path_raw)
post_path = Path(post_path_raw)
backup_root = Path(backup_root_raw)
target_root = Path(target_root_raw)
file_plan = Path(file_plan_raw)
directory_plan = Path(directory_plan_raw)
validated_env = Path(validated_env_raw)
live_gate_receipt_path = Path(live_gate_receipt_raw) if live_gate_receipt_raw else None
sha_pattern = re.compile(r"[0-9a-f]{64}")
identity_pattern = re.compile(r"[A-Za-z0-9_.+-]+")
mode_pattern = re.compile(r"[0-7]{3,4}")
full_commit = re.compile(r"[0-9a-f]{40}")


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    fail(f"non-finite JSON value: {value}")


def load_json(path: Path):
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"invalid rollback JSON {path.name}: {exc}")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_tsv(path: Path, header: str, width: int) -> list[list[str]]:
    body = path.read_bytes()
    if not body.endswith(b"\n") or b"\r" in body or b"\0" in body:
        fail(f"rollback TSV framing is invalid: {path.name}")
    try:
        lines = body.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        fail(f"rollback TSV encoding is invalid: {path.name}: {exc}")
    if not lines or lines[0] != header:
        fail(f"rollback TSV header is invalid: {path.name}")
    rows = [line.split("\t") for line in lines[1:]]
    if any(len(row) != width for row in rows):
        fail(f"rollback TSV row width is invalid: {path.name}")
    return rows


authority = load_json(state_path)
authority_keys = {
    "authority_scope",
    "created_at_utc",
    "deployment_approval",
    "directory_state_sha256",
    "post_deploy_sha256",
    "pre_deploy_sha256",
    "python_version",
    "receipt_sha256",
    "release_manifest_sha256",
    "repository",
    "rollback_capability_sha256",
    "rollback_capture_id",
    "run_attempt",
    "run_id",
    "schema",
    "source_commit",
    "target_directory",
    "workflow",
}
if not isinstance(authority, dict) or set(authority) != authority_keys:
    fail("rollback authority fields do not match the strict schema")
if authority.get("schema") != authority_schema:
    fail("rollback authority schema mismatch")
if authority.get("repository") != repository or authority.get("workflow") != workflow:
    fail("rollback authority repository or workflow mismatch")
if authority.get("authority_scope") != authority_scope:
    fail("rollback authority scope mismatch")
if authority.get("deployment_approval") != deployment_approval:
    fail("rollback authority approval mismatch")
if authority.get("source_commit") != source_commit or full_commit.fullmatch(source_commit) is None:
    fail("rollback authority source commit mismatch")
if type(authority.get("run_id")) is not int or authority["run_id"] != run_id:
    fail("rollback authority run ID mismatch")
if type(authority.get("run_attempt")) is not int or authority["run_attempt"] != run_attempt:
    fail("rollback authority run attempt mismatch")
if authority.get("rollback_capability_sha256") != rollback_capability_sha256:
    fail("rollback authority capability mismatch")
if authority.get("target_directory") != target_directory:
    fail("rollback authority target directory mismatch")
if authority.get("rollback_capture_id") != rollback_name:
    fail("rollback directory name is not bound to the authority")
python_version = authority.get("python_version")
if not isinstance(python_version, str) or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", python_version) is None:
    fail("rollback authority Python version is invalid")
python_parts = tuple(int(part) for part in python_version.split("."))
if python_parts < (3, 9, 0):
    fail("rollback authority Python version is below the supported floor")
created_at_utc = authority.get("created_at_utc")
if not isinstance(created_at_utc, str) or re.fullmatch(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", created_at_utc
) is None:
    fail("rollback authority timestamp is invalid")
authority_hash = authority.get("receipt_sha256")
if not isinstance(authority_hash, str) or sha_pattern.fullmatch(authority_hash) is None:
    fail("rollback authority receipt digest is invalid")
authority_without_hash = dict(authority)
del authority_without_hash["receipt_sha256"]
canonical_authority = json.dumps(
    authority_without_hash,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=True,
).encode("ascii")
if hashlib.sha256(canonical_authority).hexdigest() != authority_hash:
    fail("rollback authority receipt digest mismatch")
if authority.get("release_manifest_sha256") != digest(manifest_path):
    fail("rollback manifest digest mismatch")
if authority.get("pre_deploy_sha256") != digest(pre_path):
    fail("pre-deploy digest mismatch")
if authority.get("directory_state_sha256") != digest(directory_path):
    fail("directory-state digest mismatch")
if authority.get("post_deploy_sha256") != digest(post_path):
    fail("post-deploy digest mismatch")

live_gate_hash = ""
if trigger == "LIVE_GATE_REJECTED":
    if live_gate_receipt_path is None:
        fail("rejected live gate is missing its receipt")
    live_gate = load_json(live_gate_receipt_path)
    live_gate_keys = {
        "base_url",
        "checked_at_utc",
        "expected_file_count",
        "matched_file_count",
        "release_verified",
        "results",
        "schema",
        "source_commit",
    }
    if not isinstance(live_gate, dict) or set(live_gate) != live_gate_keys:
        fail("live-gate receipt fields do not match the strict schema")
    if live_gate.get("schema") != live_gate_schema or live_gate.get("source_commit") != source_commit:
        fail("live-gate receipt binding mismatch")
    if live_gate.get("release_verified") is not False:
        fail("compensation is forbidden for a verified live gate")
    if type(live_gate.get("expected_file_count")) is not int or live_gate["expected_file_count"] != file_count:
        fail("live-gate receipt expected count mismatch")
    if type(live_gate.get("matched_file_count")) is not int or not 0 <= live_gate["matched_file_count"] < file_count:
        fail("live-gate receipt matched count is invalid")
    if not isinstance(live_gate.get("results"), list) or len(live_gate["results"]) != file_count:
        fail("live-gate receipt result count mismatch")
    live_gate_hash = digest(live_gate_receipt_path)
elif live_gate_receipt_path is not None:
    fail("unexpected live-gate receipt for missing-or-error trigger")

manifest = load_json(manifest_path)
manifest_keys = {
    "archive_sha256",
    "file_count",
    "files",
    "schema",
    "source_commit",
    "target_directory",
}
manifest_file_keys = {
    "archive_name",
    "bytes",
    "git_blob_oid",
    "install_mode",
    "repo_path",
    "sha256",
}
if not isinstance(manifest, dict) or set(manifest) != manifest_keys:
    fail("rollback manifest fields do not match the strict schema")
if manifest.get("schema") != manifest_schema:
    fail("rollback manifest schema mismatch")
if manifest.get("source_commit") != source_commit:
    fail("rollback manifest source commit mismatch")
if manifest.get("target_directory") != target_directory:
    fail("rollback manifest target directory mismatch")
manifest_rows = manifest.get("files")
if not isinstance(manifest_rows, list) or manifest.get("file_count") != file_count:
    fail("rollback manifest file count mismatch")
manifest_hashes = {}
for row in manifest_rows:
    if not isinstance(row, dict) or set(row) != manifest_file_keys:
        fail("rollback manifest file row fields mismatch")
    name = row.get("archive_name")
    if name in manifest_hashes:
        fail("rollback manifest contains a duplicate file")
    manifest_hashes[name] = row.get("sha256")
if list(manifest_hashes) != expected_files:
    fail("rollback manifest allowlist or order mismatch")
if any(sha_pattern.fullmatch(str(value)) is None for value in manifest_hashes.values()):
    fail("rollback manifest contains an invalid file hash")

pre_rows = read_tsv(
    pre_path,
    "file\tstate\tsha256\towner\tgroup\tuid\tgid\tmode",
    8,
)
if len(pre_rows) != file_count or [row[0] for row in pre_rows] != expected_files:
    fail("pre-deploy rows do not match the exact allowlist and order")
present = {}
missing = set()
for name, state_name, sha256, owner, group, uid, gid, mode in pre_rows:
    if state_name == "PRESENT":
        if (
            sha_pattern.fullmatch(sha256) is None
            or identity_pattern.fullmatch(owner) is None
            or identity_pattern.fullmatch(group) is None
            or not uid.isdigit()
            or not gid.isdigit()
            or mode_pattern.fullmatch(mode) is None
        ):
            fail(f"invalid present pre-deploy row: {name}")
        present[name] = (sha256, int(uid), int(gid), int(mode, 8))
    elif state_name == "MISSING":
        if [sha256, owner, group, uid, gid, mode] != ["-"] * 6:
            fail(f"invalid missing pre-deploy row: {name}")
        missing.add(name)
    else:
        fail(f"invalid pre-deploy state: {name}")
directory_rows = read_tsv(
    directory_path,
    "directory\tstate\tuid\tgid\tmode",
    5,
)
if (
    len(directory_rows) != len(expected_directories)
    or [row[0] for row in directory_rows] != expected_directories
):
    fail("directory-state rows do not match the exact allowlist and order")
for name, state_name, uid, gid, mode in directory_rows:
    if state_name == "PRESENT":
        if not uid.isdigit() or not gid.isdigit() or mode_pattern.fullmatch(mode) is None:
            fail(f"invalid present directory-state row: {name}")
    elif state_name == "MISSING":
        if [uid, gid, mode] != ["-"] * 3:
            fail(f"invalid missing directory-state row: {name}")
    else:
        fail(f"invalid directory state: {name}")

post_rows = read_tsv(
    post_path,
    "file\texpected_sha256\tactual_sha256\towner\tgroup\tuid\tgid\tmode",
    8,
)
if len(post_rows) != file_count or [row[0] for row in post_rows] != expected_files:
    fail("post-deploy rows do not match the exact allowlist and order")
candidate_uid = None
candidate_gid = None
candidate_files = {}
for name, expected, actual, owner, group, uid, gid, mode in post_rows:
    if (
        expected != manifest_hashes[name]
        or actual != expected
        or identity_pattern.fullmatch(owner) is None
        or identity_pattern.fullmatch(group) is None
        or not uid.isdigit()
        or not gid.isdigit()
        or mode != "644"
    ):
        fail(f"invalid post-deploy row: {name}")
    if candidate_uid is None:
        candidate_uid = int(uid)
        candidate_gid = int(gid)
    elif candidate_uid != int(uid) or candidate_gid != int(gid):
        fail("post-deploy ownership is inconsistent")
    candidate_files[name] = (expected, int(uid), int(gid), int(mode, 8))
    target = target_root.joinpath(*PurePosixPath(name).parts)
    for parent in target.parents:
        if parent == target_root.parent:
            break
        try:
            parent_stat = parent.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(parent_stat.st_mode):
            fail(f"target parent became a symlink: {name}")
    try:
        target_stat = target.lstat()
    except FileNotFoundError:
        if name not in missing:
            fail(f"present target disappeared after apply: {name}")
        continue
    if not stat.S_ISREG(target_stat.st_mode) or target_stat.st_nlink != 1:
        fail(f"target has an unsupported type or link count: {name}")
    target_hash = digest(target)
    candidate_ok = (
        target_hash == expected
        and target_stat.st_uid == int(uid)
        and target_stat.st_gid == int(gid)
        and stat.S_IMODE(target_stat.st_mode) == int(mode, 8)
    )
    prior_ok = False
    if name in present:
        prior_hash, prior_uid, prior_gid, prior_mode = present[name]
        prior_ok = (
            target_hash == prior_hash
            and target_stat.st_uid == prior_uid
            and target_stat.st_gid == prior_gid
            and stat.S_IMODE(target_stat.st_mode) == prior_mode
        )
    if not candidate_ok and not prior_ok:
        fail(f"target contains concurrent drift outside candidate or prior state: {name}")

if trigger == "LIVE_GATE_REJECTED":
    if live_gate.get("base_url") != "https://lumen-core.ai":
        fail("live-gate base URL mismatch")
    checked_at_utc = live_gate.get("checked_at_utc")
    if not isinstance(checked_at_utc, str) or re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z",
        checked_at_utc,
    ) is None:
        fail("live-gate timestamp is invalid")
    result_rows = live_gate["results"]
    observed_keys = {
        "actual_sha256",
        "archive_name",
        "bytes",
        "content_type",
        "content_type_allowed",
        "expected_sha256",
        "http_status",
        "status",
        "url",
    }
    error_keys = {"archive_name", "detail", "expected_sha256", "status", "url"}
    route_map = {
        "operator_home.html": "/",
        "evidence/index_bounded.html": "/evidence/",
        "build_week/prooflock_console/index.html": "/build_week/prooflock_console/",
    }
    recomputed_matches = 0
    for name, result in zip(expected_files, result_rows):
        if not isinstance(result, dict):
            fail(f"live-gate result row is invalid: {name}")
        expected = manifest_hashes[name]
        route = route_map.get(name, "/" + name)
        expected_url = f"https://lumen-core.ai{route}?release={source_commit}"
        if (
            result.get("archive_name") != name
            or result.get("expected_sha256") != expected
            or result.get("url") != expected_url
        ):
            fail(f"live-gate result binding is invalid: {name}")
        status_name = result.get("status")
        if status_name == "ERROR":
            if (
                set(result) != error_keys
                or not isinstance(result.get("detail"), str)
                or not result["detail"]
            ):
                fail(f"live-gate error row is invalid: {name}")
            continue
        if set(result) != observed_keys:
            fail(f"live-gate observed row fields are invalid: {name}")
        actual = result.get("actual_sha256")
        byte_count = result.get("bytes")
        http_status = result.get("http_status")
        allowed = result.get("content_type_allowed")
        if (
            not isinstance(actual, str)
            or sha_pattern.fullmatch(actual) is None
            or type(byte_count) is not int
            or byte_count < 0
            or type(http_status) is not int
            or type(allowed) is not bool
            or not isinstance(result.get("content_type"), str)
            or not result["content_type"]
        ):
            fail(f"live-gate observed row values are invalid: {name}")
        should_match = http_status == 200 and actual == expected and allowed
        if status_name != ("MATCH" if should_match else "MISMATCH"):
            fail(f"live-gate result contradicts its evidence: {name}")
        recomputed_matches += int(should_match)
    if recomputed_matches != live_gate["matched_file_count"] or recomputed_matches == file_count:
        fail("rejected live-gate aggregate contradicts its rows")

if candidate_uid is None or candidate_gid is None:
    fail("post-deploy candidate ownership is missing")
for name, state_name, uid, gid, mode in directory_rows:
    target = target_root.joinpath(*PurePosixPath(name).parts)
    try:
        target_stat = target.lstat()
    except FileNotFoundError:
        if state_name != "MISSING":
            fail(f"previously present directory disappeared: {name}")
        continue
    if not stat.S_ISDIR(target_stat.st_mode):
        fail(f"release directory has an unsupported type: {name}")
    candidate_ok = (
        target_stat.st_uid == candidate_uid
        and target_stat.st_gid == candidate_gid
        and stat.S_IMODE(target_stat.st_mode) == 0o755
    )
    prior_ok = (
        state_name == "PRESENT"
        and target_stat.st_uid == int(uid)
        and target_stat.st_gid == int(gid)
        and stat.S_IMODE(target_stat.st_mode) == int(mode, 8)
    )
    if not candidate_ok and not prior_ok:
        fail(f"directory contains concurrent metadata drift: {name}")

if not backup_root.is_dir() or backup_root.is_symlink():
    fail("rollback backup root is not a real directory")
actual_files = set()
actual_directories = set()
for current_root, directories, files in os.walk(backup_root, followlinks=False):
    root_path = Path(current_root)
    relative_root = root_path.relative_to(backup_root)
    for directory in directories:
        path = root_path / directory
        if path.is_symlink():
            fail("rollback backup contains a symbolic directory")
        actual_directories.add((relative_root / directory).as_posix())
    for filename in files:
        path = root_path / filename
        file_stat = path.lstat()
        if stat.S_ISLNK(file_stat.st_mode) or not stat.S_ISREG(file_stat.st_mode) or file_stat.st_nlink != 1:
            fail("rollback backup contains an unsupported file")
        actual_files.add((relative_root / filename).as_posix())
expected_backup_directories = set()
for name in present:
    parent = PurePosixPath(name).parent
    while parent != PurePosixPath("."):
        expected_backup_directories.add(parent.as_posix())
        parent = parent.parent
if actual_files != set(present) or actual_directories != expected_backup_directories:
    fail("rollback backup inventory does not match the captured present-file set")
for name, (expected_hash, uid, gid, mode) in present.items():
    path = backup_root.joinpath(*PurePosixPath(name).parts)
    file_stat = path.stat()
    if (
        digest(path) != expected_hash
        or file_stat.st_uid != uid
        or file_stat.st_gid != gid
        or stat.S_IMODE(file_stat.st_mode) != mode
        or file_stat.st_nlink != 1
    ):
        fail(f"rollback backup identity mismatch: {name}")

file_plan.write_text(
    "".join(
        f"{name}\t{state_name}\t{sha256}\t{uid}\t{gid}\t{mode}"
        f"\t{candidate_files[name][0]}\t{candidate_files[name][1]}"
        f"\t{candidate_files[name][2]}\t{candidate_files[name][3]:o}\n"
        for name, state_name, sha256, _owner, _group, uid, gid, mode in pre_rows
    ),
    encoding="ascii",
)
directory_plan.write_text(
    "".join(
        f"{name}\t{state_name}\t{uid}\t{gid}\t{mode}"
        f"\t{candidate_uid}\t{candidate_gid}\t755\n"
        for name, state_name, uid, gid, mode in directory_rows
    ),
    encoding="ascii",
)
validated_env.write_text(
    "".join(
        [
            f"ROLLBACK_AUTHORITY_SHA256={authority_hash}\n",
            f"MANIFEST_SHA256={digest(manifest_path)}\n",
            f"PRE_DEPLOY_SHA256={digest(pre_path)}\n",
            f"LIVE_GATE_RECEIPT_SHA256={live_gate_hash}\n",
            f"PRESENT_COUNT={len(present)}\n",
            f"MISSING_COUNT={len(missing)}\n",
        ]
    ),
    encoding="ascii",
)
PY

while IFS='=' read -r key value; do
  case "$key" in
    ROLLBACK_AUTHORITY_SHA256) rollback_authority_sha256="$value" ;;
    MANIFEST_SHA256) manifest_sha256="$value" ;;
    PRE_DEPLOY_SHA256) restored_pre_deploy_sha256="$value" ;;
    LIVE_GATE_RECEIPT_SHA256) live_gate_receipt_sha256="$value" ;;
    PRESENT_COUNT) previously_present_file_count="$value" ;;
    MISSING_COUNT) previously_missing_file_count="$value" ;;
    *) die "unexpected validated restore field: $key" ;;
  esac
done < "$plan_root/validated.env"
[[ "$rollback_authority_sha256" =~ ^[0-9a-f]{64}$ ]] || die "validated rollback authority digest is invalid"
[[ "$manifest_sha256" =~ ^[0-9a-f]{64}$ ]] || die "validated manifest digest is invalid"
[[ "$restored_pre_deploy_sha256" =~ ^[0-9a-f]{64}$ ]] || die "validated pre-deploy digest is invalid"
if [[ "$trigger" == "LIVE_GATE_REJECTED" ]]; then
  [[ "$live_gate_receipt_sha256" =~ ^[0-9a-f]{64}$ ]] || die "validated live-gate receipt digest is invalid"
else
  [[ -z "$live_gate_receipt_sha256" ]] || die "unexpected live-gate receipt digest"
fi
[[ "$previously_present_file_count" =~ ^[0-9]+$ ]] || die "validated present count is invalid"
[[ "$previously_missing_file_count" =~ ^[0-9]+$ ]] || die "validated missing count is invalid"
[[ "$((previously_present_file_count + previously_missing_file_count))" -eq "$EXPECTED_FILE_COUNT" ]] || \
  die "validated rollback counts do not cover the exact allowlist"

current_target_state=""
revalidate_file_target() {
  local name="$1" prior_state="$2" prior_hash="$3" prior_uid="$4" prior_gid="$5" prior_mode="$6"
  local candidate_hash="$7" candidate_uid="$8" candidate_gid="$9" candidate_mode="${10}"
  local target_path="$target_root/$name" actual_hash actual_uid actual_gid actual_mode actual_links
  [[ "$(realpath -m -- "$target_path")" == "$target_path" ]] || die "target path now traverses a symlink: $name"
  [[ ! -L "$target_path" ]] || die "target became a symlink: $name"
  if [[ ! -e "$target_path" ]]; then
    if [[ "$prior_state" == "MISSING" ]]; then
      current_target_state="PRIOR"
      return 0
    fi
    die "present target disappeared before mutation: $name"
  fi
  [[ -f "$target_path" ]] || die "target has an unsupported type before mutation: $name"
  actual_links="$(stat -c '%h' -- "$target_path")"
  [[ "$actual_links" == "1" ]] || die "target has multiple hard links before mutation: $name"
  actual_hash="$(sha256sum -- "$target_path")"
  actual_hash="${actual_hash%% *}"
  read -r actual_uid actual_gid actual_mode < <(stat -c '%u %g %a' -- "$target_path")
  if [[ "$actual_hash" == "$candidate_hash" && "$actual_uid" == "$candidate_uid" && \
        "$actual_gid" == "$candidate_gid" && "$actual_mode" == "$candidate_mode" ]]; then
    current_target_state="CANDIDATE"
    return 0
  fi
  if [[ "$prior_state" == "PRESENT" && "$actual_hash" == "$prior_hash" && \
        "$actual_uid" == "$prior_uid" && "$actual_gid" == "$prior_gid" && \
        "$actual_mode" == "$prior_mode" ]]; then
    current_target_state="PRIOR"
    return 0
  fi
  die "target changed outside candidate or prior state before mutation: $name"
}

revalidate_directory_target() {
  local relative="$1" prior_state="$2" prior_uid="$3" prior_gid="$4" prior_mode="$5"
  local candidate_uid="$6" candidate_gid="$7" candidate_mode="$8"
  local path="$target_root/$relative" actual_uid actual_gid actual_mode
  [[ "$(realpath -m -- "$path")" == "$path" ]] || die "directory path now traverses a symlink: $relative"
  [[ ! -L "$path" ]] || die "release directory became a symlink: $relative"
  if [[ ! -e "$path" ]]; then
    if [[ "$prior_state" == "MISSING" ]]; then
      current_target_state="PRIOR"
      return 0
    fi
    die "present release directory disappeared before mutation: $relative"
  fi
  [[ -d "$path" ]] || die "release directory has an unsupported type before mutation: $relative"
  read -r actual_uid actual_gid actual_mode < <(stat -c '%u %g %a' -- "$path")
  if [[ "$actual_uid" == "$candidate_uid" && "$actual_gid" == "$candidate_gid" && \
        "$actual_mode" == "$candidate_mode" ]]; then
    current_target_state="CANDIDATE"
    return 0
  fi
  if [[ "$prior_state" == "PRESENT" && "$actual_uid" == "$prior_uid" && \
        "$actual_gid" == "$prior_gid" && "$actual_mode" == "$prior_mode" ]]; then
    current_target_state="PRIOR"
    return 0
  fi
  die "release directory changed outside candidate or prior state before mutation: $relative"
}

restore_started=1
while IFS=$'\t' read -r name state_name expected_hash uid gid mode candidate_hash candidate_uid candidate_gid candidate_mode; do
  target_path="$target_root/$name"
  backup_path="$rollback_dir/files/$name"
  if [[ -n "$before_target_hook" ]]; then
    "$before_target_hook" "$name" "$target_path"
  fi
  if [[ "$state_name" == "PRESENT" ]]; then
    parent="$(dirname -- "$target_path")"
    temporary_target="$parent/.$(basename -- "$name").public-site-restore-${run_id}-${run_attempt}-$$"
    temporary_targets+=("$temporary_target")
    cp -a -- "$backup_path" "$temporary_target"
    if [[ "$test_mode" -eq 0 ]]; then
      chown "$uid:$gid" -- "$temporary_target"
    fi
    chmod "$mode" -- "$temporary_target"
    temporary_hash="$(sha256sum -- "$temporary_target")"
    temporary_hash="${temporary_hash%% *}"
    [[ "$temporary_hash" == "$expected_hash" ]] || die "staged restore hash mismatch: $name"
    read -r temporary_uid temporary_gid temporary_mode < <(stat -c '%u %g %a' -- "$temporary_target")
    [[ "$temporary_uid" == "$uid" && "$temporary_gid" == "$gid" && "$temporary_mode" == "$mode" ]] || \
      die "staged restore metadata mismatch: $name"
    revalidate_file_target "$name" "$state_name" "$expected_hash" "$uid" "$gid" "$mode" \
      "$candidate_hash" "$candidate_uid" "$candidate_gid" "$candidate_mode"
    if [[ "$current_target_state" == "CANDIDATE" ]]; then
      mv -f -- "$temporary_target" "$target_path"
    else
      rm -f -- "$temporary_target"
    fi
  elif [[ "$state_name" == "MISSING" ]]; then
    revalidate_file_target "$name" "$state_name" "$expected_hash" "$uid" "$gid" "$mode" \
      "$candidate_hash" "$candidate_uid" "$candidate_gid" "$candidate_mode"
    if [[ "$current_target_state" == "CANDIDATE" ]]; then
      rm -- "$target_path"
    fi
  else
    die "validated restore plan contains an invalid file state: $name"
  fi
  if [[ "$state_name" == "PRESENT" ]]; then
    [[ -f "$target_path" && ! -L "$target_path" && "$(stat -c '%h' -- "$target_path")" == "1" ]] || \
      die "restored target identity is invalid immediately after mutation: $name"
    immediate_hash="$(sha256sum -- "$target_path")"
    immediate_hash="${immediate_hash%% *}"
    read -r immediate_uid immediate_gid immediate_mode < <(stat -c '%u %g %a' -- "$target_path")
    [[ "$immediate_hash" == "$expected_hash" && "$immediate_uid" == "$uid" && \
          "$immediate_gid" == "$gid" && "$immediate_mode" == "$mode" ]] || \
      die "restored target does not equal prior state immediately after mutation: $name"
  else
    [[ ! -e "$target_path" && ! -L "$target_path" ]] || \
      die "previously missing target remains immediately after mutation: $name"
  fi
  restored_file_count=$((restored_file_count + 1))
done < "$plan_root/files.tsv"

mapfile -t directory_rows < "$plan_root/directories.tsv"
for ((index = ${#directory_rows[@]} - 1; index >= 0; index--)); do
  IFS=$'\t' read -r relative state_name uid gid mode candidate_uid candidate_gid candidate_mode <<<"${directory_rows[$index]}"
  path="$target_root/$relative"
  revalidate_directory_target "$relative" "$state_name" "$uid" "$gid" "$mode" \
    "$candidate_uid" "$candidate_gid" "$candidate_mode"
  if [[ "$state_name" == "PRESENT" ]]; then
    if [[ "$current_target_state" == "CANDIDATE" ]]; then
      if [[ "$test_mode" -eq 0 ]]; then
        chown "$uid:$gid" -- "$path"
      fi
      chmod "$mode" -- "$path"
    fi
  elif [[ "$state_name" == "MISSING" ]]; then
    if [[ "$current_target_state" == "CANDIDATE" ]]; then
      rmdir -- "$path"
    fi
  else
    die "validated restore plan contains an invalid directory state: $relative"
  fi
  if [[ "$state_name" == "PRESENT" ]]; then
    [[ -d "$path" && ! -L "$path" ]] || die "restored directory is invalid immediately after mutation: $relative"
    read -r immediate_uid immediate_gid immediate_mode < <(stat -c '%u %g %a' -- "$path")
    [[ "$immediate_uid" == "$uid" && "$immediate_gid" == "$gid" && "$immediate_mode" == "$mode" ]] || \
      die "restored directory does not equal prior state immediately after mutation: $relative"
  else
    [[ ! -e "$path" && ! -L "$path" ]] || \
      die "previously missing directory remains immediately after mutation: $relative"
  fi
done

while IFS=$'\t' read -r name state_name expected_hash uid gid mode _candidate_hash _candidate_uid _candidate_gid _candidate_mode; do
  target_path="$target_root/$name"
  if [[ "$state_name" == "PRESENT" ]]; then
    [[ -f "$target_path" && ! -L "$target_path" ]] || die "restored file is not regular: $name"
    actual_hash="$(sha256sum -- "$target_path")"
    actual_hash="${actual_hash%% *}"
    read -r actual_uid actual_gid actual_mode < <(stat -c '%u %g %a' -- "$target_path")
    [[ "$actual_hash" == "$expected_hash" ]] || die "restored file hash mismatch: $name"
    [[ "$actual_uid" == "$uid" && "$actual_gid" == "$gid" && "$actual_mode" == "$mode" ]] || \
      die "restored file metadata mismatch: $name"
  else
    [[ ! -e "$target_path" && ! -L "$target_path" ]] || die "previously missing file remains after restore: $name"
  fi
done < "$plan_root/files.tsv"

for row in "${directory_rows[@]}"; do
  IFS=$'\t' read -r relative state_name uid gid mode _candidate_uid _candidate_gid _candidate_mode <<<"$row"
  path="$target_root/$relative"
  if [[ "$state_name" == "PRESENT" ]]; then
    [[ -d "$path" && ! -L "$path" ]] || die "restored directory is not real: $relative"
    read -r actual_uid actual_gid actual_mode < <(stat -c '%u %g %a' -- "$path")
    [[ "$actual_uid" == "$uid" && "$actual_gid" == "$gid" && "$actual_mode" == "$mode" ]] || \
      die "restored directory metadata mismatch: $relative"
  else
    [[ ! -e "$path" && ! -L "$path" ]] || die "previously missing directory remains after restore: $relative"
  fi
done

[[ "$restored_file_count" -eq "$EXPECTED_FILE_COUNT" ]] || die "restore did not cover the exact allowlist"
write_receipt
restore_started=0
printf 'PUBLIC_SITE_RUN_ID=%s\n' "$run_id"
printf 'PUBLIC_SITE_RUN_ATTEMPT=%s\n' "$run_attempt"
printf 'PUBLIC_SITE_ROLLBACK_AUTHORITY_SHA256=%s\n' "$rollback_authority_sha256"
printf 'PUBLIC_SITE_RESTORED_FILE_COUNT=%s\n' "$restored_file_count"
printf '%s\n' 'PUBLIC_SITE_ROLLBACK_OK'
