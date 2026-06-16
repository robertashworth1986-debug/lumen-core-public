# Safety + Grant Evidence Hardening

## Summary

This branch adds a safe live-data/no-orders execution ladder and a grant evidence benchmark package.

## Safety Work

- Adds live-data/no-orders gate.
- Adds central order safety gate.
- Routes order router through safety gate.
- Adds safe live executor facade.
- Redirects legacy live compounding launchers to safe no-orders path.
- Adds tiny-live manual-arm readiness design without activation.

## Grant Evidence Work

- Adds grant evidence benchmark lab.
- Builds evidence cards for DICE, HarborSentinel, MissionWeave, NSF, TrackCast, and Safety Runtime.
- Verifies existing TrackCast stack artifacts.
- Builds submission pack with abstracts, benchmark table, budget template, portal mapping, and transition path.

## Safety Boundary

No live trading is enabled by this branch. Live-data/no-orders mode blocks order permission.

## Human Review Needed

- Confirm budget numbers.
- Add letters of support / pilot validation.
- Select target grant opportunity.
- Final claims review before submission.
