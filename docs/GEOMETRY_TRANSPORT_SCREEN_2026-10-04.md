# LumenCore Geometry Transport Screen — 4 October 2026

This is a reproducible **internal synthetic screening experiment**, with eight graph layouts and exact geometric generators. It does not validate signal retention, fluid performance or any legacy Geometry Championship family. The canonical registry and its promotion gates remain authoritative.

## What this adds

- Eight 64-node resistor graphs with complete coordinates, edges, metrics and seed metadata in [`results.json`](../evidence/geometry_transport_screen/20261004/results.json).
- Five exact Platonic-solid edge models: tetrahedron, cube, octahedron, dodecahedron, icosahedron.
- Cycloid, sunflower phyllotaxis and a branching-tree geometry generator in portable [`math-models.mjs`](../dashboard/portfolio/math-models.mjs).
- Ten reconciled entries with existing registry links, tentative voice-transcription interpretations and primary source URLs in [`geometry_extension_registry.json`](../evidence/geometry_transport_screen/20261004/geometry_extension_registry.json).
- [the vector graph figure](../evidence/geometry_transport_screen/20261004/geometry_transport_screen.svg), a vector figure drawn directly from the numerical graph data.
- Eleven Python transport tests, nine tests of the shipped mathematical module and four portfolio/data tests. Transport tests include independent grounded circuit solves, Kirchhoff current balance and energy balance. Mathematical tests check faces, incidence, Euler characteristics and physical assumptions.

## The controlled question

At the same 64 terminal coordinates and normalized conductor-material budget, how does changing connectivity alter ideal steady DC conductance, shortest-path detour and single-edge-failure connectivity?

For each graph, normalize its greatest pairwise terminal distance to `D=1`. Set material volume `V=1` and resistivity `ρ=1`. Distribute conductor volume uniformly across the graph's total wire length `L`:

`A=V/L`, `g_e=A/(ρ l_e)`.

These are normalized quantities. Conductance scales in `V/(ρ D²)` and resistance in `ρ D²/V`. A physically small material volume can rescale the model; this calculation does not check finite wire width, junction volume or geometric overlaps. It is not a manufacturable device design.

The weighted graph Laplacian satisfies Kirchhoff's laws. For each unordered terminal pair `(i,j)`, effective resistance is `R_ij = L⁺_ii + L⁺_jj − 2L⁺_ij`. The primary metric is the arithmetic mean of `1/R_ij`, equally weighting all 2,016 terminal pairs. Secondary metrics are mean/worst geometric path stretch and exhaustive one-edge-deletion connectivity. Deleted material is not reallocated; the fault metric uses topology only.

The controlled set is the first six graphs: serpentine chain, square grid, triangulated square grid, Euclidean minimum spanning tree, loop-augmented tree and randomized-tree control. All use identical grid terminals. Edge count and total wire length differ and are disclosed. The triangulated grid uses one diagonal per square cell; it is not an equilateral triangular lattice. The random control uses randomized Kruskal with seed **20261005**, not a uniform spanning-tree sampler. Every other construction is deterministic.

Honeycomb and sunflower retain the same node count, material and diameter but have different terminal positions and shapes. They are **exploratory embedding comparisons**. Pooling their scores with the controlled group would confuse terminal placement with topology.

## Findings to show at the meeting

| Identical-terminal model | Edges | Mean normalized conductance ↑ | Mean path stretch ↓ | Edge deletions keeping all nodes connected ↑ |
|---|---:|---:|---:|---:|
| Serpentine chain | 63 | 0.184884 | 5.1234 | 0% |
| Square grid | 112 | 0.764307 | 1.2531 | 100% |
| Triangulated square grid | 161 | 0.660194 | 1.1484 | 100% |
| Minimum spanning tree | 63 | 0.255317 | 2.5959 | 0% |
| Loop-augmented tree | 96 | 0.709147 | 1.2853 | 100% |
| Randomized tree control | 63 | 0.197135 | 3.0135 | 0% |

In this one frozen synthetic scenario, adding diagonals shortened routes but reduced mean conductance relative to the square grid: more total wire reduced every edge's cross-section. The loop-augmented tree kept full connectivity under all one-edge removals with fewer edges than the square grid, but had lower conductance and slightly greater path stretch. This is a useful tradeoff, not a universal winner.

The honeycomb patch scored 1.256373 mean conductance and 76.6% fully connected edge-deletion trials; the sunflower network scored 0.523487 and 100%. These values describe different terminal embeddings and are deliberately excluded from the controlled ranking.

A tree's 0% fully connected trials does **not** mean every connection disappears: any one edge disconnects a tree somewhere. The JSON also reports the fraction of all terminal pairs that remain mutually connected, including the worst case.

## Scientific boundaries

No time evolution, frequency, inductance, capacitance, impedance matching, dielectric loss, bandwidth, attenuation or signal-to-noise is included. Stronger/longer-lasting signals require a defined medium, frequency range, loads, noise model and transmission-line or Maxwell validation. Fluid branching requires a separate hydraulic model, material and boundary conditions.

The loop-augmented tree is a designed detour-closing heuristic with biological inspiration. It is not a fungal growth simulation. Murray's cubic-radius relation is illustrated algebraically in the branching generator; its fluid assumptions are not imported into the resistor benchmark. A brachistochrone is a fastest-descent cycloid under the stated gravitational assumptions, not a universal fastest communication path. The five Platonic solids are regular convex polyhedra, not a scientific assertion that all reality is made of five shapes.

This run has one layout per family and one random-control seed. It has no independent holdout, paired uncertainty analysis, multiplicity correction, experimental data or frozen multi-fold promotion receipt. It **does not pass** the repository's full promotion protocol. Historical financial-transform results, including negative findings, stay separate. Screenshots alone do not provide simulator inputs, executable code, calibration or independent replication.

