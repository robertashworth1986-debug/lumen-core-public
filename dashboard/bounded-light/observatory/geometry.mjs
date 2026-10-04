/**
 * Deterministic mathematical point clouds. No browser or package dependencies.
 * Coordinates are finite Float32 values inside a sphere of radius 1.8.
 * These are geometric visualizations; no physical simulation is implied.
 */

const PI = Math.PI;
const TAU = 2 * PI;
const GOLDEN = (Math.sqrt(5) - 1) / 2;
const MAX_RADIUS = 1.8;

export const GEOMETRY_KINDS = Object.freeze(['trefoil', 'hopf', 'gyroid', 'superformula']);

export const geometryMetadata = Object.freeze({
  trefoil: Object.freeze({
    title: 'Trefoil tube',
    subtitle: 'A (2, 3) torus knot',
    formula: 'C(t) = ((R + r cos 3t) cos 2t, (R + r cos 3t) sin 2t, r sin 3t)',
    surfaceFormula: 'P(t,v) = C(t) + a(t)[cos(v) N(t) + sin(v) B(t)]',
    description: 'A closed tube follows a trefoil: two turns around the torus and three turns through its hole.',
    assumptions: 'N = (cos 3t cos 2t, cos 3t sin 2t, sin 3t), T = C′/|C′|, B = T × N. Complexity controls tube corrugation; deformation changes the torus ratio and corrugation amplitude. This is parameter sampling, not uniform surface-area sampling.',
    sources: Object.freeze([]),
  }),
  hopf: Object.freeze({
    title: 'Hopf fibers',
    subtitle: 'Linked circles from the 3-sphere',
    formula: '(z₁, z₂) = (cos η eⁱᵗ, sin η eⁱ⁽ᵗ⁺ᵝ⁾)',
    surfaceFormula: 'P(t) = (Re z₁, Im z₁, Re z₂) / (1 − Im z₂)',
    description: 'Distinct fibers are circles on S³. Stereographic projection reveals their linked arrangement in three dimensions.',
    assumptions: 'A finite selection of fibers is shown, not the entire fibration. The projection is S³ → R³. The inverse goes in the opposite direction. η ≤ 0.95 keeps the projection denominator above 0.186. Each rendered sample lies on a true projected circle; there is no artificial tube thickness.',
    sources: Object.freeze(['https://arxiv.org/abs/2212.01642']),
  }),
  gyroid: Object.freeze({
    title: 'Gyroid approximation',
    subtitle: 'A trigonometric zero-isosurface',
    formula: 'sin x cos y + sin y cos z + sin z cos x = 0',
    surfaceFormula: 'A sin z + B cos z = C; A = cos x, B = sin y, C = −sin x cos y',
    description: 'A repeating, connected labyrinth sampled directly on the zero set of a three-term trigonometric field.',
    assumptions: 'This nodal approximation is not the exact minimal gyroid. Roots are solved analytically, rather than accepting a thick band around the surface. A bounded cube clips the infinite periodic surface. Deformation applies a stated anisotropic scale; cyclic axis sampling reduces directional bias but is not exactly uniform in surface area.',
    sources: Object.freeze(['https://doi.org/10.3390/mi13101632']),
  }),
  superformula: Object.freeze({
    title: 'Superformula shell',
    subtitle: 'A spherical product of Gielis curves',
    formula: 'r(θ) = (|cos(mθ/4)|ⁿ² + |sin(mθ/4)|ⁿ³)⁻¹/ⁿ¹',
    surfaceFormula: 'P(u,v) = (r₁(u)r₂(v)cos v cos u, r₁(u)r₂(v)cos v sin u, r₂(v)sin v)',
    description: 'Two superformula curves shape longitude and latitude, turning a sphere into a folded, symmetric shell.',
    assumptions: 'a = b = 1, positive exponents, and integer symmetry counts keep the surface closed and bounded. Zero deformation is exactly a sphere. Complexity changes symmetry counts. Equal-area sphere directions are mapped onto the shell, so the deformed samples are not uniform in surface area. Sharp ridges can occur.',
    sources: Object.freeze(['https://doi.org/10.3732/ajb.90.3.333']),
  }),
});

