"""Run the exact frozen verifier with NPZ entries decoded once per context.

No validation predicate, source identity, numeric comparison or checksum is
changed. The wrapper is separately identified in the verification receipt.
"""
import argparse
import time
from pathlib import Path

import numpy as np
import run_stage8 as run
import verify_stage8 as frozen


class CachedNPZ:
    def __init__(self, archive):
        self.files = list(archive.files)
        try:
            self.arrays = {key: archive[key] for key in self.files}
        finally:
            archive.close()

    def __getitem__(self, key):
        return self.arrays[key]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.arrays.clear()


def verify(packet, inputs, expected):
    original_load = np.load
    def cached_load(*args, **kwargs):
        result = original_load(*args, **kwargs)
        return CachedNPZ(result) if isinstance(result, np.lib.npyio.NpzFile) else result
    start = time.perf_counter()
    try:
        np.load = cached_load
        receipt = frozen.verify(packet, inputs, expected)
    finally:
        np.load = original_load
    receipt.update(io_cache="NPZ entries decoded once per context; all frozen verifier checks retained",
                   cache_wrapper_sha256=run.sha(Path(__file__)),
                   frozen_verifier_sha256=run.sha(Path(frozen.__file__)),
                   elapsed_seconds=time.perf_counter() - start)
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--expected-manifest-sha256", required=True)
    p.add_argument("--receipt", type=Path, required=True)
    a = p.parse_args()
    frozen.require(not a.receipt.exists(), "Refusing to overwrite verification receipt")
    frozen.require(not a.receipt.resolve().is_relative_to(a.packet.resolve()), "Receipt must be outside immutable packet")
    r = verify(a.packet, a.inputs, a.expected_manifest_sha256)
    run.write_json(a.receipt, r)
    print(__import__("json").dumps(r, indent=2))
