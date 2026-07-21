#!/usr/bin/env bash
set -euo pipefail

umask 022

if [[ -z "${CODECHECK_SOURCE_COMMIT:-}" ]]; then
  echo "CODECHECK_SOURCE_COMMIT is required" >&2
  exit 64
fi
if [[ ! -f /input/RELEASE_MANIFEST.json ]]; then
  echo "The read-only input must be a release-bundle root" >&2
  exit 65
fi
if find /output -mindepth 1 -print -quit | grep -q .; then
  echo "The output mount must be empty" >&2
  exit 66
fi

mkdir -p /work/repo
cp -a /input/. /work/repo/
cd /work/repo

CODECHECK_RUN_DIR=out/codecheck_eia
copy_capsule_outputs() {
  if [[ -d "${CODECHECK_RUN_DIR}" ]]; then
    cp -a "${CODECHECK_RUN_DIR}/." /output/ || true
  fi
}
trap copy_capsule_outputs EXIT

python code/ops/VERIFY_CODECHECK_REVIEWER_RUNTIME.py \
  --output /output/runtime_receipt.json \
  --source-commit "${CODECHECK_SOURCE_COMMIT}"
python code/ops/VERIFY_REVIEWER_DEPENDENCY_LOCK.py
python -m pip check
python code/ops/RUN_REVIEWER_REPRODUCIBILITY_CAPSULE.py \
  --with-fixture-tests \
  --run-dir "${CODECHECK_RUN_DIR}"
copy_capsule_outputs
trap - EXIT

python - <<'PY'
import json
from pathlib import Path

runtime = json.loads(Path("/output/runtime_receipt.json").read_text(encoding="utf-8"))
capsule = json.loads(
    Path("/output/reviewer_reproducibility_receipt.json").read_text(
        encoding="utf-8"
    )
)
assert runtime["passed"] is True
assert runtime["independent_execution_complete"] is False
assert runtime["external_validation_complete"] is False
assert capsule["status"] == "BOUNDED_REPRODUCIBILITY_PASS"
assert capsule["summary"]["suite_pass_count"] == capsule["summary"]["suite_count"] == 3
assert capsule["summary"]["assertion_pass_count"] == capsule["summary"]["assertion_count"] == 31
assert capsule["summary"]["external_validation_complete"] is False
PY
