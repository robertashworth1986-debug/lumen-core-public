# ProofLock Threat Model

## Security Goal

ProofLock must distinguish three questions:

1. Are the receipt and declared repository files byte-consistent?
2. Do machine-verifiable facts support each automatic gate?
3. Has an authorized external or human reviewer approved the remaining gates?

Only the first two questions are answered by the bundled verifier. The third remains fail-closed.

## Trusted Inputs

- The verifier code from a pinned Git commit.
- Repository artifact bytes loaded through the local `assets/` allowlist.
- Browser Web Crypto or Python `hashlib` for SHA-256.

The receipt author, receipt text, recorded gate statuses, and recorded decision are not trusted authorities.

## Covered Attacks

- Mutation without resealing: receipt hash mismatch.
- Artifact substitution: artifact hash mismatch.
- Path traversal, alternate-origin fetches, encoded traversal, and absolute paths: rejected.
- Removal or downgrading of a canonical required gate: rejected as a malformed receipt contract.
- Setting external or human gates to `PASS`, selecting `PROMOTE`, and recomputing a valid receipt hash: integrity can remain valid, but policy fails and promotion remains blocked.
- Malformed top-level receipts or artifact/gate rows: structured fail-closed report.

## Gate Authority

`artifact_hashes` is derived from actual repository bytes. `lineage_manifest` is derived by parsing the two hash-matched manifests and checking their declared identifiers and supersession references.

Engineering CAD, prototype testing, qualified safety review, and human release are not derivable from receipt text. A recorded `PASS` for those gates becomes effective `OPEN` until a future trusted-attestation verifier is explicitly implemented.

## Non-Guarantees

SHA-256 detects byte changes but does not authenticate who authored or approved a receipt. Internal manifest consistency is not independent provenance. The bundled console does not provide digital signatures, trusted issuer identity, non-repudiation, external validation, legal authorization, safety certification, patent conclusions, or engineering performance proof.

## Promotion Invariant

`promotion_allowed` is true only when all of the following are true:

- receipt and artifact integrity are valid;
- policy validation is valid;
- every canonical required gate has an effective status of `PASS`;
- the recorded decision is exactly `PROMOTE`.

The bundled receipt intentionally cannot satisfy this invariant because its external authority gates have no trusted attestations.
