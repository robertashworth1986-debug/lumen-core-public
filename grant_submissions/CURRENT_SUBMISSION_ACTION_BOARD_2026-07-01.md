# Current Submission Action Board

Generated: 2026-07-01

Purpose: keep the funding lane aligned with the current proof state, current official deadlines, and honest claim boundaries.

## Repo / Proof State

- Main repo: active on `codex/live-domain-proof-feed-bundle`.
- Latest pushed commits:
  - `5eeea0b` - refresh live domain verification docs.
  - `e796efc` - refresh operator context domain status.
  - `9eead8a` - expose local proof readiness in operator context.
- Current working pass hardened phase diagnostics and refreshed proof-feed deployment docs; preserve commit hashes in git as the authoritative audit trail.
- Public proof feed: reviewer-ready, with `12/12` required live-domain hashes matching.
- Live source maximizer: 25 measured providers out of 29 enabled; 823 fresh measured rows in the latest maximizer run.
- Outreach sent: Incubatenergy/EPRI lane, Tennessee Advanced Energy lane, LaunchTN, Vanderbilt Wond'ry, Tennessee Tech protocol-review lane, ORNL partnerships, EPB, and Spark/TVA.
- Additional outreach sent 2026-07-01: OpenPowerAI/EPRI technical-fit request asking for the right reviewer or a buyer-authorized field replay lane. Gmail thread id: `19f1e7f0925ae31c`.

## Current Diagnostic Upgrade

- Champion phase proxy diagnostics now mark flat or low-variance numeric series as degenerate.
- Current replay diagnostic: `23/24` usable numeric holdouts, `15` non-degenerate numeric holdouts, `8` degenerate numeric holdouts excluded from source-level phase means.
- Current champion lane: `kuramoto_phase_coupling` against named baseline `kalman_filter`.
- Claim boundary remains strict: phase proxy diagnostics support mechanism triage only; they do not prove hardware PLL behavior, field validation, realized savings, or a fixed frozen-delta dollar price.

## Current Submission Reality

| Lane | Portal | Current posture | Action |
| --- | --- | --- | --- |
| DICE / HR001126S0010 | DARPA BAAT | Proposal Abstract finalized. DARPA BAAT email confirmation received 2026-06-29 for `HR001126S0010-DICE-PA-052`. | Preserve the confirmation, monitor for BAAT/DARPA follow-up, and reuse the strongest DICE proof in future DARPA/AI autonomy lanes. |
| HarborSentinel / DON26BZ03-NV063 | DSIP | Official SBIR topic page shows open, due July 22, 2026. | Treat as the strongest near-term defense package. Refresh Volume 2 with the latest live-domain proof feed and public AIS gate, then submit through DSIP only after final portal validation. |
| NV065 Adaptive Sensor Management / DON26BZ03-NV065 | DSIP | Official SBIR topic page shows open, due July 22, 2026. | Keep as the second defense package. Strengthen with source-conditioned replay and sensor-resource assumptions before upload. |
| MissionWeave / DLA26BZ03-NV011 | DSIP | Public grant trackers and package records show July 22, 2026 close. | Keep as a strategic organizational-digital-twin package. It needs the clearest buyer story and bounded process metric. |
| NSF Project Pitch | NSF Seed Fund | Pitch path is rolling; full proposal requires invited pitch first. | Best low-friction non-dilutive path. Submit/update the pitch with honest internal proof and external validation ask. |
| Grants.gov live-scan items | Grants.gov | Many urgent items are poor eligibility/fit despite high urgency score. | Do not chase Tribal/WIC/HUD/child-welfare grants unless a real partner unlocks eligibility. |

## What Is Strong Enough To Say

- LumenCore has a public, hash-verified proof-feed layer suitable for reviewer inspection.
- The system has internal replay evidence across live public-source measurements and frozen artifacts.
- The strongest technical claim is a source-conditioned replay and benchmark-selection engine, not universal geometry superiority.
- The current buyer ask should be: "Please provide or approve a held-out operational dataset, incumbent baseline, acceptance metric, and avoided-cost conversion so we can run an externally valid replay."
- DARPA BAAT received the DICE Proposal Abstract titled "Coherence-Bounded Peer Mesh: Sparse Task Markets and Local Inference Control for Resilient Heterogeneous AI Collectives" under identifier `HR001126S0010-DICE-PA-052`.

## What Is Not Yet Unlocked

- Field validation.
- Realized savings.
- Fixed dollar value per frozen delta.
- Institutional trading performance.
- Hardware grid/RF/PLL validation.
- Any claim that the system is guaranteed to outperform on a buyer's live system.

## Next Submit Order

1. DICE follow-up watch - preserve DARPA confirmation and answer any BAAT/DARPA requests quickly.
2. HarborSentinel NV063 - strongest near-term defense narrative and public AIS evidence spine.
3. NV065 Adaptive Sensor Management - strong adjacent Navy sensor-tasking narrative.
4. MissionWeave DLA NV011 - coherent platform/software story if the bounded-process metric is refreshed.
5. NSF Project Pitch - quickest non-portal-heavy path, but not a same-day cash path.
6. DOE Genesis Mission / energy-AI lanes - strategic, but later deadline and likely higher proposal burden.

## Decision Rule

Submit only when the portal, eligibility, final upload preview, representations/certifications, and final human approval are all clean. If any of those are missing, build the packet and keep it in "ready for final portal action," not "submitted."
