# Geometry Evaluation Protocol v1

## Purpose

This protocol lets LumenCore evaluate Euclidean, curved, manifold, graph, topology-aware, spiral, helical, branching, gyroid, and phyllotactic representations without turning geometry terminology into an unsupported claim.

The geometry is a candidate component of a bounded experiment. It is not a product identity and it receives no evidentiary credit until it beats matched baselines on a named task.

## Core rule

> No geometry is sacred until it wins under frozen conditions—and a simpler baseline wins a tie.

## Five claim levels

**Visualization only** means the geometry organizes or displays information. Visual layout cannot strengthen a verifier result.

**Geometric optimization** means a declared geometry improved a frozen task metric against matched baselines and compute budgets.

**Physics-informed** means named physical equations, constraints, units, and parameter sources influenced the model, but the implementation may still violate those laws numerically.

**Physics-constrained** means residuals, conservation or balance checks, stability, convergence, boundaries, and failure thresholds are measured and enforced.

**Experimentally validated** requires an authorized real source, a predeclared experiment, calibration and instrument uncertainty, and a qualified external execution or acceptance record.

## Required mathematical declarations

Every registered experiment must state:

- task lane and claim level;
- dimensionality and coordinate system or chart;
- units for every physical quantity;
- the distance, metric, pseudometric, or directed cost definition;
- curvature sign and convention;
- whether the representation is intrinsic or embedded;
- initial and boundary conditions;
- discretization, mesh, solver, software version, and numerical tolerances;
- random seeds, source rights, data split, primary metric, acceptance threshold, and compute budget.

Terms such as *manifold*, *topological*, *geodesic*, *curvature*, and *non-Euclidean* must be tied to those definitions. A name without a measurable object is not a scientific result.

## Required comparisons

Every optimization experiment must include:

1. an incumbent or domain baseline;
2. a plain Euclidean or straight baseline;
3. a randomized or null baseline;
4. a geometry-only ablation;
5. an algorithm or control-only ablation;
6. the proposed hybrid.

All candidates use matched data, seeds, and compute budgets unless the protocol explicitly normalizes and reports the difference. Secondary metrics cannot rescue failure of the frozen primary metric.

## Physics and numerical checks

As applicable, the experiment must evaluate:

- dimensional consistency;
- coordinate-transform consistency;
- metric symmetry, or a declared reason for asymmetry;
- nonnegative distance, or a declared pseudometric;
- curvature convention consistency;
- initial and boundary consistency;
- numerical stability and resolution or mesh convergence;
- claimed invariance or equivariance;
- conservation or balance residuals;
- causal time order;
- capacity, collision, separation, material, thermal, flow, or other task constraints;
- uncertainty, repeated seeds, stress tests, out-of-distribution behavior, and compute cost.

Failures and incomplete results stay in the evidence package.

## Task lanes

Geometry comparisons are allowed only inside a named lane:

- routing and networks;
- formation and control;
- sensor coverage and tasking;
- materials, structures, and packaging;
- visualization and evidence navigation.

Results cannot be ranked across unrelated lanes. A geometry that helps routing is not thereby superior for control, materials, or reviewer navigation.

## Promotion boundaries

The following claims are prohibited without their named evidence:

- universal geometry superiority;
- “non-Euclidean is inherently better”;
- simulation equals field validation;
- visualization equals physics;
- curved geometry implies quantum behavior;
- topology without a defined invariant;
- manifold language without a metric or chart;
- physics validation without units and governing constraints;
- experimental validation without an external record.

## Relationship to LumenCore

The protocol strengthens LumenCore’s core lane: inspecting whether a technical claim is reproducible, bounded, and ready for the next evidence gate. It does not make LumenCore a general geometry laboratory, physics simulator, foundation-model company, or field-certification authority.
