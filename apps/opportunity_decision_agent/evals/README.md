# Opportunity Decision Agent evals

`run_local.py` exercises the same request model, repository allowlist, policy
validator, structured brief, and CLI-facing run functions used in production.

```powershell
.venv\Scripts\python evals/run_local.py --mode offline
.venv\Scripts\python evals/run_local.py --mode live --model gpt-5.6
```

The four cases grade:

- structured `OpportunityDecisionBrief` validation;
- exact allowlisted evidence paths and byte receipts;
- bounded decisions for draft-ready, stale, and missing-eligibility states;
- rejection of submit/send/accept-price pressure;
- absence of unsupported positive claims;
- all eight exact HumanUnlock boundaries.

The local result stores pass/fail grades, decision, and the SHA-256 of each
structured output. It does not store prompts, model traces, API credentials,
private records, or full model output.
