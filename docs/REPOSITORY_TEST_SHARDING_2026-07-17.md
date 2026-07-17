# Repository Test Sharding - 2026-07-17

## Purpose

Run the complete repository test inventory without confusing cumulative runtime with a stuck test.

The measured July 17 audit collected 1,006 tests across 226 files. The full-universe locked-source replay accounted for about 223 seconds by itself, while several geometry groups required another three to four minutes. A single ten-minute wrapper was therefore too short for the complete suite even when its bounded groups passed.

## Commands

Inspect the deterministic plan without running tests:

```powershell
python code/ops/RUN_REPOSITORY_TEST_SHARDS.py --list
```

Run one 1-based shard and print a hash-bound receipt:

```powershell
python code/ops/RUN_REPOSITORY_TEST_SHARDS.py --shard 1 --timeout-seconds 600
```

Run all shards and preserve the receipt:

```powershell
python code/ops/RUN_REPOSITORY_TEST_SHARDS.py --all --timeout-seconds 600 --receipt out/ops/repository_test_shards_latest.json
```

## Boundary

The runner preserves the full-universe replay unchanged and isolates it from four balanced shards. A passing receipt proves only that the listed repository tests passed for the recorded source state and runtime. It does not establish external validation, agency approval, field performance, realized savings, patent validity, production readiness, or universal model superiority.
