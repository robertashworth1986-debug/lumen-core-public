# Healthcare Website Embed Playbook

This playbook wires Luma healthcare grant intelligence into an external website (for example, MindWise Health) without exposing your owner API key in client-side JavaScript.

## Security model

- Do not place your owner API key in browser code.
- Use the key only in a trusted server/runner job.
- Publish the generated website feed JSON as a static asset.
- Embed the widget that reads the static feed.

## Build/refresh the feed

Run from stack root:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File code/ops/RUN_HEALTHCARE_WEBSITE_FEED.ps1 -ApiKey "<institutional_key>" -ExpiringDays 45 -TopN 40
```

Artifacts produced:

- `out/ops/healthcare_grants_engine/healthcare_website_feed_latest.json`
- `out/ops/healthcare_grants_engine/healthcare_website_feed_heartbeat_latest.json`

## Embed on external website

Include this container where the grants widget should appear:

```html
<div
  data-luma-healthcare-feed="https://YOUR-HOST/out/ops/healthcare_grants_engine/healthcare_website_feed_latest.json"
  data-luma-title="MindWise Healthcare Opportunity Radar"
  data-luma-max="8"
  data-luma-grants-console="https://YOUR-HOST/dashboard/grants.html"
  data-luma-theme="host"
  data-luma-density="cozy"
  data-luma-new-tab="1"
></div>
<script src="https://YOUR-HOST/dashboard/js/luma_healthcare_grants_embed.js"></script>
```

Optional host-brand CSS variables for native visual parity:

```css
:root {
  --mw-blue: #48afe5;
  --mw-blue-dark: #4f8bc9;
  --mw-navy: #0d2a3d;
  --mw-off-white: #f9fbf7;
  --mw-coral: #ff6c52;
  --mw-coral-hover: #e85a42;
  --mw-text: #0d2a3d;
  --mw-text-light: #5a6d7a;

  --mindwise-primary: #0f4a74;
  --mindwise-secondary: #0f766e;
  --mindwise-border: #d7e4ee;
  --mindwise-link-bg: #eef7ff;
  --mindwise-link-text: #0f3f67;
  --mindwise-link-border: #9cc1dd;
}
```

Widget options:

- `data-luma-theme`: `host` (default), `mindwise`, `clinical`, or `executive`.
- `mindwise` uses MindWise-native color/token defaults directly.
- `data-luma-density`: `cozy` (default) or `compact`.
- `data-luma-new-tab`: `1` (default) opens actions in new tab, `0` opens in same tab.
- `data-luma-max`: max records shown (recommended 4-10).

Runtime refresh hook:

```js
window.LumaHealthcareEmbed.refresh();
```

Use this after replacing the feed file during a live page session if you want to refresh without page reload.

## Review behavior

- `Review Official Source`: opens the best-known authoritative or source-linked listing for requirements review.
- `Draft Workspace`: opens `grants.html` with `auto_fill=1` for a source-grounded draft structure and blocker ledger. It does not establish eligibility or submit anything.
- `Opportunity Console`: opens the same candidate in full console mode without draft initialization.

## Frontend parity

For internal parity with mission control and grants console:

- Keep `dashboard/mission_control.html` mirrored with `INSTITUTIONAL_STACK_V2/dashboard/mission_control.html`.
- Keep `dashboard/grants.html` mirrored with `INSTITUTIONAL_STACK_V2/dashboard/grants.html`.
- Run parity audit after sync.

## Notes

- Some portals require authenticated workspace creation before final submission.
- Feed scores measure configured relevance and urgency signals, not organizational eligibility or award probability.
- The widget routes users to the best-known listing entry point from feed metadata. Users must verify the official source, current requirements, deadline, eligibility, and submission route.
