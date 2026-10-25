# LumenCore Institutional Operations Manual

**Version:** 1.0.0  
**Effective:** October 25, 2026  
**Status:** Production-Ready  
**Audience:** Operators, customers, reviewers  

---

## 1. OPERATIONAL AUTHORITY & RESPONSIBILITY

### 1.1 Authority Structure
- **Founder/Systems Architect:** Robert Ashworth
  - Authority to approve releases, scope decisions, customer contracts
  - Sole signatory for SOW, incident response, and policy changes
  - Responsible for evidence integrity and claim boundaries

### 1.2 Operational Roles
| Role | Authority | Responsibility |
|---|---|---|
| **Founder** | Full | Policy, contracts, releases, customer acceptance |
| **External Reviewer** | Read-only | Verify evidence, audit claims, document findings |
| **Customer (Buyer)** | Scoped | Provide data, validate baseline, accept decision |

### 1.3 Decision Gates
All production decisions require documented approval:
- **Release promotion:** Founder sign-off + test suite green
- **Customer SOW:** Founder + buyer both sign
- **Incident response:** Founder approval + documented severity
- **Data handling:** Founder approval + buyer consent

---

## 2. CUSTOMER ENGAGEMENT LIFECYCLE

### 2.1 Pre-Engagement: Buyer Qualification

**Stage:** Fit Assessment  
**Duration:** 1–2 weeks  
**Objective:** Determine if buyer-owned baseline validation is achievable

**Gate Criteria:**
- [ ] Buyer has identified candidate model
- [ ] Buyer has accepted baseline (incumbent/naive/historical)
- [ ] Buyer can lock metric definition before scoring
- [ ] Buyer owns data or has written authorization
- [ ] Buyer has budget authorization and decision timeline
- [ ] Data handling requirements are within LumenCore scope

**Output:** Fit Assessment Result
- `scope_candidate` → proceed to SOW
- `needs_facts` → request missing information
- `needs_separate_controls` → escalate to legal/security
- `no_fit` → close engagement politely

**Document:** `LUMENCORE_BUYER_OWNED_VALIDATION_INTAKE.md`

---

### 2.2 Pre-Engagement: Statement of Work

**Stage:** Scope Definition  
**Duration:** 1–2 weeks  
**Objective:** Execute legally binding agreement with clear deliverables

**Required SOW Sections:**
1. **Parties:** Buyer legal entity, LumenCore (Robert Ashworth)
2. **Scope:** One candidate, one baseline, one metric, one decision window
3. **Deliverables:**
   - Proof Capsule v3 JSON (verifiable evidence package)
   - Manifest with input/output hashes
   - Verification instructions
   - Executive briefing (1 page max)
4. **Data Rights & Confidentiality:**
   - Buyer retains ownership of all input data
   - Buyer retains ownership of candidate model and baseline
   - LumenCore retains Proof Capsule methodology IP
   - Explicit non-disclosure terms (30-year default)
5. **Payment Terms:**
   - 50% at SOW signature (non-refundable scoping fee)
   - 50% on Proof Capsule delivery (regardless of result)
   - No performance guarantees; negative/hold result is valid delivery
6. **Timeline & SLA:**
   - Maximum 30 calendar days from prerequisites to delivery
   - Prerequisites: data access, baseline access, metric agreement
   - SLA: best-effort 30 days; delays documented with cause
7. **Decision Authority:**
   - Named buyer authorized to approve/reject result
   - LumenCore recommends decision; buyer makes final choice
   - Decision options: promote, rerun, external review, hold, reject

**Template:** `LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md`

**Gate:** Both parties sign SOW before any evaluation starts.

---

### 2.3 Engagement: Evaluation Execution

**Stage:** Compute  
**Duration:** 14–28 days (median 21 days)  
**Objective:** Reproduce baseline, generate candidate predictions, measure delta

**Frozen Commitment Requirements:**
1. **Environment Lock:**
   - Code commit: pinned at start of evaluation
   - Dependencies: frozen via lock files
   - Infrastructure: documented hardware/OS spec
   - All decisions recorded in evaluation log

2. **Baseline Verification:**
   - Retrieve accepted baseline (model, weights, version)
   - Test: reproduce baseline on hold-out window
   - Record baseline prediction hash
   - Document any baseline failures/exceptions

3. **Candidate Execution:**
   - Retrieve candidate model (buyer-provided or accessible)
   - Execute on identical hold-out window
   - Record candidate prediction hash
   - Document any candidate failures/exceptions

