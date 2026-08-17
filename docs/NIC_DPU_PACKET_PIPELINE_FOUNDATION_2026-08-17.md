# NIC/DPU Packet-Pipeline Foundation

## Decision

LumenCore now has a bounded C systems-programming lane for packet parsing and policy decisions. This is a host-user-space reference implementation and evidence harness. It is not a NIC driver, DPU application, DPDK program, line-rate result, production control, or expert certification.

## Implemented Surface

- Strict C11 compilation with `-Wall -Wextra -Werror -pedantic`.
- Allocation-free Ethernet II and single 802.1Q VLAN parsing.
- IPv4 version, header-length, total-length, and transport-length checks.
- TCP and UDP source/destination port extraction for non-fragmented packets.
- Fragment-aware behavior that does not claim unavailable transport ports.
- Fixed first-match rules with pass, drop, and queue actions.
- Monotonic parse and action counters.
- Seven deterministic vector tests and a non-gating host timing measurement.
- AddressSanitizer and UndefinedBehaviorSanitizer smoke execution of the vector suite.
- SHA-256 source and evidence receipts.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pip install ziglang==0.15.2
.\.venv\Scripts\python.exe code\ops\BUILD_NIC_DPU_PACKET_PIPELINE_EVIDENCE.py
.\.venv\Scripts\python.exe code\ops\BUILD_NIC_DPU_PACKET_PIPELINE_EVIDENCE.py --mirror
.\.venv\Scripts\python.exe -m pytest -q tests\test_nic_dpu_packet_pipeline.py
```

The generated receipt is `out/hardware/nic_dpu_packet_pipeline/nic_dpu_packet_pipeline_latest.json`.
The `--mirror` option writes and hash-verifies the same bounded package at the established LumaProofVault, LumenCoreSync, and legacy institutional-stack E-drive destinations. Mirror integrity is custody evidence, not public publication or hardware validation.

## Evidence Ladder

| Stage | Required work | Current status |
|---|---|---|
| C11 reference fast path | Strict compile, deterministic parsing/policy tests, hashes | Implemented and locally testable |
| Parser hardening | Property tests, fuzzing, IPv6, stacked VLANs, options | Not started |
| Kernel or poll-mode path | Port the same contract to XDP/eBPF or DPDK | Not started |
| NIC measurement | Named hardware, frozen traffic, loss/latency/CPU metrics | Not started |
| DPU offload | Named SDK/hardware, host/offload parity, resource accounting | Not started |
| Independent review | External reproducer and dated technical assessment | Not started |

## Claim Boundary

The present evidence supports one narrow statement: a deterministic C11 packet parser and fixed policy path is implemented and tested under the frozen local protocol. It does not establish deep C expertise, NIC or DPU expertise, security, production readiness, hardware acceleration, line rate, or NVIDIA technology experience.

Expert language becomes defensible only after the higher stages are completed with reproducible receipts and independent scrutiny. The useful move is to accumulate that evidence rather than changing the title first.
