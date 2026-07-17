# Public Visual Experience Budget

**Purpose:** Make LumenCore visually memorable without weakening performance, accessibility, verifier integrity, or the reviewer path.

## Core rule

The public experience may become cinematic, spatial, and highly interactive. It may not become dependent on a single GPU tier, hide evidence behind animation, change the verifier result, or make a stronger claim than the underlying receipt.

**Bounded light speed for visuals:** add intensity until the measured performance or comprehension budget is reached, then degrade gracefully instead of breaking.

## Layered experience

### Layer 0 — canonical static proof

Always available:

- semantic HTML;
- readable source, baseline, metric, manifest, result, limitation, and next gate;
- no JavaScript dependency;
- no remote asset required for the core evidence;
- printable and screen-reader usable.

The existing `dashboard/evidence/index_bounded.html` is the Layer 0 reliability surface.

### Layer 1 — lightweight motion

Progressive enhancement:

- CSS gradients and glows;
- subtle parallax;
- state transitions tied to real verifier fields;
- no continuous animation when off-screen;
- reduced-motion support;
- no layout shift after first render.

### Layer 2 — Evidence Lattice

Optional Canvas/WebGL experience:

- artifact nodes derived from the receipt;
- hash-valid links illuminate;
- open authority gates remain visibly incomplete;
- failed hashes fracture or disconnect the lattice;
- `HOLD` produces a stable contained state rather than a success celebration;
- deterministic positioning and timing derived from the receipt hash;
- guided verify → tamper → fail → restore → verify sequence;
- no write to the canonical receipt during the guided demonstration.

### Layer 3 — immersive reviewer mode

Optional high-tier experience:

- spatial camera movement;
- depth-aware labels;
- interactive lineage inspection;
- holographic material treatment;
- bounded particles, bloom, and post-processing;
- cinematic transitions between source, baseline, run, manifest, and decision.

Layer 3 must never be the only path to content.

## Performance budgets

### Initial load

- canonical HTML and critical CSS remain small enough for immediate reading;
- no blocking third-party script for the evidence path;
- heavy 3D code loads only after first content paint or explicit interaction;
- compressed visual assets use responsive sizes;
- repeated assets are cached and content-addressed where practical.

### Runtime

Target tiers:

- **Ultra:** 60 frames per second target on capable desktop hardware;
- **Balanced:** 30–60 frames per second with reduced particles and post-processing;
- **Lite:** 24–30 frames per second using Canvas or simplified geometry;
- **Static:** no continuous animation, full evidence readability.

Automatic downgrade triggers:

- sustained frame time above budget;
- low device memory or hardware concurrency;
- save-data preference;
- reduced-motion preference;
- WebGL context loss;
- thermal or battery pressure where detectable;
- repeated asset or shader failure.

A downgrade is a successful safety behavior, not an error.

## Complexity limits

Before adding a visual effect, identify:

- the evidence field it explains;
- its GPU and CPU cost;
- its memory cost;
- its mobile behavior;
- its fallback;
- its reduced-motion behavior;
- its failure mode;
- whether it can alter or obscure verifier output.

Decorative effects with no explanatory role must remain below the cost of evidence-bearing visuals.

## Accessibility and comprehension

- all state colors include text or icon labels;
- no meaning depends on color alone;
- keyboard navigation reaches every control;
- focus state remains visible;
- motion can be paused;
- reduced-motion users receive instant state transitions;
- important results are rendered as text outside the canvas;
- the experience remains understandable in under three minutes for a first-time reviewer.

## Evidence binding

Every visual state must be a pure projection of a structured verifier result.

```text
receipt + observed files -> verifier result -> visual state
```

Never:

```text
visual state -> claimed verifier result
```

The visual layer may show:

- artifact custody;
- declared lineage;
- hash matches and failures;
- required gate status;
- current decision state;
- limitations and open review steps.

It may not imply:

- engineering performance not measured by the receipt;
- CAD accuracy;
- prototype existence;
- certification;
- external validation;
- field deployment;
- customer acceptance;
- agency endorsement;
- patent outcome.

## Public architecture

Recommended routes:

- `/evidence/` — canonical static reviewer path;
- `/prooflock/` — focused interactive verifier console;
- `/experience/` — optional cinematic Evidence Lattice and founder build timeline;
- `/status/` — operational health and current public-safe state.

The static reviewer path remains the front-door fallback even when an immersive route is degraded.

## Release gates

A visual release is ready only when:

- verifier results are unchanged by the visual layer;
- desktop, mobile, reduced-motion, keyboard, and no-WebGL checks pass;
- the static fallback is complete;
- no remote dependency blocks core proof;
- performance budgets are measured, not assumed;
- the public claim boundary is visible before and after the guided sequence;
- screenshots and demo video match the released commit;
- every visual asset has source, rights, version, and hash metadata.

## Mesmerizing without breaking

The highest-value visual effect is not more particles. It is a clear transformation that lets a reviewer see evidence integrity:

1. evidence arrives as separate artifacts;
2. custody and lineage assemble into a coherent field;
3. open gates remain visibly incomplete;
4. tampering breaks the field;
5. exact restoration reconstitutes it;
6. the final state stays `HOLD` until external authority gates are satisfied.

That sequence is memorable because the visual choreography and the integrity logic are the same system.