## Reproduce

Requirements: Python 3.11+ and NumPy 2.x; Node.js with the built-in test runner. The recorded environment used Python 3.12.14 and NumPy 2.3.5; [`results.json`](../evidence/geometry_transport_screen/20261004/results.json) records the actual interpreter version.

```bash
python code/research/geometry_transport_screen.py --output /tmp/geometry-transport-results.json
python -m pytest -q tests/test_geometry_transport_screen.py
node --test tests/portfolio_math_models.test.mjs tests/portfolio.test.mjs
```

No network calls or external data are needed. Wall-clock duration is diagnostic and naturally varies; graph coordinates, edges, seeds and numerical metrics are reproducible to floating-point tolerance. `source_sha256` binds the result to its Python source. The browser consumes the saved results for graph previews. The separately reviewed [`math-models.mjs`](../dashboard/portfolio/math-models.mjs) supplies the mathematical SVG studies. The extension registry is a naming/source crosswalk, not another performance result.

## Next gate for an actual engineering claim

Choose one application and freeze its source/sink demands, operating conditions, budget, primary metric and acceptance threshold. Compare equal-resource baselines over the canonical protocol's validation folds and seeds, retain negative outcomes, quantify paired uncertainty and enforce the promotion gate. For communications, add frequency-domain loss/reflection analysis and a measured reference fixture. For liquid transport, add pressure/flow boundary conditions, viscosity, radius constraints and a hydraulic or CFD reference. Greater visual complexity earns no scientific credit by itself.

Primary mathematical and engineering sources, their scope and access limitations are retained in [`geometry_extension_registry.json`](../evidence/geometry_transport_screen/20261004/geometry_extension_registry.json).


The October 4 result is an immutable dated first-party receipt. Its source hash
matches `code/research/geometry_transport_screen.py` at source commit
`e7e16954f27308c19f308e2e78a74eee0edb3bb0`, before the continuation below. The public release inventory
independently binds the browser copy of this data to the selected Git snapshot.
No private correspondence, API data or user photographs are part of this run.

## October 5 continuation: conductance after a broken wire

This completes the prior screen's missing post-failure conductance stage in the
same existing reviewer lane. It preserves every October 4 result, graph,
coordinate, seed and primary objective. The
[`outage_protocol.json`](../evidence/geometry_transport_screen/20261005/outage_protocol.json)
defines this retrospective continuation; it is not an independent
preregistration, a new holdout, or the full championship promotion gate.

All **743 distinct single-edge outages** across the eight layouts were scored.
Every surviving wire keeps its original cross-section and resistivity; removed
material is lost. Every score retains all 2,016 original terminal pairs, with
zero conductance for disconnected pairs. Equal weights across edge deletions
describe this stress screen, not physical failure probabilities. Outage results
are secondary metrics and cannot replace the original no-fault primary metric.

| Identical-terminal model | Outages | Disconnecting outages | Before fault | Mean after one fault | Worst after one fault |
|---|---:|---:|---:|---:|---:|
| Serpentine chain | 63 | 63 | 0.184884 | 0.160192 | 0.151037 |
| Square grid | 112 | 0 | 0.764307 | 0.750934 | 0.743609 |
| Triangulated square grid | 161 | 0 | 0.660194 | 0.653952 | 0.649009 |
| Minimum spanning tree | 63 | 63 | 0.255317 | 0.230626 | 0.171642 |
| Loop-augmented tree | 96 | 0 | 0.709147 | 0.691456 | 0.675174 |
| Randomized tree control | 63 | 63 | 0.197135 | 0.178529 | 0.143273 |

All conductance values use the same normalized units as the original screen.
Square-grid mean conductance retention was 98.250%; triangulated-grid retention
was 99.055%, but its absolute post-fault conductance remained lower. The
loop-augmented tree retained 97.505%, also below the square grid. These tradeoffs
are retained, with no winning-family promotion.

Different-terminal exploratory results remain separate: honeycomb had 77
outages, 18 disconnecting, with conductance 1.256373 before, 1.205968 mean after,
and 1.167786 worst after. Sunflower had 108 outages, none disconnecting, with
0.523487 before, 0.513223 mean after, and 0.495442 worst after.

The implementation reuses the unfaulted inverse through a rank-one update for
connected deletions. Removing a bridge leaves effective resistance within each
surviving component unchanged; cross-component conductance becomes zero. Tests
compare **every outage** with an independent direct grounded component solve,
alongside exact small circuits, fixed-material checks, scale laws and
non-increasing conductance under wire deletion. Repeated timing passes reuse
the same 743 scenarios; they are not additional independent experiments.

The retained [`solver_comparison.json`](../evidence/geometry_transport_screen/20261005/solver_comparison.json)
records every timing pass and the numerical agreement, while
[`outage_results.json`](../evidence/geometry_transport_screen/20261005/outage_results.json)
retains every deletion and the full original coordinates. The
[`manifest.json`](../evidence/geometry_transport_screen/20261005/manifest.json)
binds source, tests, protocol and results. Runtime comparisons are first-party
diagnostics on one machine, not general hardware or physical efficiency claims.

Reproduce the continuation and the independent comparison:

```bash
python code/research/geometry_transport_screen.py --edge-outages --output /tmp/geometry-outages.json
python tests/test_geometry_transport_screen.py --benchmark-outages /tmp/geometry-outage-solver-comparison.json
python -m unittest discover -s tests -p test_geometry_transport_screen.py -v
```

Reruns now record their actual UTC timestamp rather than incorrectly reusing
October 4. The legacy result and browser data remain unchanged. The 26-family
registry still has no performance-ready entries. Frequency-dependent signal
transport, physical fixtures, multi-fold validation and independent engineering
acceptance remain open.
