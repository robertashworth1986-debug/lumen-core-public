# Security Policy

## Supported Systems

| System | Status |
|--------|--------|
| lumen-core.ai (production portal) | ✅ Active |
| Kraken Execution Dashboard | ✅ Active |
| Evidence Ledger API | ✅ Active |
| Agent Approval Hub | ✅ Active |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

If you discover a security issue — whether in the web frontend, the API endpoints, or anything that could impact the live trading system or user data — please report it privately.

**Contact:** Open a [GitHub private security advisory](https://github.com/robertashworth1986-debug/lumen-core-public/security/advisories/new) or reach out via the contact on [lumen-core.ai](https://lumen-core.ai).

### What to include

- A description of the vulnerability and its potential impact
- Steps to reproduce (or a proof-of-concept if you have one)
- Which URL, endpoint, or component is affected

### What to expect

- Acknowledgement within **48 hours**
- Resolution timeline communicated within **5 business days**
- Credit in the changelog (if you'd like it) once the issue is resolved

## Scope

This repository is a **public mirror** of the lumen-core.ai production stack. The full institutional trading engine (private keys, API credentials, order execution code) is maintained in a private deployment environment and is **not** in this repository.

If you find something that looks like a leaked credential or key in this repo — please report it immediately so it can be rotated.

## Responsible Disclosure

We appreciate responsible disclosure. If you've found something real and you report it privately, we'll:

1. Fix it as fast as we can
2. Give you credit if you want it
3. Thank you publicly

The live system handles real money and real execution proofs. Security matters here.
