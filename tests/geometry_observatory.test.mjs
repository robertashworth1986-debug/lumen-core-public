import test from 'node:test';
import assert from 'node:assert/strict';
import { GEOMETRY_KINDS, generateGeometry, presets, geometryMetadata } from '../dashboard/bounded-light/observatory/geometry.mjs';

const EPSILON = 8e-6; // Float32 output, including inverse projection/scale error.
const close = (actual, expected, tolerance = EPSILON) => assert.ok(Math.abs(actual - expected) < tolerance, `${actual} ≠ ${expected}`);

function validateCloud(cloud) {
  assert.ok(cloud.positions instanceof Float32Array);
  assert.ok(cloud.phases instanceof Float32Array);
  assert.equal(cloud.positions.length, 3 * cloud.count);
  assert.equal(cloud.phases.length, cloud.count);
  for (const n of cloud.positions) {
    assert.ok(Number.isFinite(n));
    assert.ok(Math.abs(n) <= 1.800001);
  }
  for (const n of cloud.phases) assert.ok(Number.isFinite(n) && n >= 0 && n <= 1);
  assert.ok(cloud.bounds.radius <= 1.800001);
  for (let axis = 0; axis < 3; axis++) assert.ok(cloud.bounds.min[axis] <= cloud.bounds.max[axis]);
}

test('default call and each preset produce complete finite point clouds', () => {
  validateCloud(generateGeometry());
  for (const preset of presets) {
    const input = { ...preset };
    const cloud = generateGeometry(input);
    validateCloud(cloud);
    assert.deepEqual(input, preset);
    assert.equal(cloud.metadata, geometryMetadata[preset.kind]);
    assert.ok(cloud.metadata.formula.length > 20);
  }
});

for (const kind of GEOMETRY_KINDS) {
  test(`${kind}: deterministic values, seed sensitivity, and independent output buffers`, () => {
    const options = { kind, count: 2048, complexity: 2.7, deformation: 0.65, seed: 99999 };
    const a = generateGeometry(options), b = generateGeometry(options);
    assert.deepEqual(a.positions, b.positions);
    assert.deepEqual(a.phases, b.phases);
    assert.notEqual(a.positions.buffer, b.positions.buffer);
    assert.notDeepEqual(a.positions, generateGeometry({ ...options, seed: 0 }).positions);
    a.positions[0] = 42;
    assert.notEqual(b.positions[0], 42);
  });

  test(`${kind}: finite output across parameter corners and one-point limit`, () => {
    for (const complexity of [1, 2, 3, 4, 5]) {
      for (const deformation of [0, 1]) {
        for (const seed of [0, 42, 99999]) {
          validateCloud(generateGeometry({ kind, count: 1024, complexity, deformation, seed }));
        }
      }
    }
    validateCloud(generateGeometry({ kind, count: 1, complexity: 1, deformation: 0, seed: 0 }));
    validateCloud(generateGeometry({ kind, count: 100000, complexity: 5, deformation: 1, seed: 99999 }));
  });
}

test('invalid inputs are rejected rather than coerced, silently clamped, or allocated', () => {
  for (const options of [null, [], 'trefoil', 0]) assert.throws(() => generateGeometry(options), TypeError);
  for (const kind of ['unknown', 'constructor', '__proto__', null, 1]) assert.throws(() => generateGeometry({ kind }), RangeError);
  for (const name of ['count', 'complexity', 'deformation', 'seed']) {
    for (const value of [NaN, Infinity, -Infinity, '2', null]) {
      assert.throws(() => generateGeometry({ [name]: value }), TypeError);
    }
  }
  for (const count of [0, -1, 0.5, 100001, 1e12]) assert.throws(() => generateGeometry({ count }), RangeError);
  for (const complexity of [0, 5.01]) assert.throws(() => generateGeometry({ complexity }), RangeError);
  for (const deformation of [-0.001, 1.001]) assert.throws(() => generateGeometry({ deformation }), RangeError);
  for (const seed of [-1, 100000, 1.5]) assert.throws(() => generateGeometry({ seed }), RangeError);
});

test('gyroid samples satisfy the independent implicit equation after undoing display scaling', () => {
  for (const complexity of [1, 3.4, 5]) {
    for (const deformation of [0, 0.5, 1]) {
      const cloud = generateGeometry({ kind: 'gyroid', count: 5000, complexity, deformation, seed: 78 });
      const { scale, axisScale, halfExtent, attempts } = cloud.construction;
      assert.ok(attempts < 5000 * 10, 'normal acceptance should be far below the search budget');
      for (let i = 0; i < cloud.positions.length; i += 3) {
        const [x, y, z] = [0, 1, 2].map(axis => cloud.positions[i + axis] / (scale * axisScale[axis]));
        for (const v of [x, y, z]) assert.ok(Math.abs(v) <= halfExtent + EPSILON);
        close(Math.sin(x) * Math.cos(y) + Math.sin(y) * Math.cos(z) + Math.sin(z) * Math.cos(x), 0);
      }
    }
  }
});

