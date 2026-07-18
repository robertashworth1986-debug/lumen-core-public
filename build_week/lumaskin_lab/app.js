const interlockDefinitions = [
  ["estop_released", "E-stop released", true],
  ["outputs_zeroed", "Outputs zeroed", true],
  ["occupant_detected", "Occupant detected", false],
  ["fixture_locked", "Fixture locked", true],
  ["quick_release_verified", "Quick release verified", false],
  ["wearer_stop_signal_verified", "Wearer stop verified", false],
  ["skin_contact_ok", "Skin-contact check", true],
  ["thermal_envelope_ok", "Thermal envelope", true],
  ["electrical_envelope_ok", "Electrical envelope", true],
  ["battery_health_ok", "Battery health", true],
  ["communications_ok", "Communications", true],
  ["calibration_current", "Calibration current", true],
  ["session_timer_armed", "Session timer armed", false],
  ["trained_supervisor_present", "Trained supervisor", true],
  ["ethics_or_irb_determination_recorded", "Ethics/IRB determination", false],
  ["informed_consent_recorded", "Informed consent", false],
  ["single_zone_gate_passed", "Single-zone gate", false],
  ["cross_modal_sync_validated", "Cross-modal sync", false]
];

const interlockRoot = document.querySelector("#interlocks");
const decision = document.querySelector("#decision");
const modes = [...document.querySelectorAll(".mode")];
const zones = [...document.querySelectorAll(".zone")];
const intensity = document.querySelector("#intensity");
const duration = document.querySelector("#duration");
const frequency = document.querySelector("#frequency");
let requestedState = "BENCH_SAFE";
let selectedZone = "left_shoulder";
let canonicalRecord = {
  loaded: false,
  programStatus: "BENCH_PROTOCOL_READY_HUMAN_TESTS_BLOCKED",
  assetStatus: "CONCEPT_DIAGRAM_NOT_ENGINEERING_VALIDATION",
  humanTestingAuthorized: false,
  authorityGatesOpen: 8
};

for (const [id, label, checked] of interlockDefinitions) {
  const row = document.createElement("label");
  row.className = "interlock";
  row.innerHTML = `<input type="checkbox" data-interlock="${id}" ${checked ? "checked" : ""}><span>${label}</span>`;
  interlockRoot.append(row);
}

function interlocks() {
  return Object.fromEntries(
    [...document.querySelectorAll("[data-interlock]")].map((input) => [
      input.dataset.interlock,
      input.checked
    ])
  );
}

function show(kind, message) {
  decision.className = `decision ${kind}`;
  decision.textContent = message;
}

function updateOutputs() {
  document.querySelector("#intensityValue").value = Number(intensity.value).toFixed(2);
  document.querySelector("#durationValue").value = `${duration.value} ms`;
  document.querySelector("#frequencyValue").value = `${frequency.value} Hz`;
}

for (const input of [intensity, duration, frequency]) {
  input.addEventListener("input", updateOutputs);
}

for (const mode of modes) {
  mode.addEventListener("click", () => {
    modes.forEach((item) => item.classList.remove("active"));
    mode.classList.add("active");
    requestedState = mode.dataset.state;
    show("neutral", `${requestedState} selected. Evaluate the current interlocks.`);
  });
}

for (const zone of zones) {
  zone.addEventListener("click", () => {
    zones.forEach((item) => item.classList.remove("selected"));
    zone.classList.add("selected");
    selectedZone = zone.dataset.zone;
    document.querySelector("#selectedZone").textContent = selectedZone;
  });
}

function firstFailed(checks) {
  const state = interlocks();
  for (const [key, message] of checks) {
    if (!state[key]) return message;
  }
  return null;
}