4. **Metric Computation:**
   - Apply pre-locked metric definition to both predictions
   - Compute delta (candidate - baseline)
   - Record decision threshold (buyer-approved)
   - Determine recommendation: promote/rerun/hold/reject

5. **Failure Logging:**
   - All errors, warnings, missing data recorded
   - Negative results are **required** in output
   - Incomplete gates trigger `hold` recommendation automatically

**Gate:** All hashes verified before proceeding to proof generation.

---

### 2.4 Engagement: Proof Generation

**Stage:** Evidence Packaging  
**Duration:** 1–2 days  
**Objective:** Create verifiable, tamper-evident record

**Proof Capsule v3 Requirements:**
1. **Source Block:** Buyer data, rights status, time window
2. **Baseline Block:** Model name, selection method, version
3. **Metric Block:** Definition, unit, direction, threshold
4. **Run Block:** Timestamp (UTC), code commit, dependencies, window
5. **Manifest Block:**
   - Input hashes (data, baseline, candidate)
   - Output hashes (predictions, results, logs)
   - Manifest hash (verifiable integrity)
   - Public-safe flag (no forbidden promotion phrases)
6. **Result Block:**
   - Summary (1 sentence decision recommendation)
   - Primary delta (metric improvement or regression)
   - Secondary metrics (if any)
   - Negative results (required; at least one)
   - Failure notes (required; list all exceptions)
7. **Claim Boundary Block:**
   - Proves: What this evaluation actually validates
   - Does not prove: What remains unvalidated (field performance, customer savings, etc.)
   - Safe public sentence: One-sentence boundary for external communication
8. **External Validation Block:** Status (not_established for first-party)
9. **Decision Block:**
   - Status: promote / rerun / external_review / hold / reject
   - Next gate: what must happen for promotion
   - Owner: named buyer authorized to approve

**Gate:** Proof Capsule passes `proof_capsule_verifier.py` 100%.

---

### 2.5 Engagement: Delivery & Acceptance

**Stage:** Handoff  
**Duration:** 1–3 days  
**Objective:** Deliver evidence and obtain buyer acceptance

**Deliverables Package:**
1. **Proof Capsule JSON** (verifiable, hash-locked)
2. **Input/Output Manifest** (all artifact hashes)
3. **Verification Instructions** (how to verify locally)
4. **Executive Briefing** (1 page: decision, confidence, next steps)
5. **Signed Release Receipt** (GitHub OIDC + Sigstore attestation)

**Buyer Acceptance Gate:**
- [ ] Buyer downloads Proof Capsule
- [ ] Buyer runs local verification
- [ ] Buyer reviews executive briefing
- [ ] Buyer confirms receipt (email: "Accepted [Date] [Time UTC]")
- [ ] Buyer makes decision: promote, rerun, hold, reject, or external review

**Payment Gate:**
- 50% delivery fee (remaining balance) cleared upon acceptance
- Invoice includes Proof Capsule hash and delivery timestamp

---

## 3. INCIDENT RESPONSE & OPERATIONAL SECURITY

### 3.1 Incident Severity Scale

| Level | Example | Response SLA | Authority |
|---|---|---|---|
| **Critical** | Data breach, unauthorized access, false claim in published evidence | <4 hours notification + mitigation | Founder + Buyer (if affected) |
| **High** | Test suite regression, evaluation failure, evaluation timeout | <24 hours root-cause + fix | Founder |
| **Medium** | Performance degradation, documentation drift, stale dependency alert | <72 hours diagnosis + plan | Founder |
| **Low** | Typo, deprecated API, cosmetic issue | Best-effort within sprint | Founder |

### 3.2 Incident Response Procedure

**Step 1: Detection & Notification**
- Incident detected (internal test, customer report, or CI alert)
- Founder notified immediately
- Severity assessed using scale above
- If customer-affecting: buyer notified <4 hours

**Step 2: Containment**
- If evaluation in progress: halt and assess
- If release affected: rollback to last-known-good
- If data breach: activate quarantine protocol
- Document incident timestamp, initial observation, suspected cause

**Step 3: Investigation**
- Root-cause analysis (technical investigation)
- Scope assessment (who/what affected)
- Evidence gathering (logs, commits, reproductions)
- Timeline reconstruction (when it started)

**Step 4: Remediation**
- Fix identified (code change, policy update, or reversal)
- Fix tested (local + CI verification)
- Fix deployed (merge + release + attestation)
- Verification (re-run affected evaluations or tests)

**Step 5: Post-Incident**
- Document findings (incident report)
- Update procedures to prevent recurrence
- Notify all affected parties
- Archive incident record (append-only log)