export const presets = Object.freeze([
  Object.freeze({ id: 'trefoil', name: 'Trefoil tube', kind: 'trefoil', count: 28000, complexity: 3, deformation: 0.55, seed: 42 }),
  Object.freeze({ id: 'hopf', name: 'Hopf fibers', kind: 'hopf', count: 24000, complexity: 3, deformation: 0.6, seed: 31415 }),
  Object.freeze({ id: 'gyroid', name: 'Gyroid approximation', kind: 'gyroid', count: 36000, complexity: 3, deformation: 0.18, seed: 27182 }),
  Object.freeze({ id: 'superformula', name: 'Superformula shell', kind: 'superformula', count: 28000, complexity: 3, deformation: 0.8, seed: 16180 }),
]);

function randomGenerator(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6D2B79F5) >>> 0;
    let n = Math.imul(state ^ (state >>> 15), 1 | state);
    n ^= n + Math.imul(n ^ (n >>> 7), 61 | n);
    return ((n ^ (n >>> 14)) >>> 0) / 4294967296;
  };
}

const fract = (x) => x - Math.floor(x);

function numberInRange(name, value, min, max, integer = false) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new TypeError(`${name} must be a finite number`);
  }
  if ((integer && !Number.isInteger(value)) || value < min || value > max) {
    throw new RangeError(`${name} must be ${integer ? 'an integer ' : ''}between ${min} and ${max}`);
  }
}

function validateOptions(options) {
  if (!options || typeof options !== 'object' || Array.isArray(options)) {
    throw new TypeError('options must be an object');
  }
  const { kind = 'trefoil', count = 18000, complexity = 3, deformation = 0.35, seed = 42 } = options;
  if (!GEOMETRY_KINDS.includes(kind)) throw new RangeError(`Unknown geometry kind: ${String(kind)}`);
  numberInRange('count', count, 1, 100000, true);
  numberInRange('complexity', complexity, 1, 5);
  numberInRange('deformation', deformation, 0, 1);
  numberInRange('seed', seed, 0, 99999, true);
  return { kind, count, complexity, deformation, seed };
}

function sampleTrefoil(out, phase, options, random) {
  const { count, complexity, deformation } = options;
  const R = 1.05;
  const r = 0.3 + 0.26 * deformation;
  const tubeRadius = 0.11;
  const amplitude = 0.28 * deformation;
  const corrugations = 2 + 2 * Math.round(complexity);
  const scale = MAX_RADIUS / (R + r + tubeRadius * (1 + amplitude));
  const shiftT = random();
  const shiftV = random();
  for (let i = 0; i < count; i++) {
    const u = fract((i + 0.5) / count + shiftT);
    const t = TAU * u;
    const v = TAU * fract(i * GOLDEN + shiftV);
    const c2 = Math.cos(2 * t), s2 = Math.sin(2 * t);
    const c3 = Math.cos(3 * t), s3 = Math.sin(3 * t);
    const radius = R + r * c3;
    const cx = radius * c2, cy = radius * s2, cz = r * s3;
    const tx = -3 * r * s3 * c2 - 2 * radius * s2;
    const ty = -3 * r * s3 * s2 + 2 * radius * c2;
    const tz = 3 * r * c3;
    const invLength = 1 / Math.hypot(tx, ty, tz);
    const nx = c3 * c2, ny = c3 * s2, nz = s3;
    const bx = (ty * nz - tz * ny) * invLength;
    const by = (tz * nx - tx * nz) * invLength;
    const bz = (tx * ny - ty * nx) * invLength;
    const a = tubeRadius * (1 + amplitude * Math.cos(corrugations * t));
    const cv = a * Math.cos(v), sv = a * Math.sin(v);
    out[3 * i] = scale * (cx + cv * nx + sv * bx);
    out[3 * i + 1] = scale * (cy + cv * ny + sv * by);
    out[3 * i + 2] = scale * (cz + cv * nz + sv * bz);
    phase[i] = u;
  }
  return { scale, R, r, tubeRadius, amplitude, corrugations };
}

