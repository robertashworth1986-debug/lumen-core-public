# Live Domain Hash Table Unlock

Generated UTC: `2026-06-27T20:26:00Z`

## Current Truth

The local proof stack is ready, but the live domain is not yet serving the required proof feeds. The current verifier shows:

- Required local feeds ready: `7/7`
- Required hosted hash matches: `0/7`
- Domain state: `LOCAL_READY_DOMAIN_NOT_VERIFIED_OR_STALE`
- Current blocking condition: VPS SSH public-key authentication failed for `opc@157.151.148.234`
- Glyph drive mirror: `E:\LumaProofVault\LIVE_DOMAIN_HASH_TABLE_UNLOCK_20260627T201823Z`

This means the hash table is not blocked by missing benchmark work. It is blocked by publishing the already-built JSON feeds to the live web root and re-running the verifier.

## How To Unlock It

1. Confirm the correct VPS SSH key or user for `157.151.148.234`.
   - The attempted key was `C:\Users\Novac\.ssh\id_rsa`.
   - The remote rejected it with `Permission denied (publickey,gssapi-keyex,gssapi-with-mic)`.
2. Run the feed-only deploy script:
   `.\deploy\PUSH_PROOF_FEEDS_TO_VPS.ps1 -BundleRoot "C:\LumaTrader\INSTITUTIONAL_STACK_V2\.deploy_stage\live_domain_proof_feeds_20260627T195816Z"`
3. Verify hosted hashes:
   `python .\code\ops\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py --timeout 8`
4. Only after `required_remote_hash_match_count` reaches `7` should reviewer emails or grant packets point at the live JSON feeds.

## Answers To The Next Questions

**Which required proof feed is missing or stale on the live domain?**

All seven required feeds are currently missing or stale on the hosted domain: `champion_metric_gauntlet`, `kuramoto_holdout_expansion`, `geometry_champion_of_champions`, `field_money_truth_sweep`, `live_proof_value_meter`, `field_validated_dollar_claim_ladder`, and `dollar_claim_gate`.

**What exact URL should a reviewer open first?**

After the hashes verify, send reviewers to `https://lumen-core.ai/mission_control.html` first, then the grants console at `https://lumen-core.ai/grants.html?grant_id=nsf_sbir_phase_i`. Do not point them to the proof-feed URLs until the verifier reports hosted hash matches.

**Which claim is safe once hosted hashes match?**

Safe: “The public domain is serving the same hash-verified internal proof feeds used by the submission packet.”  
Not safe yet: field validation, realized dollar savings, a fixed dollar value per frozen delta, live trading edge, medical efficacy, or guaranteed awards.

**What still blocks field validation after deployment is verified?**

A named buyer/operator must authorize a field replay on their system, define the baseline, define the acceptance metric, and sign off on before/after measurement. Internal live-data benchmarks can justify the request, but they are not a substitute for buyer-authorized field validation.

**What buyer-authorized replay would turn this from internal proof into a field claim?**

The fastest high-value replay is a narrow energy/grid or maritime operations replay: one operator-owned dataset, one baseline, one LumenCore champion, one acceptance metric, and a signed result. That creates a real pilot claim instead of a broad theoretical valuation claim.

## Email Readiness

Yes, bounded outreach can start now, but only as pilot/discovery outreach. Do not sell frozen deltas as fixed-price assets yet. The correct ask is:

> We have hashable internal benchmark evidence and are looking for a buyer/operator willing to run a bounded field replay against their baseline. If the replay shows measurable improvement, we can discuss pilot scope, licensing, or sponsored validation.

## Why This Is Worth Something

The current value is not a guaranteed dollar claim. The value is an evidence-backed pilot opportunity: a reviewer or buyer can see that the work is measured, hashed, reproducible, and bounded by claim gates. The commercial unlock happens when a third party lets us replay the champion against their live or historical operational baseline and the result holds.