function evaluate() {
  const state = interlocks();
  const critical = firstFailed([
    ["estop_released", "LOCKOUT: E-stop is not released."],
    ["thermal_envelope_ok", "LOCKOUT: thermal envelope failed."],
    ["electrical_envelope_ok", "LOCKOUT: electrical envelope failed."],
    ["battery_health_ok", "LOCKOUT: battery health failed."],
    ["communications_ok", "LOCKOUT: communications are unhealthy."]
  ]);
  if (critical) return show("fail", critical);
  if (!state.outputs_zeroed) return show("fail", "DENIED: mode entry requires zeroed outputs.");

  if (requestedState === "BENCH_SAFE") {
    if (state.occupant_detected) return show("fail", "DENIED: bench mode requires no occupant.");
    if (!state.fixture_locked) return show("fail", "DENIED: bench fixture is not locked.");
    return show("pass", "PASS: BENCH_SAFE interlocks are satisfied. No wearable output is issued.");
  }

  if (requestedState === "MANNEQUIN_FIXTURE") {
    if (state.occupant_detected) return show("fail", "DENIED: mannequin testing requires no occupant.");
    const missing = firstFailed([
      ["fixture_locked", "DENIED: mannequin fixture is not locked."],
      ["calibration_current", "DENIED: calibration is stale."],
      ["trained_supervisor_present", "DENIED: trained supervisor is absent."]
    ]);
    return missing ? show("fail", missing) : show("pass", "PASS: MANNEQUIN_FIXTURE is authorized for synthetic evaluation.");
  }

  const humanMissing = firstFailed([
    ["occupant_detected", "HOLD: verified occupancy is missing."],
    ["quick_release_verified", "HOLD: quick release is not verified."],
    ["wearer_stop_signal_verified", "HOLD: wearer stop signal is not verified."],
    ["skin_contact_ok", "HOLD: skin-contact check is incomplete."],
    ["calibration_current", "HOLD: calibration is stale."],
    ["session_timer_armed", "HOLD: session timer is not armed."],
    ["trained_supervisor_present", "HOLD: trained supervisor is absent."],
    ["ethics_or_irb_determination_recorded", "HOLD: institutional ethics or IRB determination is absent."],
    ["informed_consent_recorded", "HOLD: informed consent is absent."]
  ]);
  if (humanMissing) return show("lock", humanMissing);
  if (!canonicalRecord.loaded) {
    return show("lock", "HOLD: canonical status packet is unavailable; participant modes fail closed.");
  }
  if (!canonicalRecord.humanTestingAuthorized) {
    return show(
      "lock",
      `HOLD: canonical controller record has ${canonicalRecord.authorityGatesOpen} open authority gate(s). UI controls cannot authorize participant testing.`
    );
  }

  if (requestedState === "PASSIVE_FIT") {
    return show("pass", "PASS: passive fit is gate-complete in this simulation. Outputs remain zero.");
  }

  if (Number(intensity.value) > 0.25) return show("fail", "DENIED: intensity exceeds the 0.25 preliminary command cap.");
  if (Number(duration.value) > 250) return show("fail", "DENIED: duration exceeds the 250 ms preliminary command cap.");
  if (Number(frequency.value) < 20 || Number(frequency.value) > 180) return show("fail", "DENIED: frequency is outside the 20-180 Hz preliminary command band.");

  if (requestedState === "XR_MULTIMODAL") {
    if (!state.single_zone_gate_passed) return show("lock", "HOLD: single-zone evidence gate has not passed.");
    if (!state.cross_modal_sync_validated) return show("lock", "HOLD: cross-modal synchronization is not validated.");
  }

  show("pass", `PASS: ${requestedState} synthetic cue for ${selectedZone} is inside the command envelope. No hardware output was sent.`);
}

document.querySelector("#evaluate").addEventListener("click", evaluate);
document.querySelector("#fault").addEventListener("click", () => {
  show("fail", "FAULT_LOCKOUT: all modeled outputs are forced to zero; manual service reset required.");
});

async function loadProtocol() {
  const body = document.querySelector("#testRows");
  try {
    const [protocolResponse, packetResponse] = await Promise.all([
      fetch("../../config/lumaskin_test_protocol_v1.json", {cache: "no-store"}),
      fetch("../../out/ops/lumaskin_protocol_packet_latest.json", {cache: "no-store"})
    ]);
    if (!protocolResponse.ok) throw new Error(`protocol HTTP ${protocolResponse.status}`);
    if (!packetResponse.ok) throw new Error(`status packet HTTP ${packetResponse.status}`);
    const protocol = await protocolResponse.json();
    const packet = await packetResponse.json();
    const projection = packet.public_projection || {};
    const expectedProgramStatus = document.body.dataset.programStatus;
    const expectedAssetStatus = document.body.dataset.assetStatus;
    if (projection.program_status !== expectedProgramStatus) {
      throw new Error("program-status projection mismatch");
    }
    if (projection.asset_status !== expectedAssetStatus) {
      throw new Error("asset-status projection mismatch");
    }
    if (projection.human_testing_authorized !== false) {
      throw new Error("unexpected participant authorization");
    }
    canonicalRecord = {
      loaded: true,
      programStatus: projection.program_status,
      assetStatus: projection.asset_status,
      humanTestingAuthorized: projection.human_testing_authorized,
      authorityGatesOpen: packet.authority_gates.filter((gate) => gate.status !== "PASS").length
    };
    document.querySelector("#canonicalStatus").textContent =
      `Human tests locked / ${canonicalRecord.authorityGatesOpen} gates open`;
    body.innerHTML = protocol.test_families.map((item) => `
      <tr><td>${item.id}</td><td>${item.name}</td><td>${item.stage}</td><td>Defined / not run</td></tr>
    `).join("");
    show("neutral", "Canonical record loaded. BENCH_SAFE is available; participant modes remain locked.");
  } catch (error) {
    canonicalRecord.loaded = false;
    body.innerHTML = `<tr><td colspan="4">Protocol unavailable: ${error.message}</td></tr>`;
    document.querySelector("#canonicalStatus").textContent = "Human tests locked / record unavailable";
    show("lock", "HOLD: canonical status packet failed to load; participant modes fail closed.");
  }
}

updateOutputs();
loadProtocol();