function sampleHopf(out, phase, options, random) {
  const { count, complexity, deformation } = options;
  const ringCount = 2 + Math.round(complexity / 2);
  const fibersPerRing = 6 + 2 * Math.round(complexity);
  const fiberCount = ringCount * fibersPerRing;
  const etaMin = 0.25 + 0.1 * deformation;
  const etaMax = 0.65 + 0.3 * deformation;
  const scale = MAX_RADIUS / Math.sqrt((1 + Math.sin(etaMax)) / (1 - Math.sin(etaMax)));
  const betaShift = TAU * random();
  const tShift = TAU * random();
  const fibers = [];
  for (let j = 0; j < fiberCount; j++) {
    const ring = Math.floor(j / fibersPerRing);
    fibers.push({
      eta: etaMin + (etaMax - etaMin) * ring / (ringCount - 1),
      beta: TAU * ((j % fibersPerRing) / fibersPerRing + ring * GOLDEN) + betaShift,
    });
  }
  // Interleaving guarantees that truncating a cloud keeps all fibers represented.
  for (let i = 0; i < count; i++) {
    const j = i % fiberCount;
    const fiber = fibers[j];
    const sampleIndex = Math.floor(i / fiberCount);
    const samplesOnFiber = Math.floor((count - 1 - j) / fiberCount) + 1;
    const t = TAU * (sampleIndex + 0.5) / samplesOnFiber + tShift;
    const c = Math.cos(fiber.eta), s = Math.sin(fiber.eta);
    const denominator = 1 - s * Math.sin(t + fiber.beta);
    out[3 * i] = scale * c * Math.cos(t) / denominator;
    out[3 * i + 1] = scale * c * Math.sin(t) / denominator;
    out[3 * i + 2] = scale * s * Math.cos(t + fiber.beta) / denominator;
    phase[i] = j / (fiberCount - 1);
  }
  return { scale, ringCount, fibersPerRing, fiberCount, etaMin, etaMax, minimumDenominator: 1 - Math.sin(etaMax), fibers };
}

function sampleGyroid(out, phase, options, random) {
  const { count, complexity, deformation } = options;
  const halfExtent = PI * (0.9 + 0.22 * complexity);
  const axisScale = [1 + 0.15 * deformation, 1, 1 - 0.3 * deformation];
  const scale = MAX_RADIUS / (halfExtent * Math.hypot(...axisScale));
  let accepted = 0;
  let attempts = 0;
  const limit = Math.max(1000, count * 50);
  while (accepted < count && attempts++ < limit) {
    const x = (2 * random() - 1) * halfExtent;
    const y = (2 * random() - 1) * halfExtent;
    const A = Math.cos(x), B = Math.sin(y), C = -Math.sin(x) * Math.cos(y);
    const radius = Math.hypot(A, B);
    if (radius < 1e-12 || Math.abs(C) > radius) continue;
    const angle = Math.asin(Math.max(-1, Math.min(1, C / radius)));
    const delta = Math.atan2(B, A);
    const principal = (random() < 0.5 ? angle : PI - angle) - delta;
    const firstPeriod = Math.ceil((-halfExtent - principal) / TAU);
    const lastPeriod = Math.floor((halfExtent - principal) / TAU);
    if (firstPeriod > lastPeriod) continue;
    const z = principal + TAU * (firstPeriod + Math.floor(random() * (lastPeriod - firstPeriod + 1)));
    // F is invariant under cyclic permutations, so all three solve directions
    // lie on the same zero set. Apply anisotropic display scaling afterwards.
    let px, py, pz;
    if (accepted % 3 === 0) { px = x; py = y; pz = z; }
    else if (accepted % 3 === 1) { px = y; py = z; pz = x; }
    else { px = z; py = x; pz = y; }
    out[3 * accepted] = scale * axisScale[0] * px;
    out[3 * accepted + 1] = scale * axisScale[1] * py;
    out[3 * accepted + 2] = scale * axisScale[2] * pz;
    phase[accepted] = 0.5 + 0.2 * Math.sin(px) + 0.15 * Math.cos(py) + 0.15 * Math.sin(pz);
    accepted++;
  }
  if (accepted !== count) throw new Error('Gyroid sampler exceeded its bounded search budget');
  return { scale, halfExtent, axisScale, level: 0, attempts };
}

