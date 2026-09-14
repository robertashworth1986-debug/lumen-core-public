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
- A separately identified compiler must detect deliberate AddressSanitizer and
  UndefinedBehaviorSanitizer faults before its vector-suite run is accepted.
- SHA-256 receipts bind retained source snapshots actually used for compilation.
- An optional frozen generator checks parser, policy and counter invariants over
  deterministic arbitrary bytes, protocol templates, mutations and truncations.

## Sanitizer assurance correction - September 14, 2026

The earlier builder treated `-fsanitize=address,undefined` plus a successful exit
as evidence that both sanitizers were active. A deliberate one-byte heap
allocation followed by an out-of-bounds write **exited successfully without an
ASAN diagnostic** under the pinned Windows Zig 0.15.2 driver. Supplying the
address flag separately failed to link the missing ASAN runtime. The
[Zig driver source](https://raw.githubusercontent.com/ziglang/zig/0.15.2/src/main.zig)
handles the recognized `undefined` option internally and does not forward the
combined option's unrecognized address component in that path.

Consequently, earlier flag-based receipts do not establish AddressSanitizer
execution. The original seven vector outcomes remain recorded, but the old
ASAN assurance is withdrawn for the reproduced environment. Earlier frozen
protocols and receipts are retained without alteration.

The v2 builder requires both deliberate-fault controls to exit nonzero with
their specific diagnostics. A generic crash, silent success, or diagnostic
with a zero exit is insufficient. It then compiles the vector suite and optional
generated supplement with the same sanitizer compiler and flags, rejects
sanitizer diagnostics even when the target exits zero, and requires matching
vector counts. The primary strict C11 build still requires Zig **0.15.2**.

The local replacement was the portable UCRT x86-64
[LLVM-MinGW 20260908 / Clang 23.1.1 release](https://github.com/mstorsjo/llvm-mingw/releases/tag/20260908).
Its downloaded archive SHA-256 was
`1bcf74d06b724aeecaa6412ca85f5b26fb1da770e7cdcefa9263c9c5c3ad34b6`,
matching the official release asset digest. The builder records the selected
compiler executable hash and version; that is not a complete toolchain
dependency attestation. No global PATH, registry, service or application
configuration was changed for this local experiment.

## Generated-input result - September 14, 2026

The unchanged generator, seed **20260914** and **500,000** iterations produced:

| Parser outcome | Generated iterations |
|---|---:|
| Parsed | 228,933 |
| Non-IPv4 | 128,504 |
| Truncated | 135,592 |
| Malformed | 6,971 |
| Total | 500,000 |

Both deliberate-fault controls detected their faults, the seven vectors passed,
and the generated run had no reported invariant failure or ASAN/UBSAN finding.
This is one frozen deterministic experiment, not 500,000 independent tests.
It checks declared status/action ranges, malformed-input dropping, fragment
port handling, initialized-view repeatability, parser/pipeline agreement,
per-packet counter partitions and preservation of input bytes. Inputs include
offsets 0, 1 and 3 and a declared maximum frame length of 65,553 bytes.

The supplement is
`config/nic_dpu_packet_pipeline_property_protocol_v1.json`; it does not rewrite
the August 17 protocol. The initial run used the same generator but its ASAN
assurance was withdrawn. The verified-toolchain rerun reproduced all four
outcome counts. Neither run provides coverage-guided fuzzing, exhaustive
coverage, checksum validation, IPv6, stacked VLAN support, independent review,
hardware measurements, security certification or production authorization.

The retained correction and v2 run are under
`evidence/hardware/nic_dpu_packet_pipeline_20260914/`.

## Custody repair

Before compilation, the builder copies all package inputs into its unique run
directory. It compiles the retained C sources and checks their hashes again
before publishing. Edits to the original worktree during compilation cannot be
substituted into the receipt. A changed retained input prevents publication.
Mirror packages include all run-manifest dependencies, the retained sources,
control sources and logs. Two disposable mirror destinations were hash-checked;
the established E-drive mirrors were not modified by the September 14 review.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pip install ziglang==0.15.2
# Set this to an installed Clang with working ASAN and UBSAN runtimes.
$env:LUMA_NIC_SANITIZER_CC = 'C:\path\to\llvm-mingw\bin\x86_64-w64-mingw32-clang.exe'
.\.venv\Scripts\python.exe code\ops\BUILD_NIC_DPU_PACKET_PIPELINE_EVIDENCE.py --property-cases 500000
# Optional, explicit copy to the established E-drive destinations:
.\.venv\Scripts\python.exe code\ops\BUILD_NIC_DPU_PACKET_PIPELINE_EVIDENCE.py --mirror --property-cases 500000
.\.venv\Scripts\python.exe -m pytest -q tests\test_nic_dpu_packet_pipeline.py
```

The generated receipt is `out/hardware/nic_dpu_packet_pipeline/nic_dpu_packet_pipeline_latest.json`.
The `--mirror` option writes and hash-verifies the same bounded package at the established LumaProofVault, LumenCoreSync, and legacy institutional-stack E-drive destinations. Mirror integrity is custody evidence, not public publication or hardware validation.

## Evidence Ladder

| Stage | Required work | Current status |
|---|---|---|
| C11 reference fast path | Strict compile, deterministic parsing/policy tests, hashes | Implemented and locally testable |
| Parser hardening | Property tests, fuzzing, IPv6, stacked VLANs, options | Frozen generated-property supplement passed; remaining scope open |
| Kernel or poll-mode path | Port the same contract to XDP/eBPF or DPDK | Not started |
| NIC measurement | Named hardware, frozen traffic, loss/latency/CPU metrics | Not started |
| DPU offload | Named SDK/hardware, host/offload parity, resource accounting | Not started |
| Independent review | External reproducer and dated technical assessment | Not started |

## Claim Boundary

The present evidence supports one narrow statement: a deterministic C11 packet parser and fixed policy path is implemented and tested under the frozen local protocol. It does not establish deep C expertise, NIC or DPU expertise, security, production readiness, hardware acceleration, line rate, or NVIDIA technology experience.

Expert language becomes defensible only after the higher stages are completed with reproducible receipts and independent scrutiny. The useful move is to accumulate that evidence rather than changing the title first.
