#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

readonly REQUIRED_APPROVAL="DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT"
readonly PRODUCTION_TARGET="/opt/lumencore/dashboard"
readonly PRODUCTION_ROLLBACK_BASE="/opt/lumencore/rollbacks/public-site"
readonly MANIFEST_SCHEMA="lumencore.public_site_release_manifest.v1"
readonly ROLLBACK_AUTHORITY_SCHEMA="lumencore.public_site_same_run_rollback_authority.v1"
readonly REPOSITORY="robertashworth1986-debug/lumen-core-public"
readonly WORKFLOW=".github/workflows/deploy-public-site-release.yml"
readonly AUTHORITY_SCOPE="FAILED_EXTERNAL_LIVE_GATE_COMPENSATION_IN_SAME_WORKFLOW_RUN_ONLY"
readonly EXPECTED_TARGET_DIRECTORY="/opt/lumencore/dashboard"
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

archive=""
manifest=""
source_commit=""
approval=""
run_id=""
run_attempt=""
capability_stdin=0

die() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

usage() {
  cat >&2 <<'EOF'
Usage: APPLY_PUBLIC_SITE_RELEASE_ON_VPS.sh \
  --archive PATH --manifest PATH --source-commit FULL_SHA \
  --run-id POSITIVE_INTEGER --run-attempt POSITIVE_INTEGER \
  --rollback-capability-stdin \
  --approval DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT
EOF
  return 2
}

