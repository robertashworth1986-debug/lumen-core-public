# ProofLock Build Week Voiceover

This is ProofLock, a developer tool that checks whether an evidence packet is intact and whether it has authority to move forward. A valid receipt is necessary, but it is not permission to promote a claim.

Technical reviews often blur three questions: did the files stay unchanged, do they support the statement being made, and has a trusted reviewer authorized release? ProofLock keeps integrity, evidence, and authority separate, then fails closed when a required authority gate is unsupported.

The browser canonicalizes and hashes the receipt, rehashes four same-origin public artifacts, and derives the effective gates. Integrity is verified and all four artifacts match. Four engineering and human authority gates remain held, so the effective decision is HOLD.

Now the guided proof performs the harder attack. It changes every required gate to PASS, requests PROMOTE, and recomputes a valid receipt hash. Receipt integrity still passes. But self-authored engineering, prototype, safety, and human approvals are not trusted authority. ProofLock derives four held gates, blocks the requested promotion, and keeps the effective decision at HOLD.

The console restores the exact canonical receipt text, rehashes the artifacts, and returns to the original HOLD state. The attack never changes the source files or grants itself authority.

The same rules run in the browser and in a Python verifier. Focused tests cover hashes, path boundaries, browser and Python parity, deterministic visuals, restoration, accessibility, deployment isolation, and local-only dependencies. The video names the exact source commit and test result.

Using GPT-5.6 through OpenAI Codex, I isolated the release, built both verifier paths, challenged the trust model, and tested the system with provenance intact. ProofLock demonstrates receipt integrity, artifact identity, policy enforcement, and authority separation. It does not claim that a hash proves safety, patentability, field performance, external validation, or commercial readiness.
