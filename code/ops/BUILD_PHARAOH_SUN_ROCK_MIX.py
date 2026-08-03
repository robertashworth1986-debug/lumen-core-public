from __future__ import annotations

import hashlib
import json
import math
import wave
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "output" / "audio"
WAV_PATH = OUT_DIR / "pharaoh_sun_original_rock_mix.wav"
RECEIPT_PATH = OUT_DIR / "pharaoh_sun_original_rock_mix_receipt.json"

SAMPLE_RATE = 44_100
BPM = 116
BEAT_SECONDS = 60.0 / BPM
BAR_SECONDS = BEAT_SECONDS * 4.0
TOTAL_BARS = 48
SEED = 260715


def midi_hz(note: float) -> float:
    return 440.0 * (2.0 ** ((note - 69.0) / 12.0))


def adsr(length: int, attack: float, decay: float, sustain: float, release: float) -> np.ndarray:
    if length <= 0:
        return np.zeros(0, dtype=np.float32)
    a = min(length, max(1, int(attack * SAMPLE_RATE)))
    d = min(length - a, max(1, int(decay * SAMPLE_RATE)))
    r = min(length - a - d, max(1, int(release * SAMPLE_RATE)))
    s = max(0, length - a - d - r)
    parts = [
        np.linspace(0.0, 1.0, a, endpoint=False, dtype=np.float32),
        np.linspace(1.0, sustain, d, endpoint=False, dtype=np.float32),
        np.full(s, sustain, dtype=np.float32),
        np.linspace(sustain, 0.0, r, endpoint=True, dtype=np.float32),
    ]
    return np.concatenate(parts)[:length]


def pan_stereo(signal: np.ndarray, pan: float) -> np.ndarray:
    pan = float(np.clip(pan, -1.0, 1.0))
    left = math.sqrt((1.0 - pan) * 0.5)
    right = math.sqrt((1.0 + pan) * 0.5)
    return np.column_stack((signal * left, signal * right)).astype(np.float32)


def synth_note(
    note: float,
    seconds: float,
    kind: str,
    amplitude: float,
    pan: float = 0.0,
    phase: float = 0.0,
) -> np.ndarray:
    length = max(1, int(seconds * SAMPLE_RATE))
    t = np.arange(length, dtype=np.float32) / SAMPLE_RATE
    f = midi_hz(note)
    angle = 2.0 * np.pi * f * t + phase
    if kind == "bass":
        mono = 0.72 * np.sin(angle) + 0.20 * np.sin(2.0 * angle) + 0.08 * np.sin(3.0 * angle)
        env = adsr(length, 0.008, 0.08, 0.72, min(0.09, seconds * 0.25))
        mono = np.tanh(mono * 1.5) * env
    elif kind == "pluck":
        saw = 2.0 * ((f * t + phase / (2.0 * np.pi)) % 1.0) - 1.0
        mono = 0.58 * saw + 0.30 * np.sin(angle) + 0.12 * np.sin(2.0 * angle)
        env = np.exp(-t * 7.0).astype(np.float32)
        mono = np.tanh(mono * 1.25) * env
    elif kind == "lead":
        vibrato = 0.010 * np.sin(2.0 * np.pi * 5.2 * t)
        lead_angle = 2.0 * np.pi * f * t + vibrato + phase
        mono = 0.58 * np.sin(lead_angle) + 0.25 * np.sin(2.0 * lead_angle) + 0.17 * np.sin(3.0 * lead_angle)
        env = adsr(length, 0.02, 0.10, 0.78, min(0.18, seconds * 0.30))
        mono = np.tanh(mono * 1.7) * env
    elif kind == "pad":
        mono = 0.48 * np.sin(angle) + 0.28 * np.sin(angle * 0.5) + 0.24 * np.sin(angle * 1.005)
        env = adsr(length, min(0.25, seconds * 0.20), 0.20, 0.72, min(0.35, seconds * 0.25))
        mono = mono * env
    else:
        mono = np.sin(angle) * adsr(length, 0.01, 0.05, 0.75, 0.08)
    return pan_stereo((mono * amplitude).astype(np.float32), pan)