function superRadius(angle, m, n1, n2, n3) {
  return (Math.abs(Math.cos(m * angle / 4)) ** n2 + Math.abs(Math.sin(m * angle / 4)) ** n3) ** (-1 / n1);
}

function sampleSuperformula(out, phase, options, random) {
  const { count, complexity, deformation } = options;
  const longitude = { m: 4 + 2 * Math.round(complexity), n1: 2 - 1.35 * deformation, n2: 2 - 1.4 * deformation, n3: 2 - 1.4 * deformation };
  const latitude = { m: 4 + 4 * Math.round(complexity / 2), n1: 2 - 1.2 * deformation, n2: 2 - 1.1 * deformation, n3: 2 - 1.1 * deformation };
  const scale = 1.72;
  const shift = random();
  for (let i = 0; i < count; i++) {
    const u = TAU * fract(i * GOLDEN + shift) - PI;
    const z = 1 - 2 * (i + 0.5) / count;
    const v = Math.asin(z);
    const r1 = superRadius(u, longitude.m, longitude.n1, longitude.n2, longitude.n3);
    const r2 = superRadius(v, latitude.m, latitude.n1, latitude.n2, latitude.n3);
    const cv = Math.sqrt(Math.max(0, 1 - z * z));
    out[3 * i] = scale * r1 * r2 * cv * Math.cos(u);
    out[3 * i + 1] = scale * r1 * r2 * cv * Math.sin(u);
    out[3 * i + 2] = scale * r2 * z;
    phase[i] = 0.5 + 0.28 * z + 0.22 * Math.cos(longitude.m * u);
  }
  return { scale, longitude, latitude };
}

const samplers = { trefoil: sampleTrefoil, hopf: sampleHopf, gyroid: sampleGyroid, superformula: sampleSuperformula };

/**
 * @param {{kind?: 'trefoil'|'hopf'|'gyroid'|'superformula',count?: number,
 * complexity?: number,deformation?: number,seed?: number}} options
 * count: integer 1..100000; complexity: real 1..5; deformation: real 0..1;
 * seed: integer 0..99999. Complexity rounds symmetry/fiber counts where needed.
 * Same options produce byte-identical arrays in the same JS engine.
 * Math transcendental functions can differ in last bits across JS engines.
 * No normals are returned: Hopf fibers are curves and have no unique surface
 * normal. All arrays are caller-owned, and inputs/presets are never mutated.
 */
export function generateGeometry(options = {}) {
  const parameters = validateOptions(options);
  const positions = new Float32Array(parameters.count * 3);
  const phases = new Float32Array(parameters.count);
  const construction = samplers[parameters.kind](positions, phases, parameters, randomGenerator(parameters.seed));
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  let radius = 0;
  for (let i = 0; i < positions.length; i += 3) {
    for (let axis = 0; axis < 3; axis++) {
      min[axis] = Math.min(min[axis], positions[i + axis]);
      max[axis] = Math.max(max[axis], positions[i + axis]);
    }
    radius = Math.max(radius, Math.hypot(positions[i], positions[i + 1], positions[i + 2]));
  }
  return {
    kind: parameters.kind,
    count: parameters.count,
    positions,
    phases,
    bounds: { min, max, radius },
    parameters,
    construction,
    metadata: geometryMetadata[parameters.kind],
  };
}
