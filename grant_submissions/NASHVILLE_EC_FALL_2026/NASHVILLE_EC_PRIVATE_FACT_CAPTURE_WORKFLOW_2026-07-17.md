# Nashville EC Private Fact Capture Workflow - 2026-07-17

This workflow validates the six founder confirmations without placing the answers in public Git history.

## Private Boundary

- Template: `config/nashville_ec_private_facts_template_v1.json`
- Private input directory: `grant_submissions/NASHVILLE_EC_FALL_2026/private/`
- The private directory is excluded by `.gitignore`.
- The validator refuses to write founder facts elsewhere inside the repository.
- A path outside the repository is also allowed.

## Validation Command

```powershell
python code/ops/VALIDATE_NASHVILLE_EC_PRIVATE_FACTS.py --input grant_submissions/NASHVILLE_EC_FALL_2026/private/founder_facts.private.json
```

The validator checks exact portal options, normalizes the weekly-hours labels, rejects negative or malformed currency, and requires all four financial amounts when the proposed all-zero confirmation is false.

## Output Boundary

The output is a private eleven-question portal fill map. It is not authorized for publication, email transmission, fee acceptance, terms acceptance, signature, or final portal submission. The complete live preview and any fee or terms remain human-reviewed.
