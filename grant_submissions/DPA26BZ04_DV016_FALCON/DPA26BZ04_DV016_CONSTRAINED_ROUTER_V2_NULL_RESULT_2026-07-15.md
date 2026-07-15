# DPA26BZ04-DV016 Constrained Router v2 Null Result

## Evidence identity

- Run UTC: `2026-07-15T15:18:05.258291+00:00`
- Protocol: `falcon_constrained_context_router_protocol.v2`
- Protocol SHA-256: `8302c6ad5b6220ed1b37e08751c46274c5aed4a4a64a33594cc2aa6d93d4ac3f`
- Runner SHA-256: `c0adb0aa8890fa34a78d9d1473f79820f126346b8124d81bc6595f8963ef5021`
- Frozen v1 core dependency SHA-256: `8c70ab92c98e9ca917530667f3b30496bbe17b4fc393d45faded31158136d8e5`
- Model: `Qwen/Qwen2.5-0.5B-Instruct`
- Resolved model revision: `7ae557604adf67be50417f59c2c2f167def9a775`
- Device: CPU
- Decisions: `30`
- Candidate completions scored: `90`
- Model forward passes: `30`
- Model scoring time: `588.456605` seconds

## Result

The predeclared qualification gate did not pass. This result must not be presented as a qualified router or as hybrid-performance evidence.

- Overall accuracy: `0.833333` (`25/30`)
- Required overall accuracy: `0.900000`
- Unsupported output rate: `0.000000`
- Mean candidate-score margin: `0.222396`
- Confident-decision rate at the frozen `0.01` margin: `1.000000`
- Breast-cancer diagnostic domain accuracy: `0.866667`
- Wine-chemistry domain accuracy: `0.800000`
- Nominal-context accuracy: `1.000000`
- Dropout-context accuracy: `1.000000`
- Noise-context accuracy: `0.500000`

Passed checks were real model, protocol/model match, resolved revision, two domains, required decision count, per-domain minimum, zero unsupported outputs, confidence rate, and trace-chain verification. The failed checks were overall accuracy and per-context accuracy.

## Failure analysis

All five errors were noise notes classified as dropout. The allowlisted scoring method eliminated the protocol-v1 formatting failure, but the natural-language candidate completions introduced class-dependent language priors. Mean token normalization did not remove that bias. The result therefore demonstrates a valid output-control improvement without demonstrating adequate semantic routing quality.

The next prospective protocol may test a stronger model on the available NVIDIA GPU and a calibrated single-token class decision. It must use a new protocol identity, lock its thresholds before execution, retain v1 and v2 null results, and keep a future full hybrid-comparison holdout disjoint from development evidence.

## Integrity receipt

- Output manifest SHA-256: `b2ccc94072bb6fc39ea0c57b4b6b452832adf6fecbda3c6e1760ee36a6bc5e38`
- Trace terminal SHA-256: `8240d616219220fc4589b15d27143e951924746b534cce984a96bde3c49b6f64`
- Manifest self-hash: independently verified
- Output byte counts and SHA-256 hashes: independently verified
- Frozen protocol, runner, and core source hashes: independently verified
- Trace records and terminal chain: `30/30` independently verified
- Focused software tests before the real run: `8 passed in 2.13s`

## Claim boundary

This failed qualification is internal method-development evidence only. It does not establish hybrid lift, external validation, field readiness, agency acceptance, patent scope, safety, savings, enterprise scale, or universal superiority.