test('trefoil samples lie in normal cross sections at the claimed tube radius', () => {
  const cloud = generateGeometry({ kind: 'trefoil', count: 4096, complexity: 5, deformation: 1, seed: 100 });
  const { R, r, scale, tubeRadius, amplitude, corrugations } = cloud.construction;
  for (let i = 0; i < cloud.count; i++) {
    const t = cloud.phases[i] * 2 * Math.PI;
    const center = [(R + r * Math.cos(3 * t)) * Math.cos(2 * t), (R + r * Math.cos(3 * t)) * Math.sin(2 * t), r * Math.sin(3 * t)];
    const displacement = center.map((v, axis) => cloud.positions[3 * i + axis] / scale - v);
    close(Math.hypot(...displacement), tubeRadius * (1 + amplitude * Math.cos(corrugations * t)));
    // Independent central-difference tangent checks that the tube is normal to C.
    const centerAt = u => [(R + r * Math.cos(3 * u)) * Math.cos(2 * u), (R + r * Math.cos(3 * u)) * Math.sin(2 * u), r * Math.sin(3 * u)];
    const before = centerAt(t - 1e-5), after = centerAt(t + 1e-5);
    const tangent = before.map((v, axis) => (after[axis] - v) / 2e-5);
    close(displacement.reduce((sum, v, axis) => sum + v * tangent[axis], 0), 0);
  }
});

test('Hopf samples invert to S³ and retain their constant complex fiber ratio', () => {
  const cloud = generateGeometry({ kind: 'hopf', count: 10000, complexity: 5, deformation: 1, seed: 99999 });
  const { scale, fibers, fiberCount, minimumDenominator } = cloud.construction;
  assert.ok(minimumDenominator > 0.18);
  for (let i = 0; i < cloud.count; i++) {
    const fiber = fibers[i % fiberCount];
    const x = cloud.positions[3 * i] / scale, y = cloud.positions[3 * i + 1] / scale, z = cloud.positions[3 * i + 2] / scale;
    const s = x * x + y * y + z * z;
    const a = 2 * x / (1 + s), b = 2 * y / (1 + s), c = 2 * z / (1 + s), d = (s - 1) / (1 + s);
    close(a * a + b * b + c * c + d * d, 1);
    close(Math.hypot(a, b), Math.cos(fiber.eta));
    close(Math.hypot(c, d), Math.sin(fiber.eta));
    // z2 / z1 = tan(eta) exp(i beta), independent of the fiber coordinate t.
    close((a * c + b * d) / (a * a + b * b), Math.tan(fiber.eta) * Math.cos(fiber.beta));
    close((a * d - b * c) / (a * a + b * b), Math.tan(fiber.eta) * Math.sin(fiber.beta));
  }
});

test('two sampled Hopf circles have numerical Gauss linking number of magnitude one', () => {
  const reference = generateGeometry({ kind: 'hopf', count: 1, complexity: 2, deformation: 0.6 });
  const F = reference.construction.fiberCount, samples = 220;
  const cloud = generateGeometry({ kind: 'hopf', count: F * samples, complexity: 2, deformation: 0.6 });
  const point = (fiber, i) => [0, 1, 2].map(axis => cloud.positions[3 * ((i % samples) * F + fiber) + axis]);
  const segments = fiber => Array.from({ length: samples }, (_, i) => {
    const p = point(fiber, i), q = point(fiber, i + 1);
    return { midpoint: p.map((x, j) => (x + q[j]) / 2), vector: p.map((x, j) => q[j] - x) };
  });
  let sum = 0;
  for (const a of segments(0)) for (const b of segments(F - 1)) {
    const r = a.midpoint.map((x, j) => x - b.midpoint[j]);
    const u = a.vector, v = b.vector;
    const cross = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
    sum += r.reduce((s, x, j) => s + x * cross[j], 0) / Math.hypot(...r) ** 3;
  }
  close(Math.abs(sum / (4 * Math.PI)), 1, 0.003);
});

test('zero-deformation superformula is a sphere regardless of complexity', () => {
  for (const complexity of [1, 2.3, 5]) {
    const cloud = generateGeometry({ kind: 'superformula', count: 2048, complexity, deformation: 0 });
    for (let i = 0; i < cloud.positions.length; i += 3) {
      close(Math.hypot(cloud.positions[i], cloud.positions[i + 1], cloud.positions[i + 2]), 1.72, 1e-6);
    }
  }
});

test('deformed superformula is a positive bounded radial shell, not a filled volume', () => {
  const cloud = generateGeometry({ kind: 'superformula', count: 8000, complexity: 4, deformation: 1 });
  const { longitude, latitude, scale } = cloud.construction;
  const radial = (angle, p) => Math.pow(Math.pow(Math.abs(Math.cos(p.m * angle / 4)), p.n2) + Math.pow(Math.abs(Math.sin(p.m * angle / 4)), p.n3), -1 / p.n1);
  for (let i = 0; i < cloud.count; i++) {
    const x = cloud.positions[3 * i] / scale, y = cloud.positions[3 * i + 1] / scale, z = cloud.positions[3 * i + 2] / scale;
    const u = Math.atan2(y, x);
    const r1 = radial(u, longitude);
    const v = Math.atan2(z, Math.hypot(x, y) / r1);
    const r2 = radial(v, latitude);
    close(Math.hypot(x, y), r1 * r2 * Math.cos(v));
    close(z, r2 * Math.sin(v));
    assert.ok(Math.hypot(x, y, z) > 0.1);
    assert.ok(Math.hypot(x, y, z) <= 1.000001);
  }
});
