# Funding Response Triage

Generated UTC: `2026-07-03`

This file captures the latest outreach and funding-response state so future agents do not drift. It is an operator handoff, not a claim of award, funding, field validation, realized savings, or legal advice.

## Gmail Access Note

- The Gmail connector token returned `401 expired`.
- Chrome/Edge browser control was used as the fallback because Robert was already signed in.
- No emails were sent, archived, deleted, labeled, or moved during this triage pass.

## Outreach Responses Found

| Lane | Status | Meaning | Next action |
|---|---|---|---|
| Incubatenergy Labs / EPRI | Reply received from Sarah Toews. Current cycle is already underway; next IEL application/selection cycle expected in September; scheduling link offered. | Warm external validation doorway, not selection or field validation. | Book a fit call focused on buyer-authorized replay, held-out utility data, locked incumbent baseline, acceptance metric, and economic conversion. |
| Tennessee Tech / Satish Mahajan | Thread exists with a received message, but visible Gmail body did not show a substantive technical reply in the browser view. | Treat as pending/manual-check, not validation. | Manually inspect thread and send a concise follow-up if no substantive reply is present. |
| ORNL partnerships | Auto-reply received. | Receipt only, not validation. | Wait or route through a more specific ORNL/UT-Battelle partner lane. |
| Black Dog / LvlUp Ventures | Funding/application lane found in newsletter. | Investor/application opportunity, not validation. | Use the LvlUp application draft and confirm financial fields before submitting. |

## Black Dog / LvlUp Venture Application Signal

The relevant Black Dog/LvlUp email directs founders to apply through:

- `https://www.lvlup.vc/apply/funding-application`

Referral fields requested by the email:

- How did you hear about us: `Venture Scout`
- Referrer name: `Scott Kelly`
- Referrer email: `scott@blackdogvp.com`

The form asks for founder contact details, company basics, an elevator pitch, business model, pitch deck PDF/link, fundraising stage, raise amount, valuation, revenue/burn/runway/cash reserve, and which LvlUp capital/program lanes to apply for.

## Recommended Application Posture

Use disciplined language:

- LumenCore is a hash-verified evidence and replay platform.
- Current strongest result is an internal locked replay champion, not field validation.
- The platform is ready for buyer-authorized field replay using externally supplied or approved held-out data, locked baselines, acceptance metrics, and economic conversion.
- Revenue path is paid evidence review, pilot validation, platform license, grant-funded validation, or success fee after independent validation.

Avoid these claims:

- field validated
- realized savings
- guaranteed ROI
- guaranteed grant/investor outcome
- fixed dollar value per frozen delta
- autonomous trading edge
- universal geometry superiority

## SAM.gov API Key Rotation

SAM.gov email found:

- Reminder type: first rotation reminder.
- Window: rotate the individual account API key within 15 days of the July 2, 2026 email.
- Safe target date: complete before `2026-07-17`.
- New replacement key is expected under the Public API Key section of the SAM.gov user profile.

Safe rotation plan:

1. Robert signs into SAM.gov and opens the profile API key page.
2. Retrieve the replacement key without printing it into logs.
3. Store it only in the local secret/env path, not in committed files.
4. Run a SAM.gov API smoke test.
5. Update any local registry status with hash/prefix only.
6. Commit only redacted status docs or non-secret config metadata.

Do not rotate silently: changing API keys can break existing pulls if the replacement is not propagated.

Safe helper added:

```powershell
cd C:\LumaTrader\INSTITUTIONAL_STACK_V2
pwsh -ExecutionPolicy Bypass -File .\tools\Set-SamApiKey.ps1 -Validate -SetUserEnv
```

The helper stores `SAM_GOV_API_KEY` locally in `config/luma_live_keys.env`, backs up the previous env file, validates one SAM.gov Opportunities API call, and does not print the key.

## Live Breadth Correction

Current best evidence from `dashboard/data/champion_metric_gauntlet.json`:

- Champion replay core: `24/24` wins vs `kalman_filter`.
- Champion family: `kuramoto_phase_coupling`.
- Source lane: `wave_resonance_timing`.
- Champion replay source systems: `4`.
- Estimated replayed rows: `2,506,267`.
- Broader measured provider universe: `25/29`.
- Fresh rows from broader live pulls: `823`.
- Mapped source files/feeds: `186`.
- Ready-for-benchmark manifest rows: `313`.
- Registered/ranked families: `140`.

Latest live-source maximizer refresh run in this pass:

- Enabled sources: `29`.
- Measured sources: `25`.
- Failed/thin sources: `4`.
- Fresh measured rows in the refresh: `1,326`.
- Output: `out/ops/live_source_measurement_maximizer_latest.json`.

Interpretation:

- The "4 source systems" number is the champion replay core.
- The "25/29 providers" number is the broader live-breadth universe.
- The next technical unlock is promoting more of the broader universe through the same locked replay rules, not pretending those sources already belong to the champion proof.

## Highest-Value Next Actions

1. Book EPRI/IEL fit call and ask for the exact field replay unlock: held-out utility data, incumbent baseline, acceptance metric, and avoided-cost conversion.
2. Complete LvlUp application only after Robert confirms legal entity, revenue, burn, runway, valuation, and pitch-deck attachment.
3. Rotate SAM.gov key with Robert present, then run smoke tests and update redacted status.
4. Regenerate live-source and dollar-claim feeds so stale dashboard files do not contradict the current `25/29` breadth state.
5. Keep all public-facing claims in the "buyer-authorized field replay ready" lane until an external owner validates the work.
