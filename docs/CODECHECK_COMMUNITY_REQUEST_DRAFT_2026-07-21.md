# CODECHECK Community Request Draft

Status: `ACTION_TIME_READY_CANDIDATE_UNASSIGNED_NO_SEND`

This is an author-side draft. It has not been posted, emailed, submitted, assigned, or accepted. Candidate `2026-022` was clear at the latest live recheck but is not reserved. At action time, recheck the production register and use the current CODECHECK Launch Pad or the official register issue route. Stop if the identifier or labels cannot be verified.

The public preprint and exact source are frozen at commit `1c0eb51754beffac6f4df484914e35efc21c253f`. Open register issue [#199](https://github.com/codecheckers/register/issues/199) already uses `2026-021`. A later production-register search found no `2026-022` issue and no Ashworth issue. That makes `2026-022` a candidate only, not an assignment or reservation. Recheck immediately before action and stop on any collision.

Official routes checked again on 2026-07-22:

- Author guide: https://codecheck.org.uk/guide/community-workflow-author
- Configuration specification: https://codecheck.org.uk/spec/config/1.0/
- Launch Pad: https://codecheck.org.uk/launch-pad/

## Official Author-Package Contract

The frozen commit contains the three author-side files required by the current community guide:

- root `README.md` with the hash-locked Ubuntu execution commands,
- root `codecheck.yml` with the six-output manifest and scholarly-work metadata,
- root `LICENSE` with the MIT software license and separate EIA data-use notice.

The frozen package contains the declared code and data. Checker-managed fields such as `codechecker`, `report`, `certificate`, and `check_time` remain absent until an independent codechecker supplies them.

## Launch Pad Fields

### Author Names

Robert Ashworth

### Assign Codecheckers

Leave unassigned. CODECHECK or a consenting independent volunteer must supply this field.

### Issue Title

`Ashworth | 2026-022`

### Labels

- `community`
- `needs codechecker`
- `id assigned`

These labels were verified against the current production-register pattern. Recheck that they still exist immediately before action.

### Issue Description

**Work**: Robert Ashworth, "A Bounded Reproducibility Capsule for Public-Data Benchmarking and Preserved Negative Gates." Public preprint: https://raw.githubusercontent.com/robertashworth1986-debug/lumen-core-public/1c0eb51754beffac6f4df484914e35efc21c253f/docs/preprint/BOUNDED_REPRODUCIBILITY_CAPSULE_PREPRINT_2026-07-21.pdf. The manuscript is a bounded executable-computation study; it is not a field-performance, agency-approval, savings, trading, patent, or valuation claim.

**Repository and workflow**: immutable source commit https://github.com/robertashworth1986-debug/lumen-core-public/commit/1c0eb51754beffac6f4df484914e35efc21c253f. The root `README.md`, `codecheck.yml`, and `LICENSE` provide the execution instructions, six-file manifest, code license, and EIA data-use notice. The frozen input and hash-locked Ubuntu 24.04 / CPython 3.11.9 / glibc 2.39 dependency environment are included. First run `python code/ops/VERIFY_CODECHECK_REVIEWER_RUNTIME.py --check-only`; then run `python code/ops/RUN_REVIEWER_REPRODUCIBILITY_CAPSULE.py --with-fixture-tests --run-dir out/codecheck_eia --publish`.

**Bounded ask**: Independently execute the reviewed immutable source snapshot, recreate all six manifest outputs, and document which declared assertions reproduced. Please preserve every negative promotion and coverage gate. The author-side clean-runner receipt is first-party evidence only and must not be treated as the independent result.

**Known limitations**: The capsule uses a dated frozen EIA-derived panel and one deterministic synthetic suite. It does not validate the live prospective router or establish scientific, operational, economic, agency, patent, trading, or company-valuation conclusions.

## Action-Time Gates

1. Keep the commit-pinned public preprint and the 30-file computational-core identity register reconciled to source commit `1c0eb51754beffac6f4df484914e35efc21c253f`.
2. Reconcile Gmail, GitHub, and local outreach registries immediately before action to prove no prior CODECHECK request would be duplicated.
3. Robert reviews the public manuscript, issue body, source commit, license, and bounded ask.
4. Recheck that `2026-022` is unused and that all three labels remain valid.
5. Obtain a fresh action-time HumanUnlock from Robert for exactly one production-register issue titled `Ashworth | 2026-022`.
6. Open exactly one issue. Do not send a parallel team email.
7. Record the resulting issue URL and timestamp; keep assignment, execution, certificate, and external-validation fields false until CODECHECK supplies evidence.
