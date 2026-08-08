# LumenCore Public Assurance Quick Start

This is the shortest institutional review path for the canonical public evidence surface.

It runs two independent fail-closed checks from one command:

1. the merged Proof Capsule verifier v2 against the public replay capsule; and
2. the External Replication Docket validator against the canonical unassigned `HOLD` template.

The runner then records the exact public result from each validator plus SHA-256 and byte counts for every listed source file.

## Run

From a clean checkout:

```bash
python code/ops/run_public_assurance_suite.py \
  --root . \
  --commit "$(git rev-parse HEAD)" \
  --out public_assurance_receipt.json
```

PowerShell:

```powershell
$sha = git rev-parse HEAD
python code/ops/run_public_assurance_suite.py `
  --root . `
  --commit $sha `
  --out public_assurance_receipt.json
```

## Expected bounded result

The aggregate receipt must report:

- `valid: true`;
- two completed checks;
- Proof Capsule verifier version `2.0`;
- public replay evidence with decision `external_review`;
- replication docket state `template_unassigned`;
- replication docket decision `hold`;
- `safe_for_external_validation_claim: false`;
- SHA-256 and byte counts for the canonical validator and fixture files.

A passing assurance receipt proves only that the listed public validators executed successfully against the listed bytes and returned the expected bounded contracts.

It does **not** reproduce a private experiment, authenticate a reviewer, establish external or field validation, certify a system, authorize deployment, prove savings, or establish customer adoption.

## Failure behavior

The suite fails closed on:

- a missing or changed source file;
- an escaping or non-canonical source path;
- a nonzero validator exit;
- invalid or duplicate-key JSON;
- non-finite JSON values;
- stdout or stderr beyond the capture budget;
- timeout;
- result-contract drift;
- duplicate check identifiers;
- an invalid commit identifier.

Commands are executed as argument arrays with `shell=False` under a reduced public environment. No credentials, API keys, portal sessions, network calls, or private datasets are required.

## Reviewer sequence

1. Check out the exact commit.
2. Run the command above.
3. Inspect `public_assurance_receipt.json`.
4. Compare the recorded source SHA-256 values with the checked-out files.
5. Read the Proof Capsule and External Replication Docket claim boundaries.
6. Decide whether to reject, request information, preregister an outside evaluation, or scope a buyer-controlled test.

**Evidence before claims. Bounded light speed.**
