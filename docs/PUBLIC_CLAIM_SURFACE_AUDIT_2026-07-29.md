# Public Claim Surface Audit

Audit date: `2026-07-29` UTC

## Scope

This was a bounded, read-only claim-surface audit of:

- public dashboard HTML and JSON under `dashboard/`
- reviewer-facing Markdown under `docs/`
- reviewer and submission Markdown under `grant_submissions/`

The scan targeted Kuramoto champion marketing, `$39,595,200`,
`$4,520/hour`, estimated or realized savings, `money printer`, universal
superiority, and language that could make public hash verification look like
performance proof. No source artifact, generator, public page, remote service,
message, or deployment was changed.

## Governing Truth

The following current generated artifacts are the claim authority for this
audit:

- `docs/KURAMOTO_CROSS_SECTOR_BENCHMARK_2026-07-28.md:3-12` records
  `NO_CROSS_SECTOR_EFFICIENCY_GAIN_PROVEN`, no positive sector result, and
  rejects the old coefficient-driven 24/24 result as real-data performance
  evidence.
- `docs/KURAMOTO_CROSS_SECTOR_BENCHMARK_2026-07-28.md:16-20` records six
  admitted retrospective sources and zero proven sector gains.
- `docs/KURAMOTO_CROSS_SECTOR_BENCHMARK_2026-07-28.md:71-75` says not to
  market a Kuramoto efficiency gain and blocks field performance, realized
  savings, external validation, trading edge, and unbeatable claims.
- `out/ops/proof_to_revenue_engine_latest.json:90-112` keeps cross-sector
  marketing, field-validation language, modeled dollar projections, and
  realized-savings claims closed; its safe dollar values are both `0.0`.
- `dashboard/data/live_proof_value_meter.json:2-9` says no dollar projection
  is currently claimable.
- `dashboard/data/live_proof_value_meter.json:26-43` records zero allowed
  estimated-value claims and zero allowed hourly and annual values.
- `dashboard/data/dollar_claim_gate.json:2-10` is current generated output and
  records zero allowed estimated-value claims and zero allowed dollar values.
- `dashboard/data/live_domain_deployment_feed.json:2` correctly states that
  matching hosted hashes prove byte identity only, not field validation,
  realized savings, or performance.

## Ranked Findings

### CRITICAL-1: Stale dollar claims are confirmed on live-matched JSON feeds

The current zero-dollar controls conflict with older generated JSON that still
publishes `$4,520/hour` and `$39,595,200/year` as safe or allowed. These are
not merely dormant local records. The current deployment feed reports matching
hosted hashes for several of them:

| Public JSON | Contradictory lines | Live-hash evidence |
| --- | --- | --- |
| `dashboard/data/champion_metric_gauntlet.json` | `664-697` | `dashboard/data/live_domain_deployment_feed.json:20-51` |
| `dashboard/data/geometry_champion_of_champions.json` | `23-24`, `420-421` | `dashboard/data/live_domain_deployment_feed.json:137-168` |
| `dashboard/data/field_money_truth_sweep.json` | `4-5`, `68-69` | `dashboard/data/live_domain_deployment_feed.json:176-207` |
| `dashboard/data/field_validated_dollar_claim_ladder.json` | `48`, `117-119`, `161-162`, `179` | `dashboard/data/live_domain_deployment_feed.json:254-285` |
| `dashboard/data/field_validation_outreach_board.json` | `101-102`, `467-469` | `dashboard/data/live_domain_deployment_feed.json:371-402` |

Additional optional feeds are also reported as live hash matches and preserve
the same stale dollar posture:

- `dashboard/data/valuation_proposal_target_packet.json:38-39` with live-hash
  evidence at `dashboard/data/live_domain_deployment_feed.json:722-753`
- `dashboard/data/champion_metric_battery.json:324-325` with live-hash evidence
  at `dashboard/data/live_domain_deployment_feed.json:917-948`
- `dashboard/data/champion_expanded_metric_rollup.json:22-23` with live-hash
  evidence at `dashboard/data/live_domain_deployment_feed.json:956-987`
- `dashboard/data/first_buyer_target_board.json:297-298` with live-hash evidence
  at `dashboard/data/live_domain_deployment_feed.json:1034-1065`
- `dashboard/data/luma_operator_context.json:5-6` with live-hash evidence at
  `dashboard/data/live_domain_deployment_feed.json:1112-1143`

Impact: a reviewer can retrieve a hash-matched public artifact that directly
contradicts the current governed value gate. A disclaimer that the amount is
"estimated" does not cure the contradiction because the current gate permits
no modeled dollar projection at all.

### CRITICAL-2: A live-matched feed uses "money-printer" marketing and conflates hashes with skill