while (($#)); do
  case "$1" in
    --archive)
      (($# >= 2)) || usage
      archive="$2"
      shift 2
      ;;
    --manifest)
      (($# >= 2)) || usage
      manifest="$2"
      shift 2
      ;;
    --source-commit)
      (($# >= 2)) || usage
      source_commit="$2"
      shift 2
      ;;
    --approval)
      (($# >= 2)) || usage
      approval="$2"
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
    *)
      usage
      ;;
  esac
done

[[ "$approval" == "$REQUIRED_APPROVAL" ]] || die "explicit public-site deployment approval is required"
[[ "$source_commit" =~ ^[0-9a-f]{40}$ ]] || die "source commit must be a full lowercase SHA-1"
[[ "$run_id" =~ ^[1-9][0-9]*$ ]] || die "run ID must be a positive integer"
[[ "$run_attempt" =~ ^[1-9][0-9]*$ ]] || die "run attempt must be a positive integer"
[[ "$capability_stdin" -eq 1 ]] || die "rollback capability must be supplied through standard input"
[[ -f "$archive" && ! -L "$archive" ]] || die "archive must be a regular non-symlink file"
[[ -f "$manifest" && ! -L "$manifest" ]] || die "manifest must be a regular non-symlink file"

test_mode=0
if [[ "${PUBLIC_SITE_DEPLOY_TEST_MODE:-}" == "1" ]]; then
  [[ "$EUID" -ne 0 ]] || die "test mode is forbidden for root"
  [[ -n "${PUBLIC_SITE_DEPLOY_TEST_ROOT:-}" ]] || die "test mode requires PUBLIC_SITE_DEPLOY_TEST_ROOT"
  [[ "$PUBLIC_SITE_DEPLOY_TEST_ROOT" == /* && "$PUBLIC_SITE_DEPLOY_TEST_ROOT" != "/" ]] || \
    die "test root must be a non-root absolute path"
  target_root="$PUBLIC_SITE_DEPLOY_TEST_ROOT/opt/lumencore/dashboard"
  rollback_base="$PUBLIC_SITE_DEPLOY_TEST_ROOT/opt/lumencore/rollbacks/public-site"
  test_mode=1
else
  [[ -z "${PUBLIC_SITE_DEPLOY_TEST_ROOT:-}" ]] || die "test root is forbidden outside test mode"
  [[ "$EUID" -eq 0 ]] || die "production apply must run as root"
  target_root="$PRODUCTION_TARGET"
  rollback_base="$PRODUCTION_ROLLBACK_BASE"
fi

for command_name in python3 sha256sum stat cp cmp install date mktemp realpath dirname basename flock; do
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

root_stage="$(mktemp -d /tmp/lumencore-public-site-root.XXXXXXXX)"
rollback_dir=""
deployment_started=0
declare -a temporary_targets=()

cleanup() {
  if [[ -n "$root_stage" && "$root_stage" == /tmp/lumencore-public-site-root.* ]]; then
    rm -rf -- "$root_stage"
  fi
}

restore_directory_state() {
  [[ -f "$rollback_dir/directory-state.tsv" ]] || return 0
  mapfile -t directory_rows < "$rollback_dir/directory-state.tsv"
  local index relative state uid gid mode path
  local restore_failed=0
  for ((index = ${#directory_rows[@]} - 1; index >= 0; index--)); do
    IFS=$'\t' read -r relative state uid gid mode <<<"${directory_rows[$index]}"
    [[ "$relative" != "directory" ]] || continue
    path="$target_root/$relative"
    if [[ "$state" == "PRESENT" ]]; then
      if [[ -d "$path" && ! -L "$path" ]]; then
        if [[ "$test_mode" -eq 0 ]]; then
          chown "$uid:$gid" -- "$path" || restore_failed=1
        fi
        chmod "$mode" -- "$path" || restore_failed=1
      else
        restore_failed=1
      fi
    elif [[ "$state" == "MISSING" ]]; then
      rmdir -- "$path" 2>/dev/null || restore_failed=1
    fi
  done
  return "$restore_failed"
}

rollback_on_error() {
  local exit_code=$?
  trap - ERR
  set +e
  if [[ "$deployment_started" -eq 1 && -n "$rollback_dir" ]]; then
    printf 'Deployment failed; restoring bounded public-site files from %s\n' "$rollback_dir" >&2
    local name target_path backup_path temporary_target
    local rollback_failed=0
    for temporary_target in "${temporary_targets[@]}"; do
      rm -f -- "$temporary_target" || rollback_failed=1
    done
    for name in "${RELEASE_FILES[@]}"; do
      target_path="$target_root/$name"
      backup_path="$rollback_dir/files/$name"
      rm -f -- "$target_path" || rollback_failed=1
      if [[ -f "$backup_path" && ! -L "$backup_path" ]]; then
        install -d -m 0755 -- "$(dirname "$target_path")" || rollback_failed=1
        cp -a -- "$backup_path" "$target_path" || rollback_failed=1
        cmp -s -- "$backup_path" "$target_path" || rollback_failed=1
      elif [[ -e "$target_path" ]]; then
        rollback_failed=1
      fi
    done
    restore_directory_state || rollback_failed=1
    if [[ "$rollback_failed" -eq 0 ]]; then
      printf 'ROLLBACK_APPLIED=%s\n' "$rollback_dir" >&2
    else
      printf 'ROLLBACK_FAILED=%s\n' "$rollback_dir" >&2
    fi
  fi
  exit "$exit_code"
}

trap cleanup EXIT
trap rollback_on_error ERR

install -m 0600 -- "$archive" "$root_stage/release.tar"
install -m 0600 -- "$manifest" "$root_stage/manifest.json"
mkdir -m 0700 -- "$root_stage/unpacked"

python3 - \
  "$root_stage/manifest.json" \
  "$root_stage/release.tar" \
  "$root_stage/unpacked" \
  "$source_commit" \
  "$MANIFEST_SCHEMA" \
  "$EXPECTED_TARGET_DIRECTORY" \
  "${RELEASE_FILES[@]}" <<'PY'
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile


manifest_path = Path(sys.argv[1])
archive_path = Path(sys.argv[2])
output_dir = Path(sys.argv[3])
source_commit = sys.argv[4]
schema = sys.argv[5]
target_directory = sys.argv[6]
expected_names = sys.argv[7:]


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


try:
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8"),
        object_pairs_hook=strict_object,
        parse_constant=reject_constant,
    )
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    fail(f"invalid release manifest: {exc}")

expected_manifest_keys = {
    "archive_sha256",
    "file_count",
    "files",
    "schema",
    "source_commit",
    "target_directory",
}
expected_file_keys = {
    "archive_name",
    "bytes",
    "git_blob_oid",
    "install_mode",
    "repo_path",
    "sha256",
}
if not isinstance(manifest, dict) or set(manifest) != expected_manifest_keys:
    fail("manifest fields do not match the strict schema")
if manifest.get("schema") != schema:
    fail("unexpected manifest schema")
if manifest.get("source_commit") != source_commit:
    fail("manifest source commit does not match the approved commit")
if manifest.get("target_directory") != target_directory:
    fail("manifest target directory is not the bounded dashboard root")
if manifest.get("file_count") != len(expected_names):
    fail("manifest file count does not match the exact allowlist")

archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
if manifest.get("archive_sha256") != archive_sha256:
    fail("archive hash does not match the manifest")

rows = manifest.get("files")
if not isinstance(rows, list) or len(rows) != len(expected_names):
    fail("manifest must contain exactly the allowlisted file rows")
by_name = {}
for row in rows:
    if not isinstance(row, dict) or set(row) != expected_file_keys:
        fail("manifest file row does not match the strict schema")
    name = row.get("archive_name")
    if name in by_name:
        fail("manifest contains a duplicate file")
    by_name[name] = row
if list(by_name) != expected_names:
    fail("manifest file allowlist or order is invalid")

with tarfile.open(archive_path, mode="r:") as archive:
    members = archive.getmembers()
    if [member.name for member in members] != expected_names:
        fail("archive entries do not match the exact-file allowlist")
    for member in members:
        name_path = PurePosixPath(member.name)
        if name_path.is_absolute() or ".." in name_path.parts:
            fail(f"archive entry has an unsafe path: {member.name}")
        if not member.isfile() or member.mode & 0o777 != 0o644:
            fail(f"archive entry is not a regular 0644 file: {member.name}")
        row = by_name[member.name]
        if row.get("repo_path") != "dashboard/" + member.name:
            fail(f"manifest repository path is invalid: {member.name}")
        if row.get("install_mode") != "0644":
            fail(f"manifest install mode is invalid: {member.name}")
        if not isinstance(row.get("bytes"), int) or row["bytes"] < 0:
            fail(f"manifest byte count is invalid: {member.name}")
        if not re.fullmatch(r"[0-9a-f]{40}", str(row.get("git_blob_oid", ""))):
            fail(f"manifest Git blob ID is invalid: {member.name}")
        expected_hash = str(row.get("sha256", ""))
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            fail(f"manifest SHA-256 is invalid: {member.name}")

        extracted = archive.extractfile(member)
        if extracted is None:
            fail(f"archive entry cannot be read: {member.name}")
        body = extracted.read()
        if len(body) != row["bytes"]:
            fail(f"archive byte count mismatch: {member.name}")
        if hashlib.sha256(body).hexdigest() != expected_hash:
            fail(f"archive file hash mismatch: {member.name}")

        destination = output_dir.joinpath(*name_path.parts)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(body)
        os.chmod(destination, 0o644)

with (output_dir.parent / "expected.tsv").open("w", encoding="ascii", newline="\n") as handle:
    for name in expected_names:
        handle.write(f"{name}\t{by_name[name]['sha256']}\n")
PY

declare -A expected_hashes=()
while IFS=$'\t' read -r name expected_hash; do
  [[ -n "$name" && -n "$expected_hash" ]] || die "invalid expected hash row"
  expected_hashes["$name"]="$expected_hash"
done < "$root_stage/expected.tsv"
[[ "${#expected_hashes[@]}" -eq "$EXPECTED_FILE_COUNT" ]] || \
  die "expected hash set does not match the exact-file allowlist"

[[ "$(realpath -m -- "$rollback_base")" == "$rollback_base" ]] || die "rollback path cannot traverse a symlink"
[[ ! -L "$rollback_base" ]] || die "rollback directory cannot be a symlink"
install -d -m 0750 -- "$rollback_base"
read -r rollback_base_uid rollback_base_mode < <(stat -c '%u %a' -- "$rollback_base")
[[ "$rollback_base_uid" == "$EUID" && "$rollback_base_mode" == "750" ]] || \
  die "rollback base identity is invalid"
lock_path="$rollback_base/.deployment.lock"
[[ "$(realpath -m -- "$lock_path")" == "$lock_path" ]] || die "deployment lock path cannot traverse a symlink"
[[ ! -e "$lock_path" || -f "$lock_path" ]] || die "deployment lock has an unsupported type"
[[ ! -L "$lock_path" ]] || die "deployment lock cannot be a symlink"
exec 9>>"$lock_path"
chmod 0600 -- "$lock_path"
read -r lock_uid lock_mode lock_links < <(stat -c '%u %a %h' -- "$lock_path")
[[ "$lock_uid" == "$EUID" && "$lock_mode" == "600" && "$lock_links" == "1" ]] || \
  die "deployment lock identity is invalid"
flock -n 9 || die "another public-site mutation holds the deployment lock"

[[ -d "$target_root" && ! -L "$target_root" ]] || die "dashboard root must be a real directory"
[[ "$(realpath -m -- "$target_root")" == "$target_root" ]] || die "dashboard root cannot traverse a symlink"
for relative in "${RELEASE_DIRECTORIES[@]}"; do
  path="$target_root/$relative"
  [[ "$(realpath -m -- "$path")" == "$path" ]] || die "release path cannot traverse a symlink: $path"
  [[ ! -L "$path" ]] || die "release directory cannot be a symlink: $path"
  [[ ! -e "$path" || -d "$path" ]] || die "release directory path has an invalid type: $path"
done
for name in "${RELEASE_FILES[@]}"; do
  target_path="$target_root/$name"
  [[ "$(realpath -m -- "$target_path")" == "$target_path" ]] || die "target path cannot traverse a symlink: $name"
  [[ ! -L "$target_path" ]] || die "target file cannot be a symlink: $name"
  [[ ! -e "$target_path" || -f "$target_path" ]] || die "target path has an unsupported type: $name"
done

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
rollback_dir="$rollback_base/${timestamp}-${source_commit:0:12}"
[[ ! -e "$rollback_dir" ]] || die "timestamped rollback directory already exists"
mkdir -m 0700 -- "$rollback_dir" "$rollback_dir/files"
install -m 0600 -- "$root_stage/manifest.json" "$rollback_dir/release-manifest.json"

printf 'directory\tstate\tuid\tgid\tmode\n' > "$rollback_dir/directory-state.tsv"
for relative in "${RELEASE_DIRECTORIES[@]}"; do
  path="$target_root/$relative"
  if [[ -d "$path" ]]; then
    read -r uid gid mode < <(stat -c '%u %g %a' -- "$path")
    printf '%s\tPRESENT\t%s\t%s\t%s\n' "$relative" "$uid" "$gid" "$mode" >> "$rollback_dir/directory-state.tsv"
  else
    printf '%s\tMISSING\t-\t-\t-\n' "$relative" >> "$rollback_dir/directory-state.tsv"
  fi
done

printf 'file\tstate\tsha256\towner\tgroup\tuid\tgid\tmode\n' > "$rollback_dir/pre-deploy.tsv"
for name in "${RELEASE_FILES[@]}"; do
  target_path="$target_root/$name"
  backup_path="$rollback_dir/files/$name"
  if [[ -f "$target_path" ]]; then
    install -d -m 0700 -- "$(dirname "$backup_path")"
    read -r owner group uid gid mode < <(stat -c '%U %G %u %g %a' -- "$target_path")
    current_hash="$(sha256sum -- "$target_path")"
    current_hash="${current_hash%% *}"
    printf '%s\tPRESENT\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$name" "$current_hash" "$owner" "$group" "$uid" "$gid" "$mode" >> "$rollback_dir/pre-deploy.tsv"
    cp -a -- "$target_path" "$backup_path"
    [[ -f "$backup_path" && ! -L "$backup_path" ]] || die "rollback backup is not regular: $name"
    backup_hash="$(sha256sum -- "$backup_path")"
    backup_hash="${backup_hash%% *}"
    [[ "$backup_hash" == "$current_hash" ]] || die "rollback backup hash mismatch: $name"
    read -r backup_uid backup_gid backup_mode < <(stat -c '%u %g %a' -- "$backup_path")
    [[ "$backup_uid" == "$uid" && "$backup_gid" == "$gid" && "$backup_mode" == "$mode" ]] || \
      die "rollback backup metadata mismatch: $name"
    [[ "$(stat -c '%d:%i' -- "$backup_path")" != "$(stat -c '%d:%i' -- "$target_path")" ]] || \
      die "rollback backup is not an independent inode: $name"
    [[ "$(stat -c '%h' -- "$backup_path")" == "1" ]] || die "rollback backup has multiple hard links: $name"
  else
    printf '%s\tMISSING\t-\t-\t-\t-\t-\t-\n' "$name" >> "$rollback_dir/pre-deploy.tsv"
  fi
done

deployment_started=1
for relative in "${RELEASE_DIRECTORIES[@]}"; do
  path="$target_root/$relative"
  if [[ "$test_mode" -eq 1 ]]; then
    install -d -m 0755 -- "$path"
  else
    install -d -o root -g root -m 0755 -- "$path"
  fi
done

for name in "${RELEASE_FILES[@]}"; do
  source_path="$root_stage/unpacked/$name"
  target_path="$target_root/$name"
  parent="$(dirname "$target_path")"
  temporary_target="$parent/.$(basename "$name").public-site-${timestamp}-$$"
  temporary_targets+=("$temporary_target")
  if [[ "$test_mode" -eq 1 ]]; then
    install -m 0644 -- "$source_path" "$temporary_target"
  else
    install -o root -g root -m 0644 -- "$source_path" "$temporary_target"
  fi
  temporary_hash="$(sha256sum -- "$temporary_target")"
  temporary_hash="${temporary_hash%% *}"
  [[ "$temporary_hash" == "${expected_hashes[$name]}" ]] || die "staged target hash mismatch: $name"
done

for index in "${!RELEASE_FILES[@]}"; do
  mv -f -- "${temporary_targets[$index]}" "$target_root/${RELEASE_FILES[$index]}"
done

printf 'file\texpected_sha256\tactual_sha256\towner\tgroup\tuid\tgid\tmode\n' > "$rollback_dir/post-deploy.tsv"
for name in "${RELEASE_FILES[@]}"; do
  target_path="$target_root/$name"
  [[ -f "$target_path" && ! -L "$target_path" ]] || die "post-deploy file is not regular: $name"
  actual_hash="$(sha256sum -- "$target_path")"
  actual_hash="${actual_hash%% *}"
  [[ "$actual_hash" == "${expected_hashes[$name]}" ]] || die "post-deploy hash mismatch: $name"
  read -r owner group uid gid mode < <(stat -c '%U %G %u %g %a' -- "$target_path")
  [[ "$mode" == "644" ]] || die "post-deploy file mode is not 0644: $name"
  if [[ "$test_mode" -eq 0 ]]; then
    [[ "$uid" == "0" && "$gid" == "0" ]] || die "post-deploy ownership is not root:root: $name"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$name" "${expected_hashes[$name]}" "$actual_hash" "$owner" "$group" "$uid" "$gid" "$mode" >> "$rollback_dir/post-deploy.tsv"
done

created_at_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
rollback_authority_sha256="$(python3 - \
  "$rollback_dir/rollback-authority.json" \
  "$rollback_dir/release-manifest.json" \
  "$rollback_dir/pre-deploy.tsv" \
  "$rollback_dir/directory-state.tsv" \
  "$rollback_dir/post-deploy.tsv" \
  "$rollback_dir/files" \
  "$run_id" \
  "$run_attempt" \
  "$rollback_capability_sha256" \
  "$source_commit" \
  "$ROLLBACK_AUTHORITY_SCHEMA" \
  "$MANIFEST_SCHEMA" \
  "$REPOSITORY" \
  "$WORKFLOW" \
  "$AUTHORITY_SCOPE" \
  "$REQUIRED_APPROVAL" \
  "$EXPECTED_TARGET_DIRECTORY" \
  "$timestamp" \
  "$created_at_utc" \
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
    run_id_raw,
    run_attempt_raw,
    rollback_capability_sha256,
    source_commit,
    authority_schema,
    manifest_schema,
    repository,
    workflow,
    authority_scope,
    deployment_approval,
    target_directory,
    rollback_capture_id,
    created_at_utc,
    file_count_raw,
    *remaining,
) = sys.argv[1:]
try:
    separator = remaining.index("--directories")
except ValueError as exc:
    raise SystemExit("ERROR: rollback state allowlist separator is missing") from exc
expected_files = remaining[:separator]
expected_directories = remaining[separator + 1 :]
file_count = int(file_count_raw)
run_id = int(run_id_raw)
run_attempt = int(run_attempt_raw)
if file_count != len(expected_files):
    raise SystemExit("ERROR: rollback state file count is inconsistent")

state_path = Path(state_path_raw)
manifest_path = Path(manifest_path_raw)
pre_path = Path(pre_path_raw)
directory_path = Path(directory_path_raw)
post_path = Path(post_path_raw)
backup_root = Path(backup_root_raw)
sha_pattern = re.compile(r"[0-9a-f]{64}")
identity_pattern = re.compile(r"[A-Za-z0-9_.+-]+")
mode_pattern = re.compile(r"[0-7]{3,4}")


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


try:
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8"),
        object_pairs_hook=strict_object,
        parse_constant=reject_constant,
    )
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    fail(f"rollback manifest is invalid: {exc}")
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
for name, state, sha256, owner, group, uid, gid, mode in pre_rows:
    if state == "PRESENT":
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
    elif state == "MISSING":
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
for name, state, uid, gid, mode in directory_rows:
    if state == "PRESENT":
        if not uid.isdigit() or not gid.isdigit() or mode_pattern.fullmatch(mode) is None:
            fail(f"invalid present directory-state row: {name}")
    elif state == "MISSING":
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
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
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

payload = {
    "authority_scope": authority_scope,
    "created_at_utc": created_at_utc,
    "deployment_approval": deployment_approval,
    "directory_state_sha256": digest(directory_path),
    "post_deploy_sha256": digest(post_path),
    "pre_deploy_sha256": digest(pre_path),
    "python_version": ".".join(map(str, sys.version_info[:3])),
    "release_manifest_sha256": digest(manifest_path),
    "repository": repository,
    "rollback_capability_sha256": rollback_capability_sha256,
    "rollback_capture_id": f"{rollback_capture_id}-{source_commit[:12]}",
    "run_attempt": run_attempt,
    "run_id": run_id,
    "schema": authority_schema,
    "source_commit": source_commit,
    "target_directory": target_directory,
    "workflow": workflow,
}
canonical = json.dumps(
    payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=True,
).encode("ascii")
receipt_hash = hashlib.sha256(canonical).hexdigest()
payload["receipt_sha256"] = receipt_hash
rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
descriptor = os.open(state_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "w", encoding="ascii", newline="\n") as handle:
    handle.write(rendered)
verified = json.loads(
    state_path.read_text(encoding="ascii"),
    object_pairs_hook=strict_object,
    parse_constant=reject_constant,
)
if verified != payload or digest(state_path) != hashlib.sha256(rendered.encode("ascii")).hexdigest():
    fail("rollback authority did not survive write verification")
print(receipt_hash)
PY
)"
[[ "$rollback_authority_sha256" =~ ^[0-9a-f]{64}$ ]] || die "rollback authority digest is invalid"

deployment_started=0
printf 'PUBLIC_SITE_SOURCE_COMMIT=%s\n' "$source_commit"
printf 'PUBLIC_SITE_RUN_ID=%s\n' "$run_id"
printf 'PUBLIC_SITE_RUN_ATTEMPT=%s\n' "$run_attempt"
printf 'PUBLIC_SITE_ROLLBACK_DIR=%s\n' "$rollback_dir"
printf 'PUBLIC_SITE_ROLLBACK_AUTHORITY_SHA256=%s\n' "$rollback_authority_sha256"
printf '%s\n' '--- remote pre-deploy identity ---'
cat "$rollback_dir/pre-deploy.tsv"
printf '%s\n' '--- exact post-deploy identity ---'
cat "$rollback_dir/post-deploy.tsv"
printf '%s\n' 'PUBLIC_SITE_DEPLOYMENT_OK'
