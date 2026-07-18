# LumenShell Dual-Mode VTOL Research Architecture

## Decision

The intended system is not a conventional service robot. It is a shared
LumenShell architecture with two ground modes and one detachable propulsion
research module:

1. **Wearable ground mode:** a person is inside and remains the primary
   authority. Assistance is bounded, the propulsion module is deenergized, and
   quick release plus verified ground support are mandatory.
2. **Autonomous ground mode:** no person is inside. A separate controller may
   operate the suit as an unoccupied robot inside a controlled test area.
3. **Propulsion research mode:** the detachable fan module is tested first on
   an instrumented stand and later on an unoccupied, independently tethered
   system. The current architecture contains no occupied-flight state.

That separation is the main safety and credibility feature. Wearable assist,
autonomous behavior, and propulsion do not share unrestricted authority.

## What Sound And Frequency Do

Sound and frequency are useful, testable engineering channels here:

- microphone and accelerometer arrays for condition monitoring;
- ultrasonic ranging and short-range obstacle sensing;
- operational modal analysis of the frame and shell;
- active vibration and noise control within measured stability limits;
- fault detection for rotating machinery;
- wave-channel panel geometry tested for damping and impact behavior; and
- deterministic telemetry synchronized with motor, power, thermal, and motion
  data.

They are not presented as a source of free energy or as proven human-scale
lift. NASA's acoustic suspension work describes support of small objects near
an intense acoustic field, which does not establish a human-lift mechanism.
Primary lift remains a mass, thrust, power, thermal, control, and failure-case
problem that requires independent instrumented evidence.

## Safety Architecture

The proposed controls use three independent authority domains:

| Domain | Allowed authority | Prohibited authority |
| --- | --- | --- |
| Wearable controller | Bounded ground assistance from verified wearer intent | Autonomous occupancy, propulsion, or bypass of safety isolation |
| Autonomous controller | Unoccupied ground behavior and later tethered research | Motion while occupied or override of the safety controller |
| Safety controller | Energy isolation, watchdog, interlocks, fault lockout | Mission planning or performance optimization |

The executable reference monitor is
[`code/hardware/lumenshell_safety_state_machine.py`](../../../code/hardware/lumenshell_safety_state_machine.py).
It intentionally provides no hardware drivers or flight-control commands. It
exists so reviewers can exhaustively test the proposed interlocks now.

## Eight Authority Gates

The controlled requirements define eight gates. They move from source and
claim control, through passive fit, coupon evidence, ground actuation,
detached propulsion tests, unoccupied tethered integration, and finally a
written authority hold point. Gate 8 does not mean certified, safe for public
use, or approved for human flight. It means qualified independent parties have
accepted a documented basis for the next bounded test.

The machine-readable source is
[`system_requirements.json`](system_requirements.json).

## Prototype Ladder

1. Freeze mission, interfaces, hazards, claims, and acceptance metrics.
2. Build only an unpowered adjustable fit and egress rig.
3. Test wave-channel material coupons against three conventional baselines.
4. Test one actuator and joint on a guarded, tethered bench.
5. Demonstrate the unoccupied ground frame with a hardwired stop and fault
   injection.
6. Test each detached propulsion module in a qualified contained facility.
7. Integrate only an unoccupied system under independent physical tether.
8. Stop for independent aerospace, medical, safety, and regulatory review.

No step is skipped because a simulation, render, patent filing, or internal
test looks promising.

## Current Evidence Status

- The render is a concept asset, not CAD or a fabricated prototype.
- The state machine is an executable requirements model, not flight software.
- The frequency hypotheses are preregistration candidates, not performance
  results.
- No lift, damping, safety, autonomy, runtime, or reliability claim has passed
  independent validation.
- The electric-vehicle honeycomb battery remains a separate research and
  licensing lane; it is not the suit battery.

## External Reference Basis

- [FAA aircraft certification overview](https://www.faa.gov/newsroom/how-it-works-aircraft-certification)
- [FAA special airworthiness certificates](https://www.faa.gov/aircraft/air_cert/aw_cert/special_aw_certificates)
- [FAA AC 90-89C flight-test handbook](https://www.faa.gov/airports/resources/advisory_circulars/index.cfm/go/document.information/documentID/1041650)
- [NIOSH Center for Occupational Robotics Research](https://www.cdc.gov/niosh/centers/robotics.html)
- [NIOSH industrial exoskeleton risk discussion](https://www.cdc.gov/niosh/bulletin/2020/industrial-exoskeletons.html)
- [NASA acoustic suspension record](https://ntrs.nasa.gov/citations/19830028575)

These references frame the research path. They do not endorse LumenShell or
prove compliance.