`dashboard/data/champion_stress_test_matrix.json:811` calls Kuramoto the
"current money-printer truth line," labels it a strong internal champion,
states 24/24 wins, and places "public hash-verified feeds" in the same proof
sentence. The deployment feed reports that exact optional artifact as a live
hash match at `dashboard/data/live_domain_deployment_feed.json:878-909`.

The reviewer-facing counterpart repeats the same language at
`docs/CHAMPION_STRESS_TEST_MATRIX_2026-06-27.md:6-12`.

Impact: this is the highest-risk phrasing in the scanned surface. Hashes prove
artifact identity and custody, not model skill. "Money-printer" also conflicts
with the current negative cross-sector result and with the block on performance
and dollar marketing.

### HIGH-1: The current portal still presents Kuramoto as a reviewer-safe winner

The current generated HTML has corrected dollar values but retains model
marketing:

- `dashboard/dashboard_portal.html:94` leads with `24/24` under the
  Proof-to-Pilot field-validation gate.
- `dashboard/dashboard_portal.html:96` labels the section
  "Reviewer-Safe Winner State" and names Kuramoto as the "Current strongest
  family."
- `dashboard/dashboard_portal.html:107` embeds Kuramoto as
  `champion_family` with 24/24 wins in the page payload.
- `dashboard/dashboard_portal.html:96-99` links reviewers directly to the stale
  `champion_metric_gauntlet.json` and field-validation feeds.

Impact: this is current generated HTML, not historical material. Its first-view
framing omits the governed 0/6 cross-sector result and can cause the narrow
retrospective result to be read as the current model-performance conclusion.

### HIGH-2: The linked champion gauntlet contradicts the repaired engine

`dashboard/data/champion_metric_gauntlet.json` is a stale generated artifact,
not a historical document:

- lines `34-45` allow "current internal champion" language
- lines `54-96` bind hashes to the champion and dollar-claim feeds
- lines `664-697` set `internal_champion` true, call Kuramoto the current
  champion, allow a bounded estimated-value claim, and publish the old hourly
  and annual values

The repaired engine blocks broad internal champion marketing and all modeled
dollar projection at `out/ops/proof_to_revenue_engine_latest.json:90-112`.

Impact: the current portal sends reviewers to the older artifact, and the live
deployment feed confirms that the older artifact is hash matched remotely.

### HIGH-3: Public outreach and reviewer templates still promote the stale result

The following generated or reviewer-facing surfaces preserve the 24/24
Kuramoto story as current outreach language without carrying the 0/6 governed
cross-sector decision:

- `dashboard/data/field_validation_outreach_board.json:5-21`
- `dashboard/data/first_buyer_target_board.json:257`
- `dashboard/data/outreach_and_application_send_queue.json:6`, `26`, `46`
- `dashboard/data/valuation_proposal_target_packet.json:180`
- `dashboard/data/luma_operator_context.json:308-310`, `510`
- `dashboard/data/field_validation_control_room.json:49-77`, `364-397`
- `docs/EPRI_AI_FOR_POWER_FIELD_REPLAY_OUTREACH_2026-07-01.md:27`
- `docs/FIRST_BUYER_TARGET_BOARD_2026-06-27.md:102`
- `docs/FIELD_VALIDATION_OUTREACH_BOARD_2026-06-29.md:201`, `229`, `254`
- `docs/OUTREACH_VALIDATION_APPLICATION_PACKET_2026-07-03.md:106-136`,
  `169-218`, `318`
- `grant_submissions/funding_sprint_20260709/TECHNICAL_GOV_REVIEWER_APPROVAL_STACK_2026-07-09.md:29-37`,
  `56`

Several include a later boundary sentence, but they still lead with a result
that the current engine explicitly suppresses from model-performance
marketing. Hash availability beside the 24/24 wording increases the risk that
custody proof will be mistaken for performance validation.

### MEDIUM-1: Historical claim documents remain in active reviewer paths

The following date-stamped documents are historical, but they remain under the
active `docs/` or `grant_submissions/` roots and have no supersession banner:

- `docs/CLAIM_STRENGTH_VALUE_UNLOCK_MAP_2026-06-25.md:12`, `33`
- `docs/CHAMPION_METRIC_GAUNTLET_2026-06-27.md:49-50`
- `docs/CURRENT_LUMA_PROOF_AND_GRANT_STATE_2026-06-24.md:40`
- `docs/CURRENT_LUMA_PROOF_AND_GRANT_STATE_2026-06-29.md:195`
- `docs/CURRENT_LUMA_PROOF_STATE_2026-06-25.md:66`
- `docs/CURRENT_LUMA_PROOF_STATE_2026-06-26.md:37-38`
- `docs/FIELD_MONEY_TRUTH_SWEEP_2026-06-25.md:16`, `39`
- `docs/FIELD_VALIDATED_DOLLAR_CLAIM_LADDER_2026-06-27.md:14`, `20-21`, `43`
- `docs/FIELD_VALIDATION_OUTREACH_BOARD_2026-06-29.md:21`
- `docs/GEOMETRY_ASSET_WIRING_BOARD_2026-06-25.md:21`
- `docs/GEOMETRY_CHAMPIONSHIP_BRIDGE_2026-06-21.md:49`
- `docs/GEOMETRY_CHAMPION_OF_CHAMPIONS_2026-06-23.md:26`
- `docs/GEOMETRY_LIVE_BREADTH_PROOF_QUEUE_2026-06-22.md:11`
- `docs/LIVE_PROOF_VALUE_METER_2026-06-22.md:9`, `23-24`
- `docs/LUMA_CONTEXT_DASHBOARD_PARITY_AUDIT_2026-06-22.md:64`
- `docs/LUMA_OPERATOR_CONTEXT_2026-07-01.md:69-70`
- `docs/LUMENCORE_BUSINESS_PLAN_INVESTOR_READY_UPDATED_2026-07-03.md:63`
- `docs/OUTREACH_VALIDATION_APPLICATION_PACKET_2026-07-03.md:56`
- `docs/VALUATION_PROPOSAL_TARGET_PACKET_2026-06-26.md:52`
- `grant_submissions/LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md:29-30`
- `grant_submissions/LIVE_BREADTH_REPLAY_BRIDGE_2026-06-20.md:26`
- `grant_submissions/funding_sprint_20260709/REVIEWER_APPROVAL_CROSSWALK_2026-07-09.md:93`

No explicit `archive/` or `historical/` path was found in the scoped document
roots. The date in a filename is therefore the only practical stale-state cue
for a reviewer.

### INFO-1: Current canonical outputs do preserve the right boundaries

The scan did not find an affirmative current canonical claim of realized
savings or universal superiority. Those phrases generally appear in explicit
deny lists or claim boundaries. The repaired proof-to-revenue engine, current
value meter, current dollar gate, cross-sector benchmark, and
`docs/REVIEWER_START_HERE.md:7` are aligned.

The problem is publication precedence: stale generated feeds and historical
reviewer language remain reachable beside the corrected artifacts, so a
reviewer has no reliable way to know which one governs.

## Smallest Safe Fix Sequence

1. **Establish one public authority.** Make the current cross-sector benchmark
   status and repaired proof-to-revenue claim controls the only source for
   Kuramoto, dollar, and hash-language fields.
2. **Suppress the confirmed live contradictions first.** Remove public
   navigation to, or fail-closed regenerate, the six highest-risk feeds:
   `champion_stress_test_matrix.json`, `champion_metric_gauntlet.json`,
   `geometry_champion_of_champions.json`, `field_money_truth_sweep.json`,
   `field_validated_dollar_claim_ladder.json`, and
   `field_validation_outreach_board.json`.
3. **Repair the portal framing.** Replace "Reviewer-Safe Winner State" and the
   24/24 lead card with the governed status: narrow historical replay evidence,
   `0/6` cross-sector gains proven, and no performance or dollar marketing.
4. **Regenerate dependent optional feeds.** Zero old value fields, carry
   `NO_CROSS_SECTOR_EFFICIENCY_GAIN_PROVEN`, and state that hosted hashes prove
   bytes and deployment custody only.
5. **Quarantine sendable language.** Prevent the old outreach, valuation,
   operator-context, and buyer-target templates from entering a send queue
   until they include the current status and omit champion marketing.
6. **Preserve history with explicit supersession.** Move dated claim documents
   to a clearly non-current archive or add a top-of-file supersession banner
   pointing to the current benchmark and proof-to-revenue artifacts. Do not
   delete the negative or historical record.
7. **Add one fail-closed publication test.** Fail if a public HTML/JSON or
   reviewer-current document contains `money printer`, the old dollar values,
   affirmative universal-superiority or realized-savings language, or a
   Kuramoto performance claim without the current 0/6 status. Also require a
   byte-identity-only boundary wherever public hash verification is mentioned.
8. **Verify before any deployment.** Rebuild locally, rerun the static claim
   gate, verify that every required hosted hash points to the corrected bytes,
   and deploy only through the existing human-controlled release process.

## Release Decision

`HOLD_PUBLIC_CLAIM_RELEASE`

Reason: the canonical current controls are correct, but multiple stale,
contradictory artifacts are confirmed as live hash matches. Public hash
verification currently proves that some unsafe old wording is faithfully
published; it does not make that wording scientifically valid.