**Incident Log Location:** `evidence/incidents/` (append-only)

---

### 3.3 Security Policy: Credential & Secret Management

**Principle:** No production credentials in repository.

**Rule 1: Environment Variables**
- All secrets (API keys, database passwords) → environment variables only
- CI/CD secrets → GitHub Secrets (encrypted)
- Local development → `.env` file (git-ignored, never committed)
- Example: `DATABASE_URL`, `SIGSTORE_OIDC_TOKEN` (never hardcoded)

**Rule 2: Dependency Pinning**
- All production dependencies pinned to exact versions
- Lock files committed (hash-verified)
- Dependabot PRs reviewed + tested before merge
- No transitive dependency surprises

**Rule 3: Secret Detection**
- Pre-commit hooks scan for common patterns (AWS keys, API tokens, etc.)
- CI/CD runs CodeQL + secret-scanning on every PR
- Manual audit quarterly

**Rule 4: Incident Response**
- If secret exposed: rotation within 1 hour
- Affected systems: revoked access + re-authentication required
- Incident report: document scope and remediation

---

### 3.4 Security Policy: Data Handling

**Principle:** Buyer data is buyer-owned. LumenCore is temporary custodian.

**Rule 1: Data Retention**
- Default: Delete all buyer data within 30 days of delivery
- Exception: Explicit written agreement (e.g., archival for audit)
- Deletion: Cryptographic shred (overwrite 3x, then delete)
- Verification: Deletion certificate generated and retained

**Rule 2: Data Access**
- Only named authorized users access buyer data
- Access logged (who, when, what operation)
- No bulk export without buyer consent
- Encryption at rest (AES-256) and in transit (TLS 1.3)

**Rule 3: Data Integrity**
- SHA-256 hashes computed on all buyer data at intake
- Hashes retained for audit trail
- Tampering detected via hash mismatch during verification

**Rule 4: Compliance & Audit**
- SOW explicitly covers confidentiality, retention, and breach notification
- Buyer notified of any data access outside normal evaluation
- Annual compliance review (documentation audit)

---

## 4. RELEASE & DEPLOYMENT MANAGEMENT

### 4.1 Release Cycle

**Trigger:** Founder decides to promote a version to production

**Step 1: Pre-Release Checklist**
- [ ] All relevant PRs merged to `main`
- [ ] Full test suite passes (2,228+ tests)
- [ ] CodeQL security scan passes
- [ ] Dependency review passes (no high-severity vulns)
- [ ] Documentation updated
- [ ] Release notes drafted
- [ ] Changelog updated

**Step 2: Build Artifact**
- Tag commit with semantic version (e.g., `v1.0.0`)
- GitHub Actions trigger build
- Build produces:
  - Proof Capsule verifier binary (Python + dependencies)
  - SBOM (CycloneDX 1.6 format)
  - Signed attestation (GitHub OIDC + Sigstore)

**Step 3: Verification**
- Download artifact
- Verify signature
- Run smoke tests
- Compare checksums with CI output

**Step 4: Release Publication**
- Create GitHub Release with:
  - Release tag
  - Release notes (human-readable summary)
  - Signed attestation JSON
  - SBOM JSON
  - Proof Capsule verifier
- Publish to lumen-core.ai/releases/

**Step 5: Deployment**
- Update lumen-core.ai website to point to new release
- Retain old release links (no deletion)
- Update QUICKSTART.md with latest version
- Test live endpoint: verify `GET /health` returns success

---

### 4.2 Release Naming Convention

**Semantic Versioning:** `MAJOR.MINOR.PATCH[-STAGE]`

| Version | When | Example |
|---|---|---|
| `v1.0.0` | First production release | Initial institutional offering |
| `v1.0.1` | Patch (bug fix, no API change) | Security patch, documentation fix |
| `v1.1.0` | Minor (backward-compatible feature) | New Proof Capsule v3 validation rule |
| `v2.0.0` | Major (breaking change) | New evidence schema format |

**Release Candidate:** `v1.0.0-rc.1` (release candidate, pre-production testing)

---

### 4.3 Rollback Procedure

**Trigger:** Critical issue detected in production release

**Step 1: Assess Impact**
- Critical: Affects customer evaluations → immediate rollback
- High: Affects verifier logic → rollback if no other fix
- Medium: Non-breaking issue → can defer rollback

**Step 2: Execute Rollback**
- Identify last-known-good release
- Re-tag lumen-core.ai/releases/ to point to previous version
- Notify customers of rollback + ETA to fix

