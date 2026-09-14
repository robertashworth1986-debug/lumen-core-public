# NIC/DPU Packet-Pipeline Foundation Receipt

Generated: 2026-09-14T05:48:35.031277+00:00

## Verified

- The bounded reference implementation compiled as strict C11 with warnings treated as errors.
- 7 deterministic parser and policy tests passed; 0 failed.
- The same vector suite completed under AddressSanitizer and UndefinedBehaviorSanitizer.
- The implementation is allocation-free and uses a fixed rule table and counters.
- Source and protocol files are SHA-256 identified in the receipt and run manifest.
- Compilation used the retained run snapshot. Source edits made after that snapshot are not substituted into this receipt.
- The pinned Zig version, matching sanitizer test summary and absence of sanitizer diagnostics were checked before publication.
- A separately identified sanitizer compiler detected deliberate heap-overflow and signed-overflow faults before testing the pipeline with identical sanitizer flags.
- 500000 generated input iterations passed with seed 20260914; the method is deterministic and is not coverage-guided fuzzing.

## Informative Host Measurement

- Packets processed: 250000
- Measured packets per second: 83333333.333
- Interpretation: informative host-user-space measurement only.

The timing is not a NIC, DPU, line-rate, production-latency, or cross-machine claim.

## Not Verified

- DPDK, XDP/eBPF, RDMA/RoCE, GPUDirect, NIC firmware, or DPU offload.
- NVIDIA BlueField hardware or DOCA SDK behavior.
- Production security, line-rate capacity, operational reliability, or expert certification.

## Next Evidence Gates

1. Extend generated property testing with coverage-guided fuzzing and IPv6 before broad parser claims.
2. Port the same policy contract to an isolated XDP/eBPF or DPDK harness.
3. Measure on named NIC hardware with a frozen traffic protocol and loss/latency metrics.
4. Port to a named DPU SDK and preserve host-versus-offload parity receipts.
5. Seek independent review before using expert, production, or hardware-performance language.
