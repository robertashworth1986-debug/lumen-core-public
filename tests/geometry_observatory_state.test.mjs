import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { generateGeometry, GEOMETRY_KINDS } from '../dashboard/bounded-light/observatory/geometry.mjs';

// Execute the exact browser-delivered state source despite the repository's
// CommonJS default. No copied implementation or native canvas dependency.
const source = await readFile(new URL('../dashboard/bounded-light/observatory/state.js', import.meta.url));
const { DEFAULT_STATE, PALETTES, validateState, encodeState, decodeState, projectPoint, svgSnapshot } = await import(
  `data:text/javascript;base64,${source.toString('base64')}`
);

test('Observatory state defaults, supported settings, and share links round-trip exactly', () => {
  const defaultsBefore = { ...DEFAULT_STATE };
  assert.deepEqual(validateState({}), DEFAULT_STATE);
  assert.notEqual(validateState({}), DEFAULT_STATE);
  for (const kind of GEOMETRY_KINDS) {
    for (const palette of Object.keys(PALETTES)) {
      for (const count of [12000, 32000, 64000]) {
        const state = { ...DEFAULT_STATE, kind, palette, count, seed: 99999 };
        const link = encodeState(state);
        assert.ok(link.startsWith('#view='));
        assert.ok(link.length < 2500);
        assert.deepEqual(decodeState(link), state);
        assert.deepEqual(validateState(state), state);
      }
    }
  }
  for (const boundary of [
    { complexity: 1, deformation: 0, seed: 0, exposure: 0.4, yaw: -180, pitch: -85, zoom: 0.65 },
    { complexity: 5, deformation: 1, seed: 99999, exposure: 1.8, yaw: 180, pitch: 85, zoom: 1.5 },
  ]) {
    const input = { ...DEFAULT_STATE, ...boundary };
    assert.deepEqual(decodeState(encodeState(input)), input);
  }
  assert.deepEqual(DEFAULT_STATE, defaultsBefore);
});

test('Observatory state rejects unknown fields, prototype names, wrong types, and out-of-range values', () => {
  const invalid = [
    null, [], '', false, 1,
    { kind: 'constructor' }, { kind: '__proto__' }, { kind: 'unknown' },
    { palette: 'constructor' }, { palette: '__proto__' }, { palette: 'unknown' },
    { version: 0 }, { version: 2 }, { version: '1' }, { unexpected: 1 },
    JSON.parse('{"__proto__":{"palette":"ember"}}'),
    { count: 11999 }, { count: 12001 }, { count: 64001 }, { count: 100000 },
    { complexity: 0 }, { complexity: 2.5 }, { complexity: 6 },
    { deformation: -0.01 }, { deformation: 1.01 },
    { seed: -1 }, { seed: 0.5 }, { seed: 100000 },
    { exposure: 0.39 }, { exposure: 1.81 },
    { yaw: -181 }, { yaw: 181 }, { pitch: -86 }, { pitch: 86 },
    { zoom: 0.64 }, { zoom: 1.51 },
  ];
  for (const field of ['count', 'complexity', 'deformation', 'seed', 'exposure', 'yaw', 'pitch', 'zoom']) {
    for (const value of [NaN, Infinity, -Infinity, '1', null, undefined, true]) {
      invalid.push({ [field]: value });
    }
  }
  for (const input of invalid) {
    assert.throws(() => validateState(input));
    assert.throws(() => encodeState(input));
  }
  assert.equal(Object.getPrototypeOf(validateState({})), Object.prototype);
  assert.equal(Object.hasOwn(Object.prototype, 'palette'), false);
});

test('share decoding fails closed for malformed, oversized, and disallowed payloads', () => {
  for (const hash of ['', '#unrelated', '#view', '#other=value']) assert.equal(decodeState(hash), null);
  for (const hash of ['#view=', '#view=%zz', '#view=%E0%A4%A', '#view=' + 'x'.repeat(2500)]) {
    assert.throws(() => decodeState(hash));
  }
  for (const payload of [null, [], { kind: 'bad' }, { seed: -1 }, { unexpected: 1 }, { version: 2 }]) {
    assert.throws(() => decodeState('#view=' + encodeURIComponent(JSON.stringify(payload))));
  }
  assert.throws(() => decodeState('#view=%7B%22seed%22%3A1e999%7D'));
  assert.throws(() => decodeState('#view=' + encodeURIComponent(JSON.stringify(DEFAULT_STATE)) + 'trailing'));
});

