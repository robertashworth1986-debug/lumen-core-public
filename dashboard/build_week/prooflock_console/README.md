# ProofLock Console

ProofLock is a static, offline-capable decision-control verifier. It checks a
canonical JSON receipt, rehashes same-origin public artifacts, derives the
machine-verifiable custody and lineage gates, and refuses to accept a
self-authored `PASS` for baseline, held-out evaluation, independent-review, or
human-release authority.

## Primary customer problem

Teams often have a promising demo or benchmark but no defensible boundary
between what their own artifacts show and what a buyer, evaluator, or decision
owner is allowed to conclude. ProofLock prevents an internally written receipt
from converting custody, a replay, or an asserted gate into a promotion claim.

It does not determine whether the candidate performs well. The companion
bounded validation sprint supplies the named baseline, locked metric, held-out
rules, negative-result register, and decision owner.

## Run locally

From the repository root:

```powershell
python -m http.server 8080 --directory dashboard
```

Then open:

```text
http://127.0.0.1:8080/build_week/prooflock_console/
```

The public deployment target is:

```text
https://lumen-core.ai/build_week/prooflock_console/
```

## Demonstration

1. Load the bundled bounded-validation protocol receipt.
2. Verify that artifact identity and protocol lineage pass.
3. Confirm that baseline, held-out evaluation, independent review, and human
   release remain open.
4. Run the guided authority attack. ProofLock recomputes an internally valid
   receipt after self-asserted `PASS` values and still refuses promotion.
5. Restore and export the verification report.

## Security boundary

- Artifact paths are restricted to same-origin `assets/` files.
- Canonical SHA-256 identity detects byte changes but does not authenticate the
  author or establish the truth of the artifact's substantive claim.
- A self-authored receipt may preserve a hold or failure; it cannot mint
  independent authority.
- No production credential, private evidence root, live trading authority, or
  external submission capability is present.

## Receipt identity versions

The retained sample is v1 and keeps its original bytes and SHA-256. The v1
compatibility verifier now accepts only safe integer number values, ASCII
object keys, valid Unicode strings without DEL (U+007F), and ordinary JSON
data types. Raw v1 numeric tokens must be integer lexemes: `1.0`, `1e-6` and
signed zero are rejected rather than being silently reinterpreted or resealed.
Unicode string values remain supported; non-ASCII object keys require v2.
This restricted subset preserves portable historical v1 identities. Existing
v1 receipts outside it need an explicit review and new version, not a new hash
written over their historical identity. An already parsed JavaScript object
does not retain a numeric token's spelling; external input must use the strict
raw-text parser, as the browser and Python CLI now do.

For a new numeric/Unicode receipt, use schema
`lumencore.prooflock_receipt.v2` and set `canonicalization` to
`lumencore.prooflock_c14n.binary64.v2`. The precise language-independent
identity contract is in [CANONICALIZATION.md](CANONICALIZATION.md). V2 normalizes
numeric values to finite IEEE-754 binary64 bytes, orders keys by Unicode scalar
value and defines string escaping explicitly. It is a tagged serialization
contract, not a claim of RFC 8785/JCS conformance. Exact decimal quantities or
large integers must be stored as strings with a separately agreed unit/format.

Both raw receipt and manifest entrypoints reject duplicate decoded keys,
unpaired surrogates, nonfinite numbers, unsafe integers, excessive nesting and
oversized JSON text before they can lose evidence during parsing. Artifact
SHA-256 still binds raw artifact bytes; receipt SHA-256 binds the declared
canonical payload, excluding only `receipt_sha256`.

`python dashboard/build_week/prooflock_console/verify_receipt.py` verifies the
retained demo. `--write-hash` is an explicit local reseal in the receipt's
declared schema and refuses nonportable v1 values; it never upgrades a schema.
To prepare v2, retain the original file, make a separately named copy, change
its schema and add the exact canonicalization identifier before explicitly
sealing that copy. Keep the old receipt identity in the review record. No
version or reseal can mint external authority or permit a self-issued PROMOTE.

ProofLock verifies receipt integrity and decision authority. It does not provide
certification, field validation, guaranteed ROI, realized savings, production
approval, or qualified legal, regulatory, scientific, or engineering review.
