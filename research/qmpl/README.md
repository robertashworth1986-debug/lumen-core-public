# QMPL Public-Safe Validation Suite

This folder contains executable baseline simulations for:

1. second-order coupled oscillators exchanging continuous or quantized phase states;
2. delay, packet-loss, sensor-noise, heterogeneity, disturbance, and recovery sweeps;
3. generic two-dimensional formation transitions between line, ring, V, and echelon
   target geometries.

## Critical boundary

The suite is **simulation-only**. It is not a flight controller, an aerodynamic
solver, an operational drone system, or external validation. Proprietary adaptive
weighting, private formation-selection logic, and patent-sensitive embodiments are
not included.

## Windows / PowerShell

First find likely LumenCore constants and lexicon files without modifying them:

```powershell
powershell -ExecutionPolicy Bypass -File .\research\qmpl\Run-QMPLSweep.ps1 -FindLumaFiles
```

Then run with the canonical files:

```powershell
powershell -ExecutionPolicy Bypass -File .\research\qmpl\Run-QMPLSweep.ps1 `
  -ConstantsPath "C:\path\to\constants.json" `
  -LexiconPath "C:\path\to\lexicon.json"
```

The files are read only to compute hashes. Their contents are not copied into the
public output.

## Outputs

Each run creates a timestamped directory containing:

- `phase_sweep_results.csv`
- `formation_transition_results.csv`
- `summary.json`
- `manifest.json`

The manifest records SHA-256 checksums for the runner, configuration, optional
constants/lexicon files, and every output artifact.