def distorted_power_chord(root: int, seconds: float, amplitude: float, pan: float) -> np.ndarray:
    length = max(1, int(seconds * SAMPLE_RATE))
    t = np.arange(length, dtype=np.float32) / SAMPLE_RATE
    mono = np.zeros(length, dtype=np.float32)
    for interval, weight in ((0, 0.48), (7, 0.34), (12, 0.18)):
        f = midi_hz(root + interval)
        saw = 2.0 * ((f * t) % 1.0) - 1.0
        mono += weight * saw.astype(np.float32)
    env = adsr(length, 0.006, 0.08, 0.68, min(0.12, seconds * 0.25))
    mono = np.tanh(mono * 3.6) * env * amplitude
    kernel = np.ones(7, dtype=np.float32) / 7.0
    mono = np.convolve(mono, kernel, mode="same").astype(np.float32)
    return pan_stereo(mono, pan)


def kick(seconds: float = 0.34, amplitude: float = 0.85) -> np.ndarray:
    length = int(seconds * SAMPLE_RATE)
    t = np.arange(length, dtype=np.float32) / SAMPLE_RATE
    phase = 2.0 * np.pi * (82.0 * t - 50.0 * t * t)
    mono = np.sin(phase) * np.exp(-t * 14.0)
    click = np.exp(-t * 90.0) * np.sin(2.0 * np.pi * 1500.0 * t)
    return pan_stereo(np.tanh((mono + 0.12 * click) * 1.8).astype(np.float32) * amplitude, 0.0)


def snare(rng: np.random.Generator, seconds: float = 0.24, amplitude: float = 0.62) -> np.ndarray:
    length = int(seconds * SAMPLE_RATE)
    t = np.arange(length, dtype=np.float32) / SAMPLE_RATE
    noise = rng.normal(0.0, 1.0, length).astype(np.float32)
    high = np.concatenate(([noise[0]], np.diff(noise))).astype(np.float32)
    tone = np.sin(2.0 * np.pi * 190.0 * t)
    mono = (0.72 * high + 0.28 * tone) * np.exp(-t * 19.0)
    return pan_stereo(np.tanh(mono * 1.4).astype(np.float32) * amplitude, 0.04)


def hat(rng: np.random.Generator, seconds: float = 0.09, amplitude: float = 0.22, pan: float = 0.0) -> np.ndarray:
    length = int(seconds * SAMPLE_RATE)
    t = np.arange(length, dtype=np.float32) / SAMPLE_RATE
    noise = rng.normal(0.0, 1.0, length).astype(np.float32)
    high = np.concatenate(([noise[0]], np.diff(noise))).astype(np.float32)
    mono = high * np.exp(-t * 48.0) * amplitude
    return pan_stereo(mono, pan)


def add_clip(track: np.ndarray, clip: np.ndarray, start_seconds: float) -> None:
    start = max(0, int(start_seconds * SAMPLE_RATE))
    end = min(len(track), start + len(clip))
    if end > start:
        track[start:end] += clip[: end - start]


def section_for_bar(bar: int) -> str:
    if bar < 4:
        return "desert_dawn_intro"
    if bar < 16:
        return "stone_and_thunder"
    if bar < 28:
        return "pharaoh_sun_drive"
    if bar < 40:
        return "electric_nile_peak"
    if bar < 46:
        return "horizon_solo"
    return "solar_gate_outro"


