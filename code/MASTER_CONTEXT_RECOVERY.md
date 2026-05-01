# Master Context Recovery Guide

This guide prevents continuity loss when a chat/session disconnect happens.

## Fastest one-button recovery

Run this and it will:
- ensure ticker is running,
- ensure dashboard serve is running,
- run dashboard healthcheck,
- regenerate the master context files,
- optionally open the resume prompt.

```powershell
powershell -ExecutionPolicy Bypass -File code/RUN_ONE_BUTTON_RECONNECT.ps1 -OpenResumePrompt
```

## Full reset + supervised restart preset

Use this when you want an aggressive cleanup and immediate supervised recovery:

```powershell
powershell -ExecutionPolicy Bypass -File code/RUN_ONE_BUTTON_RECONNECT.ps1 -KillAllAndStartAutopilot -OpenResumePrompt
```

This preset expands to:
- kill known stack processes,
- force single-instance normalization,
- start autopilot supervision,
- refresh context artifacts and reconnect status.

## Safe dry-run cleanup preview

Preview which processes would be killed without stopping anything:

```powershell
powershell -ExecutionPolicy Bypass -File code/RUN_ONE_BUTTON_RECONNECT.ps1 -KillAllStackProcesses -DryRunKillAll
```

## What exists now

Run this command anytime before starting a new chat:

```powershell
powershell -ExecutionPolicy Bypass -File code/RUN_BUILD_MASTER_CONTEXT_SNAPSHOT.ps1
```

It regenerates:
- out/execution/master_context_snapshot.json
- out/execution/master_context_snapshot.md
- out/execution/copilot_resume_prompt.txt

## How to recover in under 60 seconds

1. Run the snapshot command above.
2. Open out/execution/copilot_resume_prompt.txt.
3. Paste the full contents into the new chat as your first message.
4. Add one sentence with your immediate goal, for example:
   Continue shipping measured-vs-modeled confidence upgrades and reliability hardening.

## Recommended first prompt after reconnect

Use this exactly if you want maximum continuity:

```text
Resume from the attached master context exactly. Verify current dashboard health, ticker status, and latest rolling opportunity snapshot, then continue with the next highest-impact measured-vs-modeled upgrade without asking me to restate prior context.
```

## Moonshot questions you should keep asking

1. Which sectors have highest measured rolling gain right now, and what concrete evidence upgrades move each lane to HIGH confidence?
2. Which dashboard or autopilot failures could still produce false confidence, and what artifact-level tests close those gaps?
3. What should be the exact investor-safe separation between realized value, measured proxy value, and modeled translation?
4. What is the shortest path from paper proof to TXID-backed controlled live deployment milestones?
5. Which one-page executive dashboard should auto-publish every cycle to maximize grant/pilot conversion?

## Optional operator commands

```powershell
# Start institutional ticker detached
powershell -ExecutionPolicy Bypass -File code/RUN_MULTI_EXCHANGE_PAPER_TICKER.ps1 -Institutional -Detach

# Start institutional dashboard detached
powershell -ExecutionPolicy Bypass -File code/RUN_INSTITUTIONAL_CRYPTO_DASHBOARD.ps1 -Mode serve -BindHost 127.0.0.1 -Port 5016 -RefreshSeconds 15 -Detach

# Start zero-touch autopilot loop
powershell -ExecutionPolicy Bypass -File code/RUN_ZERO_TOUCH_AUTOPILOT.ps1
```
