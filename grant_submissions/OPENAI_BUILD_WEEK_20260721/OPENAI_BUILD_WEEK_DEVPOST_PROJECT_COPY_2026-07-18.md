# ProofLock Console - Source-Backed Devpost Copy

Copy state: `VIDEO_ASSETS_VERIFIED_FEEDBACK_AND_PUBLICATION_OPEN`

Do not paste or submit this as final copy until every bracketed placeholder is replaced from direct evidence and the privacy/IP checklist is approved.

## Project Name

ProofLock Console

## Tagline

Hash what exists. Hold what is not proven.

## Category

Developer Tools

## Built With - Confirmed Components

Codex, gpt-5.6-sol, JavaScript, Web Crypto API, Python, pytest, HTML, CSS

Required model tag: `gpt-5.6-sol`

## Project Story

## Inspiration

AI-assisted development can move faster than the evidence behind a claim. ProofLock Console was built to make that boundary visible and testable for developers, reviewers, and automated workflows.

## What it does

ProofLock Console loads a canonical JSON receipt, recomputes its SHA-256 identity, resolves only repository-bounded artifact paths, rehashes the declared files, and evaluates required promotion gates separately from receipt integrity. The bundled example verifies four declared V2/V3 concept artifacts, then correctly keeps the decision at HOLD because engineering, prototype, safety, and human-release gates remain open.

## How we built it

The project pairs a static browser experience using Web Crypto with a matching Python verifier for local automation and CI. Deterministic tests cover receipt tampering, path traversal, artifact custody, duplicate or invalid gates, and attempts to promote while required gates remain open. Codex helped narrow the scope, implement both verification paths, review the evidence boundary, and build the test suite. A lead Codex workflow coordinated bounded specialist roles for implementation, adversarial testing, evidence reconciliation, and independent review. A privacy-preserving machine receipt records five identity-backed Build Week spawn events across five role categories, with one completion directly observed; maximum concurrency remains NOT_PROVEN. The active build task records gpt-5.6-sol at ultra reasoning effort.

## Challenges we ran into

The hardest design problem was keeping integrity and truth distinct. A receipt can be internally intact without proving the underlying engineering claim, so the interface and verifier report `integrity_valid` and `promotion_allowed` as separate decisions and fail closed when evidence is missing.

## Accomplishments that we're proud of

The public demo was observed with all ten required files returning HTTP 200 and matching their local SHA-256 identities. Desktop and mobile checks recorded zero horizontal overflow, and the bundled sample verified all four declared artifacts while preserving the HOLD decision.

## What we learned

Auditability improves when every important assertion names its evidence class, every artifact has a stable identity, and a missing human or technical gate cannot be converted into approval by polished prose.

## What's next for ProofLock Console

Next steps are an independent reproduction run, signed receipt adapters, CI integration, and additional schemas for evidence workflows. These are planned directions, not completed capabilities.

## Try It Out

https://lumen-core.ai/build_week/prooflock_console/

## Repository

https://github.com/robertashworth1986-debug/lumen-core-public

Exact scoped source:

https://github.com/robertashworth1986-debug/lumen-core-public/tree/281b76fe20d281974a2e2b44670a6a63815fe421/build_week/prooflock_console

## Installation And Testing

Open the public demo URL for the no-build browser path. For local CLI verification, clone the repository and run `python build_week/prooflock_console/verify_receipt.py`. Run the focused test with `python -m pytest -q tests/test_prooflock_console.py`.

## Supported Platforms

Current desktop and mobile browsers with Web Crypto and Fetch support, plus Python 3 for the CLI.

## Testing Access

The public demo requires no account, API key, paid service, rebuild, or test credentials for the bundled verification path. Availability is proven only at the recorded observation time.

## Pre-Existing / New Work Boundary

The larger repository and source concept assets predate the submission period. The focused console, receipt contract, browser and Python verification paths, responsive interface, and tests are the scoped Build Week extension identified by the dated commit record.

## Verified Local Release Assets

- Video: `output/video/prooflock_console_build_week_v1/prooflock_console_openai_build_week_demo_v1.mp4`
- Video duration: `124.634 seconds`
- Video SHA-256: `376fd49b2a43d37fe0901b948e18c8eacf1532144a5d5459b0d5b67bc8e8e4e9`
- Thumbnail: `output/video/prooflock_console_build_week_v1/prooflock_console_devpost_thumbnail_v1.png`
- Thumbnail SHA-256: `f894e6f1d7e021869db45f45b5088286cc60a0057faf058c9656dbc949141d98`
- Video receipt: `output/video/prooflock_console_build_week_v1/prooflock_console_openai_build_week_demo_v1.receipt.json`
- Video receipt SHA-256: `cdbf4130dc0bdc4dda39f75b5d3fc84684a0916416babe15de0f260fb102ac30`
- Orchestration receipt: `grant_submissions/OPENAI_BUILD_WEEK_20260721/CODEX_AGENT_ORCHESTRATION_RECEIPT_2026-07-19.json`
- Orchestration receipt SHA-256: `bbe6b01af60162a2267d839d7a0f6aa4ed4f7683ac5a9d0419078eea0688cbd9`

These paths identify local upload candidates. They do not claim that either asset is public or accepted by Devpost.

## Required External Placeholders

- `/feedback` Session ID: `[[FEEDBACK_SESSION_ID]]`
- Public YouTube URL: `[[PUBLIC_YOUTUBE_URL]]`

## Claim Boundary

This kit prepares source-backed draft content and a field-by-field completion contract. It confirms a bounded project draft and locally verified release assets. It does not prove a /feedback Session ID, eligibility, ownership, legal acceptance, video publication, final submission, judging outcome, endorsement, award, external validation, patent rights, safety, funding, or value.
