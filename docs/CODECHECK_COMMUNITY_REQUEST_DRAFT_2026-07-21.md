# CODECHECK Community Request Draft

Status: `HOLD_IDENTIFIER_COLLISION_DUPLICATE_RECHECK_AND_HUMANUNLOCK`

This is an author-side draft. It has not been posted, emailed, submitted, assigned, or accepted. At action time, use the current CODECHECK Launch Pad and do not invent or reserve a certificate identifier outside that process.

The public preprint and exact source are frozen at commit `1c0eb51754beffac6f4df484914e35efc21c253f`. A 2026-07-21 Launch Pad preflight exposed an identifier collision: the proposed `2026-021` identifier was already present in [open register issue #199](https://github.com/codecheckers/register/issues/199) without the `id assigned` label. Do not create a production issue until the Launch Pad or register state resolves that collision and a fresh preflight returns one unambiguous identifier.

Official routes checked on 2026-07-21:

- Author guide: https://codecheck.org.uk/guide/community-workflow-author
- Configuration specification: https://codecheck.org.uk/spec/config/1.0/
- Launch Pad: https://codecheck.org.uk/launch-pad/

## Launch Pad Fields

### Author Names

Robert Ashworth

### Assign Codecheckers

Leave unassigned. CODECHECK or a consenting independent volunteer must supply this field.

### Issue Title

`[IDENTIFIER_ASSIGNED_AT_ACTION_TIME] Ashworth - A Bounded Reproducibility Capsule for Public-Data Benchmarking and Preserved Negative Gates`

### Labels

Select the current CODECHECK community and needs-codechecker labels offered by the production Launch Pad. Do not guess stale label names.

### Issue Description

**Work**: Robert Ashworth, "A Bounded Reproducibility Capsule for Public-Data Benchmarking and Preserved Negative Gates." Public preprint: https://raw.githubusercontent.com/robertashworth1986-debug/lumen-core-public/1c0eb51754beffac6f4df484914e35efc21c253f/docs/preprint/BOUNDED_REPRODUCIBILITY_CAPSULE_PREPRINT_2026-07-21.pdf. The manuscript is a bounded executable-computation study; it is not a field-performance, agency-approval, savings, trading, patent, or valuation claim.

**Repository and workflow**: immutable source commit https://github.com/robertashworth1986-debug/lumen-core-public/commit/1c0eb51754beffac6f4df484914e35efc21c253f. The root `README.md`, `codecheck.yml`, and `LICENSE` provide the execution instructions, six-file manifest, code license, and EIA data-use notice. The frozen input and hash-locked Ubuntu 24.04 / CPython 3.11.9 / glibc 2.39 dependency environment are included. First run `python code/ops/VERIFY_CODECHECK_REVIEWER_RUNTIME.py --check-only`; then run `python code/ops/RUN_REVIEWER_REPRODUCIBILITY_CAPSULE.py --with-fixture-tests --run-dir out/codecheck_eia`.

**Bounded ask**: Independently execute the reviewed immutable source release, recreate all six manifest outputs, and document which declared assertions reproduced. Please preserve every negative promotion and coverage gate. The author-side clean-runner receipt is first-party evidence only and must not be treated as the independent result.

**Known limitations**: The capsule uses a dated frozen EIA-derived panel and one deterministic synthetic suite. It does not validate the live prospective router or establish scientific, operational, economic, agency, patent, trading, or company-valuation conclusions.

## Action-Time Gates

1. Keep the commit-pinned public preprint and all 44 release-input hashes reconciled to source commit `1c0eb51754beffac6f4df484914e35efc21c253f`.
2. Reconcile Gmail, GitHub, and local outreach registries immediately before action to prove no prior CODECHECK request would be duplicated.
3. Robert reviews the public manuscript, issue body, source commit, license, and bounded ask.
4. Obtain a fresh action-time HumanUnlock from Robert for exactly one production-register issue.
5. Confirm the production Launch Pad reports no identifier collision and assigns one unambiguous identifier.
6. Open exactly one issue through the current production Launch Pad.
7. Record the resulting issue URL and timestamp; keep assignment, execution, certificate, and external-validation fields false until CODECHECK supplies evidence.
