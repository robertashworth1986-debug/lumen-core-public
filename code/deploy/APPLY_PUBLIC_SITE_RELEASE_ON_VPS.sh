#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

readonly REQUIRED_APPROVAL="DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT"
readonly PRODUCTION_TARGET="/opt/lumencore/dashboard"
readonly PRODUCTION_ROLLBACK_BASE="/opt/lumencore/rollbacks/public-site"
readonly MANIFEST_SCHEMA="lumencore.public_site_release_manifest.v1"
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

die() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

usage() {
  cat >&2 <<'EOF'
Usage: APPLY_PUBLIC_SITE_RELEASE_ON_VPS.sh \
  --archive PATH --manifest PATH --source-commit FULL_SHA \
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
    *)
      usage
      ;;
  esac
done

[[ "$approval" == "$REQUIRED_APPROVAL" ]] || die "explicit public-site deployment approval is required"
[[ "$source_commit" =~ ^[0-9a-f]{40}$ ]] || die "source commit must be a full lowercase SHA-1"
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

for command_name in python3 sha256sum stat cp cmp install date mktemp realpath; do
  command -v "$command_name" >/dev/null 2>&1 || die "missing required command: $command_name"
done

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
[[ "$(realpath -m -- "$rollback_base")" == "$rollback_base" ]] || die "rollback path cannot traverse a symlink"
[[ ! -L "$rollback_base" ]] || die "rollback directory cannot be a symlink"
install -d -m 0750 -- "$rollback_base"
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

deployment_started=0
printf 'PUBLIC_SITE_SOURCE_COMMIT=%s\n' "$source_commit"
printf 'PUBLIC_SITE_ROLLBACK_DIR=%s\n' "$rollback_dir"
printf '%s\n' '--- remote pre-deploy identity ---'
cat "$rollback_dir/pre-deploy.tsv"
printf '%s\n' '--- exact post-deploy identity ---'
cat "$rollback_dir/post-deploy.tsv"
printf '%s\n' 'PUBLIC_SITE_DEPLOYMENT_OK'
