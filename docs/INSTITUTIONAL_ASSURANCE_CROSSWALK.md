# LumenCore Institutional Assurance Crosswalk

**Repository:** `robertashworth1986-debug/lumen-core-public`

**Scope:** public repository and bounded validation sprint

**Assessment:** first-party, informative, evidence-linked

**Production decision:** `HOLD`

## Reviewer conclusion

LumenCore has a meaningful first-party assurance foundation: bounded claim
authority, strict evidence custody, reproducibility controls, pinned reviewer
dependencies, selected negative-access and adversarial tests, private security
reporting, buyer data-handling gates, and an incident-response policy with a CI
tabletop. Those controls make a non-confidential technical fit review credible.

They do **not** establish certification, full framework conformance, an
external audit, a penetration test, a complete product or deployment SBOM,
a SLSA level or complete-product provenance, an executed DPA, regulated-data authorization,
independent or field validation, customer acceptance, revenue, or production
authorization. Production remains `HOLD`.

The canonical machine source is
[`config/institutional_assurance_crosswalk_v1.json`](../config/institutional_assurance_crosswalk_v1.json).
The verifier rejects missing evidence, silent status promotion, framework drift,
and removal of required limitations.

## Status summary

| Status | Count | Meaning |
|---|---:|---|
| Implemented first-party | 2 | Public implementation plus named first-party test or machine evidence. |
| Documented control | 2 | Policy exists; operating effectiveness is not independently established. |
| Partial or scoped | 6 | Selected controls exist; product-wide or framework-wide coverage is not established. |
| Prepared, not executed | 1 | External execution handoff exists; execution has not occurred. |
| Buyer-specific gate | 2 | Completion depends on the buyer, data, jurisdiction, and deployment. |
| Open gap | 1 | External/legal/security/commercial evidence remains absent. |

## Authoritative reference set

These are informative references, not claimed certifications or conformance
statements.