test('default projection keeps over 99 percent of each shape visible in narrow and wide viewports', () => {
  for (const kind of GEOMETRY_KINDS) {
    const cloud = generateGeometry({ ...DEFAULT_STATE, kind, count: 12000 });
    for (const [width, height] of [[390, 520], [1600, 1000], [2560, 1440]]) {
      let visible = 0;
      for (let i = 0; i < cloud.positions.length; i += 3) {
        const point = projectPoint(...cloud.positions.subarray(i, i + 3), DEFAULT_STATE, width, height);
        for (const value of [point.x, point.y, point.depth, point.scale]) assert.ok(Number.isFinite(value));
        assert.ok(point.scale > 0);
        if (point.x >= 0 && point.x <= width && point.y >= 0 && point.y <= height) visible++;
      }
      assert.ok(visible / cloud.count > 0.99, `${kind}: ${visible}/${cloud.count} visible at ${width}×${height}`);
    }
  }
});

test('SVG exports have bounded finite geometry and metadata that round-trips as XML text', () => {
  const width = 20480, height = 11520;
  for (const kind of GEOMETRY_KINDS) {
    const state = { ...DEFAULT_STATE, kind, count: 64000 };
    const cloud = generateGeometry(state);
    const svg = svgSnapshot(cloud, state, width, height);
    assert.ok(svg.startsWith('<svg xmlns="http://www.w3.org/2000/svg"'));
    assert.ok(svg.endsWith('</g></svg>'));
    assert.ok(svg.includes(`width="${width}" height="${height}"`));
    assert.ok(svg.includes(`viewBox="0 0 ${width} ${height}"`));
    assert.ok(!/NaN|Infinity|<script|\bonload\s*=|javascript:/i.test(svg));
    assert.ok(svg.length < 4e6);
    const circles = [...svg.matchAll(/<circle cx="([^"]+)" cy="([^"]+)" r="([^"]+)" fill="rgb\(([^)]+)\)" opacity="([^"]+)"\/>/g)];
    assert.ok(circles.length > 1000 && circles.length <= 24000);
    assert.equal(circles.length, (svg.match(/<circle\b/g) || []).length);
    for (const match of circles) {
      const [, x, y, radius, rgb, opacity] = match;
      for (const value of [x, y, radius, opacity, ...rgb.split(',')]) assert.ok(Number.isFinite(Number(value)));
      assert.ok(Math.abs(Number(x)) < 2 * width && Math.abs(Number(y)) < 2 * height);
      assert.ok(Number(radius) > 0 && Number(radius) < height / 100);
      assert.ok(Number(opacity) >= 0 && Number(opacity) <= 1);
      for (const channel of rgb.split(',').map(Number)) assert.ok(Number.isInteger(channel) && channel >= 0 && channel <= 255);
    }
    const metadata = /<metadata>([\s\S]*?)<\/metadata>/.exec(svg)?.[1];
    assert.ok(metadata);
    assert.ok(!metadata.includes('<'), 'Metadata must not introduce XML elements');
    assert.ok(!/&(?!(?:amp|lt|gt|quot|apos);)/.test(metadata), 'Metadata must not contain bare XML ampersands');
    const decoded = metadata.replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&quot;', '"').replaceAll('&apos;', "'").replaceAll('&amp;', '&');
    assert.deepEqual(JSON.parse(decoded), state);
  }
});

test('SVG export rejects invalid dimensions, invalid state, and XML injection before returning a file', () => {
  const cloud = generateGeometry({ ...DEFAULT_STATE, count: 12000 });
  for (const invalid of [0, 99, 30001, -1, 100.5, NaN, Infinity, '3840', null]) {
    assert.throws(() => svgSnapshot(cloud, DEFAULT_STATE, invalid, 2160));
    assert.throws(() => svgSnapshot(cloud, DEFAULT_STATE, 3840, invalid));
  }
  for (const invalid of [null, [], { count: 12001 }, { palette: '__proto__' }, { zoom: Infinity }, { unexpected: 1 }]) {
    assert.throws(() => svgSnapshot(cloud, invalid));
  }
  // Admitted state values are enums/numbers. XML-bearing strings must fail
  // schema validation instead of reaching title or metadata serialization.
  for (const attack of ['</metadata><script>alert(1)</script>', 'x & y', '"><svg onload="alert(1)">']) {
    assert.throws(() => svgSnapshot(cloud, { ...DEFAULT_STATE, kind: attack }));
    assert.throws(() => svgSnapshot(cloud, { ...DEFAULT_STATE, palette: attack }));
  }
  assert.throws(() => svgSnapshot({ positions: new Float32Array(2), phases: new Float32Array(1) }, DEFAULT_STATE));
  assert.ok(svgSnapshot(cloud, DEFAULT_STATE, 100, 100).includes('width="100" height="100"'));
  assert.ok(svgSnapshot(cloud, DEFAULT_STATE, 30000, 30000).includes('width="30000" height="30000"'));
});
