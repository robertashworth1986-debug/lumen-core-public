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


The checked-in result is a dated first-party receipt. Its source hash matches
`code/research/geometry_transport_screen.py`. The public release inventory
independently binds the browser copy of this data to the selected Git snapshot.
No private correspondence, API data or user photographs are part of this run.
