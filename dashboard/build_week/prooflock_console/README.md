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
python -m http.server 8080
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

ProofLock verifies receipt integrity and decision authority. It does not provide
certification, field validation, guaranteed ROI, realized savings, production
approval, or qualified legal, regulatory, scientific, or engineering review.
