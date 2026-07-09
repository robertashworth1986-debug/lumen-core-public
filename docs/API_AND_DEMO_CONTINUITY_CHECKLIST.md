# API and Demo Continuity Checklist

**Purpose:** Keep LumenCore demos, dashboards, proof packets, and module branches operational without exposing secrets or relying on broken billing.

This document must never include API keys, passwords, tokens, one-time codes, private portal credentials, or secret screenshots.

---

## 1. Current continuity risks

Known current risks from recent operational context:

- OpenAI API auto-recharge / credit continuity may need attention.
- LumaScout Google Cloud / Firebase / API billing continuity may need attention.
- data.gov API access should be stored locally as a secret, not committed.
- Any external proof portal must run without exposing private keys or raw account identifiers.

---

## 2. Secret handling rules

Never commit:

- API keys,
- OpenAI keys,
- Google Cloud keys,
- Kraken keys,
- DSIP/Login.gov/Okta codes,
- passwords,
- private tokens,
- billing screenshots,
- private portal screenshots,
- private customer data,
- raw grant portal exports.

Use environment variables, local `.env` files, GitHub Actions secrets, or deployment secrets.

Recommended placeholder pattern:

```bash
OPENAI_API_KEY=__SET_LOCALLY__
DATA_GOV_API_KEY=__SET_LOCALLY__
GOOGLE_APPLICATION_CREDENTIALS=__SET_LOCALLY__
KRAKEN_API_KEY=__SET_LOCALLY__
KRAKEN_API_SECRET=__SET_LOCALLY__
```

---

## 3. Demo readiness checklist

Before a live reviewer demo:

- [ ] Public site loads.
- [ ] Mission Control loads.
- [ ] Proof-to-pilot page loads.
- [ ] Evidence surface loads or has fallback text.
- [ ] README points to current proof docs.
- [ ] No private keys appear in repo or dashboards.
- [ ] API-dependent modules have fallback mode.
- [ ] LumaScout billing/API status is verified before demo reliance.
- [ ] OpenAI API credit status is verified before live generation reliance.
- [ ] LumaTrader demo language avoids audited-profit claims.
- [ ] LumaJet demo language is synthetic/simulation only.
- [ ] LumaSuit demo language is non-actuating and simulation-first.

---

## 4. Fallback mode

Every demo should have a fallback path that works without live paid APIs:

- static proof packet,
- cached public-safe JSON,
- sample Proof Capsule,
- screenshot-free report summary,
- local HTML dashboard,
- markdown reviewer packet.

The fallback should show the proof workflow even if live services are temporarily unavailable.

---

## 5. API continuity report format

Use this template for internal status only:

```json
{
  "generated_utc": "ISO-8601 timestamp",
  "openai_api": {
    "status": "ok | low_credit | disabled | unknown",
    "public_notes": "No keys exposed."
  },
  "google_cloud_lumascout": {
    "status": "ok | billing_attention | suspended | unknown",
    "public_notes": "No billing details exposed."
  },
  "data_gov": {
    "status": "ok | key_created | unknown",
    "public_notes": "Key stored locally only."
  },
  "demo_mode": "live | fallback | hybrid",
  "blockers": []
}
```

---

## 6. Public wording

Safe wording:

> LumenCore supports live and fallback demo modes. API-dependent modules are isolated behind environment variables and can be demonstrated through public-safe cached proof packets when live services are unavailable.

Avoid:

- exposing key values,
- exposing billing account details,
- showing one-time codes,
- implying API continuity when billing or credits are not verified,
- committing screenshots that contain account data.