| Reference | Current version used | Use in this crosswalk | Explicit limit |
|---|---|---|---|
| [NIST AI RMF](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10) | AI RMF 1.0 / NIST AI 100-1, 2023-01-26 | GOVERN, MAP, MEASURE, MANAGE orientation | NIST states AI RMF 1.0 is being revised; no complete profile or NIST approval is claimed. |
| [NIST GenAI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | NIST AI 600-1, 2024-07-26 | GenAI risk and action orientation | No complete risk/action assessment or deployment authorization is claimed. |
| [NIST CSF](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf) | CSF 2.0 / NIST CSWP 29, 2024-02-26 | GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND, RECOVER orientation | No Current/Target Profile, maturity rating, or external assessment is claimed. |
| [NIST SSDF](https://csrc.nist.gov/pubs/sp/800/218/final) | SSDF 1.1 / SP 800-218 final, 2022-02-03 | Secure-development vocabulary and outcomes | Full SSDF implementation is not claimed; SSDF 1.2 remains draft as of 2026-08-08. |
| [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) | ASVS 5.0.0, 2025-05-30 | Web and API security verification orientation | No ASVS level, requirement-complete assessment, OWASP endorsement, or penetration test is claimed. |
| [OWASP LLMSVS](https://owasp.org/www-project-llm-verification-standard/LLMSVS-v2.0-en.html) | LLMSVS 2.0, 2026-06-15 | LLM, agent, tool, dependency, and monitoring orientation | No LLMSVS level, complete AI threat assessment, or OWASP endorsement is claimed. |
| [SLSA](https://slsa.dev/spec/v1.2/) | approved specification 1.2, 2025-11-24 | Source, build, artifact, and provenance orientation | No Source or Build level, complete-product provenance, or hardened-builder guarantee is claimed. |

## Control-to-evidence map

| ID | Control topic | Current state | Evidence establishes | Required next gate |
|---|---|---|---|---|
| AC-01 | Governance, roles, claims, decision authority | Implemented first-party | Bounded artifact roles, evidence states, authority-escalation refusal, and human release gates. | Name buyer-side risk, data, technical, security, and decision owners. |
| AC-02 | Measurement, evaluation, reproducibility | Implemented first-party | Pinned dependencies, replay requirements, failure retention, and first-party receipts for named experiments. | Obtain a protocol-matched non-author execution and buyer-owned baseline run. |
| AC-03 | Source authorization and data rights | Buyer-specific gate | Templates require rights, purpose, classification, handling, acceptance, and authority before intake. | Execute buyer-specific rights, handling, retention, deletion, and legal terms. |
| AC-04 | Secure development and repository change | Partial or scoped | Selected pinned CI, read-only workflow permissions, credential-free checkout, tests, and diff checks. | Complete a practice-level SSDF assessment and retain repository-setting evidence. |
| AC-05 | Dependency inventory and SBOM | Partial or scoped | The reviewer computation has a scoped inventory; the current exact 43-file public release has deterministic CycloneDX 1.6 coverage. The retained, successfully verified signed SBOM set covers the historical 30-file release at commit `5fff567c`, not the current release. | Inventory VPS/runtime layers and add vulnerability triage, exception handling, and periodic trusted-root re-verification. |
| AC-06 | Build provenance and release integrity | Partial or scoped | Static release files bind to Git identity and SHA-256; one retained main-branch set binds the exact archive to GitHub OIDC/Sigstore provenance and SBOM predicates, source commit, workflow, ref, issuer, and GitHub-hosted runner. | Assess any SLSA level separately, extend provenance to deployment runtime layers, and close live deployment drift. |
| AC-07 | Identity, access, secrets, activation | Partial or scoped | Default-deny operator source and negative tests exist; consequential repair is separately gated. | Verify live secret ownership, identity controls, rotation, and negative access. |
| AC-08 | Vulnerability reporting | Documented control | Private reporting, supported-version, and best-effort response boundaries are public. | Agree buyer-specific severity, notice, remediation, and disclosure terms. |
| AC-09 | Incident response and recovery | Documented control | Severity, authority, containment, recovery, CI tabletop, and receipt rules exist. | Execute a separately authorized live recovery exercise and negotiate objectives. |
| AC-10 | Application and API verification | Partial or scoped | Selected strict parsers, path/schema defenses, default-deny behavior, and adversarial tests exist. | Define the exact app scope and commission requirement-level ASVS and penetration testing. |
| AC-11 | GenAI, agents, external models | Partial or scoped | Deterministic evidence is separated from custom-model runs; tool authority, provider, and data gates are documented. | Inventory production models/tools/data flows and execute scoped LLMSVS adversarial assessment. |
| AC-12 | Privacy and regulated data | Buyer-specific gate | Public/private separation and buyer-specific handling decisions are required. | Complete legal/security review for the actual data, sector, people, and geography. |
| AC-13 | Independent execution | Prepared, not executed | Handoff, receipt contract, and replication docket exist. | A qualified non-author must run the locked protocol and return a complete receipt. |
| AC-14 | External assurance, legal, insurance, acceptance | Open gap | Public evidence correctly preserves the boundary between technical proof and outside conclusions. | Obtain legal, IP, insurance, security, regulatory, independent-test, and buyer acceptance evidence. |

## Machine verification

From a clean checkout with Python 3.10 or newer:

```bash
python code/ops/VERIFY_INSTITUTIONAL_ASSURANCE_CROSSWALK.py \
  --verified-utc 2026-08-08T00:00:00Z \
  --json-out institutional-assurance-crosswalk-receipt.json
python -m unittest discover -s tests -p "test_institutional_assurance_crosswalk.py" -v
```

A green receipt establishes only that the declared schema, current statuses,
reference versions, limitations, evidence paths, and CI binding are internally
consistent at the checked-out commit. It does not establish that every cited
control operated effectively in production or that any framework owner,
customer, assessor, regulator, or outside reviewer accepted the system.

## Procurement answer

The honest answer to “which standards do you meet?” is:

> LumenCore maintains a first-party evidence crosswalk to selected current
> NIST, OWASP, and SLSA framework themes. The public repository provides
> bounded technical evidence for specific controls and names the missing gates.
> We do not claim certification or full conformance. For a paid sprint, we
> convert the buyer's actual security, data, legal, and acceptance requirements
> into an executed control and evidence plan before intake.