**Step 3: Root Cause & Fix**
- Investigate root cause
- Implement fix on `main`
- Tag new release (skip version, e.g., v1.0.2)
- Re-test and re-deploy

**Rollback Log:** `evidence/deployments/rollback_log.jsonl` (append-only)

---

## 5. MONITORING & OBSERVABILITY

### 5.1 Health Checks

**Automated (CI/CD):**
- Test suite: Run 2,228+ tests on every PR merge
- CodeQL: Security scan on every commit
- Dependency review: Flagged vulnerabilities on every PR
- Build: Reproducible artifact generation

**Manual (Weekly):**
- Dependencies: Check for critical security updates
- Documentation: Verify README, docs are current
- Release artifacts: Verify signatures and checksums

**Customer-Facing (On-Demand):**
- Proof Capsule verifier: `python code/proof_capsule_verifier.py --verify`
- Liveness: `curl https://lumen-core.ai/health`

---

### 5.2 Metrics & Reporting

**Key Metrics:**
- Test pass rate (target: 100%)
- Security vulnerability count (target: 0 high/critical)
- Deployment success rate (target: 100%)
- Incident mean-time-to-detect (target: <4 hours)
- Incident mean-time-to-recovery (target: <24 hours)

**Monthly Report (by founder):**
- Test/build status
- Incident summary (if any)
- Customer pipeline (projects in progress)
- Release schedule (next planned version)

---

## 6. CUSTOMER SUPPORT & ESCALATION

### 6.1 Support Channels

| Channel | Use Case | SLA |
|---|---|---|
| Email (founder) | Fit assessment, technical questions | <24 hours response |
| GitHub Issues (public) | Bug reports, feature requests | <48 hours triage |
| Direct call (founder) | Critical incident affecting customer | <4 hours |

### 6.2 Escalation Path

**Tier 1: Founder (First Responder)**
- Assess severity
- Determine if immediate action needed
- Decide: resolve, escalate, or defer

**Tier 2: External Expert (On-Call)**
- For highly technical issues outside founder expertise
- Examples: cryptography, distributed systems, domain-specific validation
- Contact: To be determined per engagement

---

## 7. AUDIT & COMPLIANCE

### 7.1 Annual Audit Checklist

**Q1:** Repository health (code quality, dependency audit)  
**Q2:** Security audit (credential scan, access control review)  
**Q3:** Customer satisfaction (feedback from engagements)  
**Q4:** Release readiness (test coverage, documentation)  

### 7.2 External Review Path

**For Qualified Reviewers:**
1. Download Proof Capsule verifier from latest release
2. Run against public example: `python code/proof_capsule_verifier.py examples/proof_capsule/dice_eia_public_capsule.json`
3. Review source: GitHub `main` branch
4. Review evidence: `docs/INSTITUTIONAL_READINESS_DOSSIER.md`
5. Submit findings: GitHub issues or email founder

**Certification:** No external certification claimed without separate agreement. Internal testing only.

---

## 8. COMMUNICATION POLICY

### 8.1 Public Statements

**Claim Authority:**
- ✅ What we built: "LumenCore enables buyer-owned baseline validation with hash-verifiable evidence"
- ✅ Test results: "2,228+ tests pass; Proof Capsule verifier passes fail-closed security checks"
- ❌ What we didn't verify: "Guaranteed ROI," "field-validated savings," "agency endorsed"
- ❌ What we haven't done: "10,000+ deployments," "proven at scale," "certified by NIST"

**Claim Boundary:** Every public statement includes explicit boundary. Examples:
- "First-party replay; not field validation"
- "Founder-operated; external validation pending"
- "Proof of concept; production readiness pending customer feedback"

---

## 9. POLICY REVISION SCHEDULE

**Effective Date:** October 25, 2026  
**Next Review:** January 25, 2027  
**Review Trigger:** Every 90 days OR after critical incident  

**Change Log:**
- v1.0.0 (Oct 25, 2026): Initial institutional ops manual

---

## 10. CONTACT & AUTHORIZATION

**Authorized Representative:**
- **Name:** Robert Ashworth
- **Title:** Founder / Systems Architect
- **Email:** robertashworth1986@icloud.com
- **Authority:** Full policy approval, customer contracting, incident response

**For Inquiries:**
- Technical: GitHub Issues or code review
- Commercial: Direct email to founder
- Security: Email founder with severity level

---

**END OF INSTITUTIONAL OPERATIONS MANUAL**

*This document is binding policy for LumenCore. Updates require founder authorization. Customers may request a copy upon signed SOW.*
