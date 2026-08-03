# DICE Abstract Postmortem

Date: 2026-07-25

Status: `OFFICIAL_FULL_PROPOSAL_DISCOURAGED_ROUTE_CLOSED`

## Decision Boundary

The official response discouraged a full proposal after comprehensive review. It
did not identify the abstract as a formatting or mandatory-conformance failure.
The cited weaknesses were the abstract's failure to articulate a convincing
ability to meet the program objectives and its failure to articulate a
compelling foundational capability leap.

This postmortem is an internal process audit. It does not infer unstated reviewer
reasoning, dispute the decision, authorize a reply, or reopen the closed route.

## What Was Submitted

- Abstract title: `Coherence-Bounded Peer Mesh: Sparse Task Markets and Local Inference Control for Resilient Heterogeneous AI Collectives`
- Receipt state: DARPA BAAT confirmed receipt on 2026-06-29.
- Candidate artifact: `LumenCore_DICE_Abstract_FINAL_CANDIDATE.docx`
- Controlling source: `HR001126S0010_OFFICIAL.pdf`

## Root Causes

### 1. The finalizer proved packaging, not reviewer fitness

`finalize_dice_abstract_candidate.py` checked section headings, draft-warning
removal, placeholders, ZIP membership, bytes, and hashes. It did not evaluate
whether the argument answered every program objective or research question.

### 2. The red-team score was self-referential

The prior reviewer gate awarded points when phrases appeared in a self-authored
Heilmeier matrix and when artifacts, manifests, and renders existed. A package
could therefore score 8/8 while its actual abstract still lacked the decisive
technical argument. File custody and cautious wording are valuable controls, but
they are not evidence of program fit.

### 3. No objective-to-claim trace was submission-blocking

The BAA asks TA1/TA2 performers to address decentralized coordination,
distributed context fusion, Byzantine resilience, TA1/TA2 invariants, local
inference control for open-weight and black-box agents, role-coherence
formalization, cognitive agility, adversarial robustness, and program metrics.
The abstract discussed most topics, but the process did not require a row for
each objective that bound:

1. the exact proposed claim,
2. the foundational leap,
3. the named state-of-the-art comparator,
4. the proposed experiment and metric,
5. current evidence and its applicability,
6. the falsifier or failure threshold, and
7. the team and compute needed to execute it.

### 4. The leap was asserted more strongly than it was differentiated

Sparse auctions, local reputation, context controls, role monitoring, and
adaptor interfaces were combined into one architecture. The abstract did not
show why the coupling was a new scientific principle rather than an aggregation
of known mechanisms, nor did it compare that coupling against named current
methods with a decisive experiment.

### 5. The evidence did not exercise the proposed scientific object

The strongest preliminary results came from stochastic task executors. The
abstract correctly disclosed that they were not language models. That preserved
claim honesty, but it also meant the evidence did not yet demonstrate
inference-time role control, long-horizon coherence, cognitive agility, or
heterogeneous open-weight and black-box behavior.

### 6. Key control quantities were not formally defined

The abstract referred to role drift, mission alignment, behavioral diversity,
confidence, and a finite coherence horizon. It did not provide the mathematical
definition, estimation method, calibration plan, or guarantee that would make
those quantities actionable to TA1.

### 7. The experiment was not mission-specific enough

The BAA rejects broadly aggregated content lacking mission-specific synthesis.
The abstract proposed general stressors and generic mission behavior, but did
not anchor the full TA1/TA2 argument in one concrete contested mission with
distributed information, contradictory evidence, role-specific success
criteria, and a named central orchestration baseline.

### 8. Execution credibility remained openly unresolved

The abstract disclosed a one-person organization, insufficient local compute for
program-scale foundation-model inference, and unnamed future collaborators.
That was honest, but the package did not contain commitments or resource access
strong enough to answer the Government's ability-to-execute concern.

### 9. Independent veto authority was missing

The drafting process, evidence synthesis, reviewer matrix, and final readiness
score were all produced inside the same local workflow. No separate reviewer
receipt was required to veto a technically weak package before finalization.

## Corrective Controls

Every future technical submission must fail closed unless all of the following
are present:

- current official source, amendment, deadline, timezone, route, and template;
- complete objective and evaluation-criterion crosswalk;
- one-sentence foundational leap with a named state-of-the-art comparator;
- proposed metric and acceptance threshold for every claimed objective;
- mission-specific experiment, adverse condition, and falsifier;
- evidence-applicability statement separating proxy, synthetic, replay,
  foundation-model, field, and independent evidence;
- named team roles, resource access, compute basis, and dependency commitments;
- cost and schedule tied to technical tasks;
- independent red-team receipt from someone or a process separate from the
  primary drafting pass; and
- fresh human action-time approval after all technical gates pass.

Formatting, file existence, hashes, privacy scans, and claim-boundary language
remain necessary, but none may be counted as a substitute for scientific and
program-fit conformance.