def build_mix() -> tuple[np.ndarray, list[dict[str, object]]]:
    rng = np.random.default_rng(SEED)
    total_seconds = TOTAL_BARS * BAR_SECONDS + 2.0
    track = np.zeros((int(total_seconds * SAMPLE_RATE), 2), dtype=np.float32)
    events: list[dict[str, object]] = []

    # D Hijaz pitch material. The motifs are original and intentionally avoid quoted melodies.
    scale = [50, 51, 54, 55, 57, 58, 60, 62]
    progression = [50, 58, 55, 57]
    lead_motifs = [
        [62, 63, 66, 67, 66, 63, 62, 60],
        [62, 66, 67, 69, 67, 66, 63, 62],
        [69, 67, 66, 63, 62, 60, 58, 60],
        [62, 63, 66, 69, 70, 69, 67, 66],
    ]

    for bar in range(TOTAL_BARS):
        section = section_for_bar(bar)
        bar_start = bar * BAR_SECONDS
        root = progression[bar % len(progression)]
        events.append({"bar": bar + 1, "section": section, "root_midi": root})

        if section in {"desert_dawn_intro", "solar_gate_outro"}:
            for step, degree in enumerate((0, 2, 1, 4, 3, 2, 1, 0)):
                note = scale[degree] + (12 if bar % 2 else 0)
                add_clip(track, synth_note(note, BEAT_SECONDS * 0.42, "pluck", 0.24, pan=(-0.34 + 0.10 * step)), bar_start + step * BEAT_SECONDS * 0.5)
            add_clip(track, synth_note(root - 12, BAR_SECONDS * 0.92, "pad", 0.14, pan=0.0), bar_start)
        else:
            for beat in range(4):
                add_clip(track, distorted_power_chord(root, BEAT_SECONDS * 0.42, 0.22, -0.33), bar_start + beat * BEAT_SECONDS)
                add_clip(track, distorted_power_chord(root, BEAT_SECONDS * 0.42, 0.22, 0.33), bar_start + beat * BEAT_SECONDS + 0.012)
                add_clip(track, synth_note(root - 12, BEAT_SECONDS * 0.74, "bass", 0.32, pan=-0.06), bar_start + beat * BEAT_SECONDS)

            for beat in (0, 2):
                add_clip(track, kick(amplitude=0.78 if section != "electric_nile_peak" else 0.90), bar_start + beat * BEAT_SECONDS)
            for beat in (1, 3):
                add_clip(track, snare(rng), bar_start + beat * BEAT_SECONDS)
            for eighth in range(8):
                add_clip(track, hat(rng, pan=(-0.18 if eighth % 2 == 0 else 0.18)), bar_start + eighth * BEAT_SECONDS * 0.5)

            motif = lead_motifs[(bar // 2) % len(lead_motifs)]
            if section in {"pharaoh_sun_drive", "electric_nile_peak", "horizon_solo"}:
                density = 8 if section != "horizon_solo" else 12
                for step in range(density):
                    note = motif[step % len(motif)] + (12 if section == "horizon_solo" and step % 3 == 0 else 0)
                    start = bar_start + step * BAR_SECONDS / density
                    duration = BAR_SECONDS / density * 0.82
                    add_clip(track, synth_note(note, duration, "lead", 0.15 if section != "horizon_solo" else 0.20, pan=0.22), start)

        if bar in {15, 27, 39, 45}:
            for sixteenth in range(16):
                add_clip(track, snare(rng, seconds=0.13, amplitude=0.18 + sixteenth * 0.018), bar_start + sixteenth * BAR_SECONDS / 16.0)

    # Short stereo echo glues the synthetic guitar and lead without quoting any source recording.
    delay = int(BEAT_SECONDS * 0.75 * SAMPLE_RATE)
    wet = np.zeros_like(track)
    wet[delay:, 0] = track[:-delay, 1] * 0.16
    wet[delay:, 1] = track[:-delay, 0] * 0.16
    track += wet

    fade = int(2.0 * SAMPLE_RATE)
    track[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)[:, None]
    peak = float(np.max(np.abs(track)))
    if peak > 0.0:
        track = np.tanh(track * (1.35 / peak)).astype(np.float32)
        track *= 0.94 / max(float(np.max(np.abs(track))), 1e-9)
    return track, events


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    track, events = build_mix()
    pcm = np.clip(track * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(str(WAV_PATH), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())

    receipt = {
        "schema": "luma_original_music_receipt_v1",
        "title": "Pharaoh Sun - Original Rock Ritual",
        "wav_path": str(WAV_PATH.relative_to(ROOT)).replace("\\", "/"),
        "wav_sha256": sha256(WAV_PATH),
        "sample_rate_hz": SAMPLE_RATE,
        "channels": 2,
        "duration_seconds": round(len(track) / SAMPLE_RATE, 3),
        "tempo_bpm": BPM,
        "tonal_material": "D Hijaz-inspired original pitch set",
        "seed": SEED,
        "sections": events,
        "claim_boundary": (
            "This is an original instrumental composition generated from programmatic synthesis. "
            "It does not contain sampled recordings, quoted lyrics, or intentionally copied melodies."
        ),
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(WAV_PATH)
    print(RECEIPT_PATH)
    print(receipt["wav_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
