// Explicit educational idealizations; not an engineering solver.
// c: https://physics.nist.gov/cuu/Constants/Value/c.html
export const C_METRES_PER_SECOND = 299792458;

function finiteNumber(value, name) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new TypeError(`${name} must be a finite number`);
  }
}

export function lightTime(distanceKm) {
  finiteNumber(distanceKm, 'distanceKm');
  if (distanceKm < 0 || distanceKm > 1e9) {
    throw new RangeError('distanceKm must be between 0 and 1,000,000,000');
  }
  const seconds = (distanceKm * 1000) / C_METRES_PER_SECOND;
  return { seconds, roundTripSeconds: 2 * seconds };
}

// Equal-amplitude, equal-frequency waves. xPhase and timePhase are radians.
export function waveSample(xPhase, timePhase, phaseDegrees) {
  [xPhase, timePhase, phaseDegrees].forEach((v, i) => finiteNumber(v, `wave input ${i}`));
  const phase = (phaseDegrees % 360) * Math.PI / 180;
  const first = Math.sin(xPhase - timePhase);
  const second = Math.sin(xPhase - timePhase + phase);
  const rawPeak = 2 * Math.abs(Math.cos(phase / 2));
  return { first, second, sum: first + second, peakAmplitude: rawPeak < 1e-12 ? 0 : rawPeak };
}

// Ring-torus geometry in normalized units, u/v in radians.
export function torusPoint(R, r, u, v) {
  [R, r, u, v].forEach((n, i) => finiteNumber(n, `torus input ${i}`));
  if (!(R > r && r > 0)) throw new RangeError('Ring torus requires R > r > 0');
  const radial = R + r * Math.cos(v);
  return { x: radial * Math.cos(u), y: radial * Math.sin(u), z: r * Math.sin(v) };
}
