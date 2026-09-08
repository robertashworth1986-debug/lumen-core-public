# Constraint discovery: signals first, savings only after measurement

This bounded research lane captures public provider status reports and optionally reads up to ten new posts from each of three technical Reddit communities. It never posts, messages, probes customer systems, alters accounts, or deploys anything. No schedule is installed.

## Existing ecosystem integration
The three Reddit environment-variable names match `code/social_platform_profile_engine_v1.py`: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_REFRESH_TOKEN. A configuration entry is not proof of working credentials. Missing runtime values, HTTP failures, and incomplete source reads remain explicit HOLD states. No secret values or token responses are stored. Reddit usernames and post bodies are not retained. Public post titles and canonical links are leads, not verified fault reports. Provider reports are not independent measurements.

## Run once
```
python -m unittest discover -s experiments/constraint_discovery -p 'test_*.py' -v
python experiments/constraint_discovery/constraint_watch.py --out out/constraint-discovery/NEW_UNIQUE_CAPTURE --with-reddit
```
Use only authorized Reddit access in accordance with provider terms and account permissions. Do not place credentials in code or messages. Cached web results are not proof of real-time Reddit ingestion. The code rejects stale/future-dated posts and records capture time separately from provider event time. Output folders cannot be overwritten.

## Delta gate
`paired_mae(rows, protocol)` is a minimal descriptive scorer for caller-provided, matched target rows. It rejects missing/non-finite truth, duplicates, and missing declared input/protocol identities; retains losses; and never converts forecast error into money. It does not itself verify data ownership, hash provenance, chronological availability, causal identification, significance, or a globally optimal solution. Full research promotion still needs the stronger existing replay protocol and independent review. The 24 tests include synthetic examples solely for software behavior, not measured field improvements.

A commercial test must name the data owner, real incumbent, feasible alternative, locked primary metric, adverse slices, acquisition window, constraints, acceptance rule, deployment cost and economic denominator. Revenue, market size, and total industry spending are not automatically addressable costs.

## Public seed leads identified September 7 Central / September 8 UTC
- Public Reddit VPN recovery-dependency report: https://www.reddit.com/r/sysadmin/comments/1vvfb7y/ . Cached web copy: freshness unverified; author reported recovery. Hypothesis: authorized independent recovery-path review. Not a current verified outage.
- Public Reddit Intune update report: https://www.reddit.com/r/sysadmin/comments/1vup66w/ . Cached copy, date unverified. Hypothesis: compare configured policy with actual patch outcome. Microsoft corroborates the general distinction, not this user's incident: https://learn.microsoft.com/en-us/troubleshoot/mem/intune/device-protection/troubleshoot-update-rings .
- Public Reddit storage support-cost report: https://www.reddit.com/r/sysadmin/comments/1vuts15/ . Unverified quotation, not a verified price or savings opportunity. Hypothesis: owner-approved three-year TCO comparison under support and recovery constraints.
- Cloudflare account invitation issue: https://www.cloudflarestatus.com/incidents/pjr4m9q1xxb1 . Provider-reported account-management incident; vendor-published workaround is not a LumenCore invention or measured gain. Live state can change.

No lead has a measured LumenCore delta or verified dollar saving. Source hashes prove what was captured, not that a report is true. Do not associate public posts with inferred employers or solicit private data.

## Continuity
Related research review: PR #215 and issue #214. Stage 6 remains internal reused-data research; no field-performance or revenue promotion. This lane is isolated from main, the production gateway, source-count claims, DNS and lumen-core.ai. Private course emails, assessment reports and founder notes do not belong in this public repository.
