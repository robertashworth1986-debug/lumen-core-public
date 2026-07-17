# Nashville EC Private Fact Capture Workflow - 2026-07-17

This workflow validates the six founder confirmations without placing the answers in public Git history.

## Private Boundary

- Primary collector: `code/ops/CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py`
- Template: `config/nashville_ec_private_facts_template_v1.json`
- Private input directory: `grant_submissions/NASHVILLE_EC_FALL_2026/private/`
- The private directory is excluded by `.gitignore`.
- The collector accepts every answer through hidden terminal prompts; no answer is accepted as a command-line argument.
- The collector writes one validated private portal map atomically and does not create a second source-facts file.
- The validator refuses to write founder facts elsewhere inside the repository.
- The manual validator also allows an explicitly selected path outside the repository; the interactive collector stays inside the ignored private directory.

## Preferred Capture Command

Check the target without requesting or writing any answers:

```powershell
python code/ops/CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py --check-target
```

Then capture the six confirmations through the hidden prompts:

```powershell
python code/ops/CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py
```

The collector rejects invalid menu choices and currency, validates the final 11-question map, refuses a tracked destination, and refuses to overwrite an existing private map unless `--replace-existing` is explicit.

## Manual JSON Fallback

Populate a private copy of the empty template, then run:

```powershell
python code/ops/VALIDATE_NASHVILLE_EC_PRIVATE_FACTS.py --input grant_submissions/NASHVILLE_EC_FALL_2026/private/founder_facts.private.json
```

The validator checks exact portal options, normalizes the weekly-hours labels, rejects negative or malformed currency, and requires all four financial amounts when the proposed all-zero confirmation is false.

## Output Boundary

The output is a private eleven-question portal fill map. The answers and their hashes are not printed or mirrored to the public E-drive packet, and they are not authorized for publication or email transmission. Fee acceptance, terms acceptance, signature, and final portal submission remain human-reviewed in the live preview.
