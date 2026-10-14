# Capital Research Lab

Open `/capital_research_lab.html` from the public site's Paid validation navigation. The lab extends the existing LumenCore funding work with Mission Control's visual language and an educational capital-planning workspace.

The four views are:

- **Capital command:** reviewed coverage, an illustrative 3D map, and three immediate research priorities.
- **Funding routes:** eight revenue, grant, equity, debt, and support routes, with official sources, conditions, uncertainties, and next actions. A program listing does not establish applicant eligibility or an award.
- **Scenario lab:** constant-burn runway, funding gap, priced-round ownership, and fixed-rate loan calculations. Inputs start empty. The optional teaching example is explicitly labeled and does not represent LumenCore's finances.
- **EC notebook:** session notes, use of funds, next action, and a readiness self-check. Saving uses this browser's local storage. Downloading a working brief includes notes and any scenario assumptions. Moving between localhost and the public domain does not transfer notes; export them first.

`dashboard/assets/capital_research.json` is a dated public-source research snapshot. Update its facts and review time together after checking the linked primary sources. Do not use file modification time as evidence that a deadline or application window is current. Preserve the distinction between grants, repayment obligations, ownership, advisory services, and customer delivery obligations.

The current research priority is to cost one verifiable milestone, ask the EC for the current Impact Grant rules, and qualify the matching-capital or federal-award dependencies before spending time on conditional programs. This is a research sequence, not a financing recommendation or a commitment.

The 3D scene reuses the repository's vendored Three.js modules. Animation is capped, honors reduced-motion preferences, and pauses rendering while the page is hidden. Orbit geometry is decorative and encodes no amount, probability, or performance measure. A static fallback is available if WebGL cannot initialize.

To preview from the repository root:

```powershell
python -m http.server 8778 --bind 127.0.0.1 --directory dashboard
```

Then open `http://127.0.0.1:8778/capital_research_lab.html`. Direct `file:` opening cannot reliably load browser modules and the JSON snapshot.

Run calculation checks with `node --test tests/capital_math.test.mjs`. The release packager and VPS allowlist include all five lab assets; exact-snapshot CI also exercises the calculation checks. Browser QA covers filtering, conditions, example/clear behavior, note recovery, export, desktop/mobile layout, and rendering errors.

The browser modules use `.js` paths because the current VPS serves that extension with a JavaScript MIME type. The live release verifier checks JavaScript MIME types across every directory; matching bytes served as `application/octet-stream` cannot pass deployment verification.
