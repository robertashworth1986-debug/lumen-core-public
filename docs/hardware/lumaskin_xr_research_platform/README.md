# LumaSkin XR Research Platform

## Decision

LumaSkin V1 is a soft, instrumented research garment for testing spatial
vibrotactile cues and an XR comfort governor. It is deliberately narrower than
the earlier suit concepts:

1. It has no powered joints, strength amplification, propulsion, electrical
   muscle stimulation, pain stimulus, or autonomous force.
2. Its first executable artifact is a fail-closed cue controller, not a device
   driver.
3. Its first physical work is unoccupied bench and mannequin testing.
4. Any passive-fit or energized human study requires an institutional ethics or
   IRB determination, informed consent, supervision, stopping rules, and the
   prior hardware gates.

The commercial hypothesis is testable: a licensed cue-governor SDK plus a
reference garment may improve cue recognition or XR task performance while
keeping comfort, workload, and cybersickness inside preregistered limits. That
is a hypothesis, not a current result.

## Architecture

| Layer | V1 function | Boundary |
| --- | --- | --- |
| Soft garment | Adjustable carrier, quick release, removable modules | Not protective equipment |
| Vibrotactile zones | Twelve addressable ERM/LRA locations | No electrical stimulation or force assist |
| Sensing | IMU, contact pressure, surface temperature, current, strain, timestamps | Non-medical unless a separate reviewed pathway applies |
| Cue controller | Checks state, authority, zone, intensity, duration, frequency, and fault health | Reference monitor only; no hardware drivers |
| XR adapter | Receives bounded scene cues from the existing Luma Experience pipeline | Must fail silent on stale, malformed, or unsafe input |
| Evidence layer | Raw traces, manifests, hashes, preregistration, aggregate outcomes | Internal receipts are not independent validation |

The executable controller is
[`code/hardware/lumaskin_safety_controller.py`](../../../code/hardware/lumaskin_safety_controller.py).
The canonical protocol is
[`config/lumaskin_test_protocol_v1.json`](../../../config/lumaskin_test_protocol_v1.json).

## Research States

`POWERED_OFF -> BENCH_SAFE` is the only entry path. Each active test returns to
zero output before another mode begins.

- `MANNEQUIN_FIXTURE`: no occupant; locked fixture, current calibration, and
  trained supervision required.
- `PASSIVE_FIT`: a consented, supervised fit and quick-release session with all
  actuator outputs held at zero.
- `SINGLE_ZONE_HAPTIC`: one low-energy vibrotactile zone within the preliminary
  command envelope.
- `XR_MULTIMODAL`: at most two zones, only after the single-zone and independent
  synchronization gates pass.
- `FAULT_LOCKOUT`: always reachable and manually reset only when outputs are
  zero and critical health checks pass.

The numerical command envelope is a software development cap. It is not a
biological safety limit and cannot authorize human use.

## Eight Test Families

1. Cue latency, jitter, dropout, wrong-zone behavior, and fail-silent faults.
2. Visual, audio, and haptic synchronization using independent clocks.
3. Fit, contact pressure, temperature, range of motion, cleaning, and release.
4. Blinded spatial cue localization against sham and repeat-session baselines.
5. Counterbalanced XR comfort and cybersickness with task fidelity as a
   co-primary outcome.
6. Fatigue, workload, balance, movement burden, and possible load transfer.
7. A train-only adaptive cue policy against fixed and no-haptic baselines, with
   abstention and worst-participant reporting.
8. Consent mapping, data minimization, hash verification, clean-room replay,
   and independent reproduction.

The exact endpoints and acceptance logic are machine-readable in the canonical
protocol. Tests are defined, not yet run.

## Eight Authority Gates

1. Freeze requirements, hazards, claims, and configuration.
2. Exhaustively test the reference controller and synthetic faults.
3. Complete qualified unoccupied electrical, thermal, energy, and stop testing.
4. Complete mannequin pressure, temperature, range, and release fixtures.
5. Review skin-contact materials, hygiene, battery containment, and wearable
   hazards.
6. Obtain an institutional ethics or IRB determination, approved consent,
   eligibility rules, adverse-event rules, and trained supervision.
7. Run the preregistered, counterbalanced human-factors study.
8. Obtain independent protocol acceptance, reproduction, and a signed result
   receipt before enabling any public benefit claim.

Gates 1 through 6 are mandatory before energized human testing. Founder
self-authorization cannot clear them.

## Current Evidence

- The protocol, controller, test console, and concept visual are design
  artifacts.
- No garment has been fabricated or energized on a person.
- No comfort, motion-sickness, task-performance, fatigue, safety, or medical
  claim is validated.
- The lab console simulates gate decisions; it does not connect to hardware.
- The strongest immediate action is the AG-02 synthetic state and fault sweep.

## External Reference Basis

- [ISO 9241-920:2024 tactile and haptic interactions](https://www.iso.org/standard/80751.html)
- [IEC 62368-1:2023 energy-source safety framework](https://webstore.iec.ch/en/publication/69308)
- [ISO 10993-1:2025 biological evaluation within risk management](https://www.iso.org/standard/10993-1)
- [HHS OHRP human-subject regulations decision charts](https://www.hhs.gov/ohrp/regulations-and-policy/decision-charts/index.html)
- [NASA Task Load Index](https://www.nasa.gov/human-systems-integration-division/nasa-task-load-index-tlx/)
- [NASA motion-sickness measurement memorandum](https://human-factors.arc.nasa.gov/publications/NASA_TM_20205009977.pdf)
- [NIOSH industrial exoskeleton risk discussion](https://www.cdc.gov/niosh/bulletin/2020/industrial-exoskeletons.html)

These sources guide protocol design. They do not endorse LumaSkin, prove
conformity, or replace access to the full standards and qualified review.
