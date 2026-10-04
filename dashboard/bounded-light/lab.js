import { lightTime, waveSample } from './math.js';

const byId = id => document.getElementById(id);
const distance = byId('distance');
const phase = byId('phase');
const canvas = byId('wave');
const ctx = canvas.getContext('2d');
const motion = byId('wave-motion');
let playing = false, animation = 0, elapsed = 0, lastTime = null;

function formatTime(seconds) {
  if (seconds === 0) return '0 s';
  const units = seconds < 1e-6 ? [1e9, 'ns'] : seconds < .001 ? [1e6, 'µs'] : seconds < 1 ? [1e3, 'ms'] : [1, 's'];
  return `${(seconds * units[0]).toLocaleString('en-US', { maximumSignificantDigits: 7 })} ${units[1]}`;
}

function updateDistance() {
  try {
    if (distance.value.trim() === '') throw new Error('Enter a distance from 0 to 1,000,000,000 kilometres.');
    const result = lightTime(Number(distance.value));
    byId('one-way').textContent = formatTime(result.seconds);
    byId('round-trip').textContent = formatTime(result.roundTripSeconds);
    byId('distance-error').textContent = '';
    distance.removeAttribute('aria-invalid');
    return result;
  } catch {
    byId('distance-error').textContent = 'Enter a distance from 0 to 1,000,000,000 kilometres.';
    byId('one-way').textContent = '—';
    byId('round-trip').textContent = '—';
    distance.setAttribute('aria-invalid', 'true');
    return null;
  }
}
distance.addEventListener('input', updateDistance);
document.querySelectorAll('[data-distance]').forEach(button => button.addEventListener('click', () => {
  distance.value = button.dataset.distance;
  updateDistance();
}));

function drawWaves() {
  if (!ctx) return;
  const w = canvas.width, h = canvas.height, left = 40, right = w - 10, mid = h / 2, scale = (h - 54) / 4;
  const degrees = Number(phase.value);
  ctx.clearRect(0, 0, w, h);
  ctx.font = '18px Arial'; ctx.textAlign = 'right';
  for (let y = -2; y <= 2; y++) {
    const py = mid - y * scale;
    ctx.strokeStyle = y === 0 ? '#51666b' : '#284047'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(left, py); ctx.lineTo(right, py); ctx.stroke();
    ctx.fillStyle = '#95abb0'; ctx.fillText(String(y), 28, py + 6);
  }
  for (const [key, colour, width] of [['first', '#eac489', 2], ['second', '#8cdde3', 2], ['sum', '#fff8eb', 3]]) {
    ctx.strokeStyle = colour; ctx.lineWidth = width; ctx.beginPath();
    for (let px = left; px <= right; px += 2) {
      const theta = (px - left) / (right - left) * Math.PI * 6;
      const sample = waveSample(theta, elapsed, degrees);
      const py = mid - sample[key] * scale;
      if (px === left) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();
  }
  const peak = waveSample(0, 0, degrees).peakAmplitude;
  byId('phase-value').textContent = `${degrees}°`;
  byId('peak').textContent = peak.toFixed(4);
  canvas.setAttribute('aria-label', `Two unit-amplitude sine waves and their sum, phase difference ${degrees} degrees. Sum peak amplitude ${peak.toFixed(4)}. Vertical scale minus 2 to plus 2. Three spatial cycles shown.`);
}
function frame(time) {
  if (!playing) return;
  if (lastTime !== null) elapsed += Math.min((time - lastTime) / 1000, .1) * 1.2;
  lastTime = time; drawWaves(); animation = requestAnimationFrame(frame);
}
function setPlaying(value) {
  playing = Boolean(value); lastTime = null;
  cancelAnimationFrame(animation);
  motion.textContent = playing ? 'Pause waves' : 'Play waves';
  motion.setAttribute('aria-pressed', String(playing));
  if (playing) animation = requestAnimationFrame(frame);
}
phase.addEventListener('input', drawWaves);
motion.addEventListener('click', () => setPlaying(!playing));
document.addEventListener('visibilitychange', () => { if (document.hidden) setPlaying(false); });

const descriptions = [
  'A sculptural connection across an impossible-looking distance. The wormhole notes supply a visual question, not an engineered passage.',
  'Light becomes a sequence of boundaries across space. The neighbouring travel-time model gives distance a measurable meaning.',
  'A cube, a torus and a spiral core translate motifs from LumenShell and LumaSpiral into imagined architecture.',
  'EchoForm-inspired networks become a luminous vault. The structure is an artistic metaphor for relationships among many parts.',
  'Two ripple origins meet in glass-like folds. The adjacent interference model explores one precise mathematical idea behind the inspiration.',
  'Organic gold and geometric cyan share one path. A metaphor for human imagination and calculation working together, not an anatomical model.'
];
const dialog = byId('art-dialog');
document.querySelectorAll('[data-art]').forEach(button => button.addEventListener('click', () => {
  const index = Number(button.dataset.art);
  const image = button.querySelector('img');
  const title = button.closest('article').querySelector('h3').textContent;
  byId('dialog-image').src = image.src; byId('dialog-image').alt = image.alt;
  byId('dialog-number').textContent = `WORLD ${String(index + 1).padStart(2, '0')} / 06`;
  byId('dialog-title').textContent = title;
  byId('dialog-description').textContent = descriptions[index];
  dialog.showModal();
}));
byId('dialog-close').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if (event.target === dialog) { const rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close(); } });

