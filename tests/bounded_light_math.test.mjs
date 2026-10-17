import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

// The browser imports this as an ES module. A data URL avoids this repository's
// CommonJS package default while executing the exact delivered source bytes.
const source = await readFile(new URL('../dashboard/bounded-light/math.js', import.meta.url), 'utf8');
const { C_METRES_PER_SECOND, lightTime, waveSample } = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`
);
const near = (value, expected, tolerance = 1e-12) => {
  assert.ok(Math.abs(value - expected) <= tolerance, `${value} != ${expected}`);
};

test('light travel reproduces exact SI reference distances and round trip', () => {
  assert.equal(C_METRES_PER_SECOND, 299792458);
  assert.deepEqual(lightTime(0), { seconds: 0, roundTripSeconds: 0 });
  assert.deepEqual(lightTime(299792.458), { seconds: 1, roundTripSeconds: 2 });
  near(lightTime(0.001).seconds, 3.3356409519815204e-9, 1e-23);
  near(lightTime(1000).seconds, 0.0033356409519815205, 1e-17);
});

test('invalid or out-of-domain distances cannot produce a model result', () => {
  for (const value of [-1, Infinity, -Infinity, NaN, 1e9 + 1, '1000', null, undefined]) {
    assert.throws(() => lightTime(value));
  }
  assert.ok(Number.isFinite(lightTime(1e9).roundTripSeconds));
});

test('wave phase preserves reinforcement, cancellation and one-cycle equivalence', () => {
  for (const theta of [0, 0.2, 1.8, 4, 6.1]) {
    const aligned = waveSample(theta, 0.7, 0);
    near(aligned.sum, 2 * aligned.first);
    near(waveSample(theta, 0.7, 180).sum, 0);
    near(waveSample(theta, 0.7, 360).sum, aligned.sum);
  }
  assert.equal(waveSample(0, 0, 180).peakAmplitude, 0);
  near(waveSample(0, 0, 90).peakAmplitude, Math.sqrt(2));
});

test('wave sampling rejects nonfinite and nonnumeric inputs', () => {
  assert.throws(() => waveSample(NaN, 0, 0));
  assert.throws(() => waveSample(0, Infinity, 0));
  assert.throws(() => waveSample(0, 0, '180'));
});
