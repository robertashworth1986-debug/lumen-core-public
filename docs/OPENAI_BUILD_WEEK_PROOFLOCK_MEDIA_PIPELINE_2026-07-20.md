# ProofLock Build Week Media Pipeline

This pipeline assembles a bounded submission video candidate and a machine-verifiable receipt. Generated audio, screenshots, motion segments, and video remain under ignored `output/` paths. The repository keeps the builder, voiceover, and tests.

## Required Local Inputs

Place these current-commit captures under `output/video/prooflock_console_build_week_v2/frames/`:

- `01_current_initial.png`
- `02_current_authority_attack.png`
- `03_current_restored.png`

Generate `output/speech/prooflock_console_build_week_narration_v2.wav` from `docs/OPENAI_BUILD_WEEK_PROOFLOCK_VOICEOVER_2026-07-20.md`. Disclose the synthetic voice. The current rehearsal receipt records `LOCAL_WINDOWS_SYNTHETIC_SPEECH_MICROSOFT_MARK`; it does not claim an OpenAI Audio API generation succeeded.

## Build And Verify

Run the focused tests first and preserve their exact result. Then bind that result and the exact source commit into the video:

```powershell
$commit = git rev-parse HEAD
$observed = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
python code\ops\BUILD_PROOFLOCK_BUILD_WEEK_DEMO_VIDEO.py `
  --observed-utc $observed `
  --public-commit $commit `
  --test-evidence '54 passed, 3 skipped'
python code\ops\BUILD_PROOFLOCK_BUILD_WEEK_DEMO_VIDEO.py --verify
```

The builder creates a 1080p H.264/AAC video under three minutes, a 3:2 thumbnail, eight bounded slides, EBU R128 single-pass narration normalization, and a receipt that rehashes every declared input and output.

When the console source tree has not changed, existing PNG captures may be rebound without being misrepresented as fresh captures. Pass the exact capture commit with `--frame-source-commit`. The builder resolves the console Git tree at both commits and fails closed unless the tree object IDs match exactly. The receipt records that provenance bridge and explicitly states that tree equality does not independently prove screenshot origin.

## Publication Gate

The current artifact is a verified local submission candidate. Do not call it the published contest video or submit the Devpost entry until all of these are true:

- the exact 15-file release remains live at `15/15` byte identity;
- the live verifier continues to pass against the commit shown in the video;
- the focused tests remain green at the displayed `54 passed, 3 skipped` result;
- the real `/feedback` Session ID has been confirmed without publishing it;
- the final public video plays while signed out; and
- Robert reviews the complete preview and performs the legal/final submission action.

The receipt proves local media assembly, declared file identity, bounded duration, and decode success. It does not prove publication, contest acceptance, judging, external validation, safety, patent rights, funding, or commercial readiness.