updateDistance(); drawWaves();

// Feature-detected browser tool interface. All changes also have visible controls.
const modelContext = document.modelContext;
if (modelContext && typeof modelContext.registerTool === 'function') {
  const lifecycle = new AbortController();
  window.addEventListener('pagehide', () => lifecycle.abort(), { once: true });
  const register = tool => Promise.resolve(modelContext.registerTool(tool, { signal: lifecycle.signal })).catch(() => {});
  const snapshot = () => ({ distanceKm: distance.value.trim() === '' ? null : Number(distance.value), travelTime: (() => { try { return distance.value.trim() === '' ? null : lightTime(Number(distance.value)); } catch { return null; } })(), phaseDegrees: Number(phase.value), sumPeakAmplitude: waveSample(0, 0, Number(phase.value)).peakAmplitude, playing });
  try {
    register({ name: 'get_bounded_light_model', annotations: { readOnlyHint: true, untrustedContentHint: false }, description: 'Read the current idealized light-travel and wave-superposition model settings and calculated results.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, execute: async () => ({ content: [{ type: 'text', text: JSON.stringify(snapshot()) }] }) });
    register({ name: 'configure_bounded_light_model', annotations: { readOnlyHint: false, untrustedContentHint: false }, description: 'Set the visible distance in kilometres and/or the relative phase in degrees for the two educational models.', inputSchema: { type: 'object', properties: { distanceKm: { type: 'number', minimum: 0, maximum: 1000000000 }, phaseDegrees: { type: 'integer', minimum: 0, maximum: 360 } }, additionalProperties: false }, execute: async args => {
      if (!args || typeof args !== 'object' || Array.isArray(args) || Object.keys(args).some(key => !['distanceKm', 'phaseDegrees'].includes(key))) throw new TypeError('Provide distanceKm and/or phaseDegrees only');
      if (args.distanceKm !== undefined) lightTime(args.distanceKm);
      if (args.phaseDegrees !== undefined && (!Number.isInteger(args.phaseDegrees) || args.phaseDegrees < 0 || args.phaseDegrees > 360)) throw new RangeError('phaseDegrees must be an integer from 0 to 360');
      if (args.distanceKm !== undefined) distance.value = String(args.distanceKm);
      if (args.phaseDegrees !== undefined) phase.value = String(args.phaseDegrees);
      updateDistance(); drawWaves(); return { content: [{ type: 'text', text: JSON.stringify(snapshot()) }] };
    } });
  } catch { /* Optional capability; ordinary browser controls remain available. */ }
}
