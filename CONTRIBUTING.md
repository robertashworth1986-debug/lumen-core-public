# Contributing to LumenCore™

First — thank you for caring enough to look at this.

LumenCore is a solo-built, production-grade institutional intelligence platform. Most of the core trading engine and AI architecture lives in a private deployment environment, but this public repo contains the live dashboards, evidence ledger, and site infrastructure that power [lumen-core.ai](https://lumen-core.ai).

---

## What You Can Contribute

### 1. Bug Reports & Issues
Found something broken on the live site? Please [file an issue](https://github.com/robertashworth1986-debug/lumen-core-public/issues/new/choose). The templates are set up to make it fast.

### 2. Dashboard Improvements
The HTML dashboards are in the `dashboard/` folder. If you have frontend chops and want to improve UX, performance, or accessibility — PRs are welcome.

- Use vanilla JS or Three.js (no new build toolchains please — this deploys to a bare nginx VPS)
- Preserve all existing data bindings (don't break the JSON feed connections)
- Test in Chrome and Firefox before submitting

### 3. Documentation
Better docs = more people understanding what this system does. If you can write clearly about:
- How the evidence ledger works
- How the alpha map is generated
- What the harmonic architecture actually does

...a PR to improve the docs is extremely welcome.

### 4. Collaboration Proposals
If you're working in quant finance, energy grid optimization, defense, or hardware R&D — and you think there's alignment with what's being built here — open a Feature Request issue or reach out directly.

---

## Ground Rules

1. **No credentials in PRs.** Ever. Not even test ones.
2. **Don't break the evidence chain.** The hash-chained proof ledger is the most important artifact in this repo. Don't modify historical entries.
3. **Keep it production-quality.** This is a live system. Broken HTML reaches real users.
4. **One concern per PR.** Smaller PRs get reviewed faster.

---

## Development Setup

The site is static HTML + JSON. No build step needed for most changes.

```bash
git clone https://github.com/robertashworth1986-debug/lumen-core-public.git
cd lumen-core-public
# Edit HTML files directly
# Open dashboard/mission_control.html in your browser to test
```

For changes that depend on live API data, the JSON feed endpoints are:
- `https://lumen-core.ai/api/live_status.json`
- `https://lumen-core.ai/api/executor_heartbeat.json`
- `https://lumen-core.ai/evidence/`

---

## Code Style

- **HTML**: 2-space indent, no inline `style=""` (use the existing CSS classes)
- **JavaScript**: Vanilla ES6+, no frameworks
- **JSON**: Pretty-printed, UTF-8
- **Filenames**: `snake_case` for data files, `kebab-case` for HTML pages

---

## License

By contributing, you agree that your contributions will be licensed under the same [MIT License](LICENSE) that covers this project.
