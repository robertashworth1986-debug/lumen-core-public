"use strict";

const Core = window.ProofLockCore;
const Lattice = window.ProofLockLattice;

if (!Core || !Lattice) throw new Error("ProofLock core modules failed to load");

const elements = {
  editor: document.querySelector("#receiptEditor"),
  load: document.querySelector("#loadSampleButton"),
  verify: document.querySelector("#verifyButton"),
  guided: document.querySelector("#guidedProofButton"),
  export: document.querySelector("#exportButton"),
  identity: document.querySelector("#receiptIdentity"),
  headerStatus: document.querySelector("#headerStatus"),
  headerStatusDot: document.querySelector("#headerStatusDot"),
  integrity: document.querySelector("#integrityMetric"),
  artifacts: document.querySelector("#artifactMetric"),
  gates: document.querySelector("#gateMetric"),
  decision: document.querySelector("#decisionMetric"),
  receiptHash: document.querySelector("#receiptHashLabel"),
  boundary: document.querySelector("#claimBoundary"),
  artifactRows: document.querySelector("#artifactRows"),
  artifactSummary: document.querySelector("#artifactSummary"),
  gateGrid: document.querySelector("#gateGrid"),
  gateSummary: document.querySelector("#gateSummary"),
  eventLog: document.querySelector("#eventLog"),
  verificationTime: document.querySelector("#verificationTime"),
  verificationLive: document.querySelector("#verificationLive"),
  latticeCanvas: document.querySelector("#evidenceLattice"),
  latticeStatus: document.querySelector("#latticeStatus"),
};

let latestReport = null;
let canonicalSampleText = "";
let guidedProofRunning = false;

function shortHash(hash) {
  return hash ? `${hash.slice(0, 14)}...${hash.slice(-10)}` : "not available";
}

function statusClass(status) {
  const normalized = String(status || "OPEN").toUpperCase();
  if (normalized === "PASS") return "pass";
  if (normalized === "FAIL") return "fail";
  return "open";
}

function makePill(status) {
  const pill = document.createElement("span");
  pill.className = `pill ${statusClass(status)}`;
  pill.textContent = String(status || "OPEN");
  return pill;
}

function makeCode(text) {
  const code = document.createElement("code");
  code.textContent = String(text || "");
  return code;
}

function renderArtifactRows(report) {
  const rows = report.artifacts.map((artifact) => {
    const row = document.createElement("tr");
    const artifactCell = document.createElement("td");
    artifactCell.dataset.label = "Artifact";
    const name = document.createElement("strong");
    name.textContent = artifact.artifact_id || "Unnamed artifact";
    artifactCell.append(name, document.createElement("br"), makeCode(artifact.repo_relative_path));

    const roleCell = document.createElement("td");
    roleCell.dataset.label = "Role";
    roleCell.textContent = artifact.role || "Not declared";

    const hashCell = document.createElement("td");
    hashCell.dataset.label = "Observed SHA-256";
    hashCell.append(makeCode(shortHash(artifact.observed_sha256)));

    const statusCell = document.createElement("td");
    statusCell.dataset.label = "Status";
    statusCell.append(makePill(artifact.hash_matches ? "PASS" : "FAIL"));
    row.append(artifactCell, roleCell, hashCell, statusCell);
    return row;
  });

  if (!rows.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.className = "empty-cell";
    cell.textContent = "No artifacts declared";
    row.append(cell);
    rows.push(row);
  }
  elements.artifactRows.replaceChildren(...rows);
}

function renderGateRows(report) {
  const rows = report.gates.map((gate) => {
    const card = document.createElement("article");
    card.className = "gate-row";
    const header = document.createElement("header");
    const heading = document.createElement("h3");
    heading.textContent = gate.label || gate.gate_id || "Unnamed gate";
    header.append(heading, makePill(gate.status));
    const basis = document.createElement("p");
    basis.textContent = gate.basis || "No basis recorded.";
    card.append(header, basis);
    return card;
  });
  elements.gateGrid.replaceChildren(...rows);
}

function reportStatus(report) {
  if (!report.integrity_valid) return "Verification failed";
  if (report.promotion_allowed) return "Verified and releasable";
  return "Verified, promotion held";
}

function renderReport(report, receipt) {
  const matches = report.artifact_hash_match_count;
  const total = report.artifact_count;
  const heldGates = report.required_open_or_failed_gates.length;
  const status = reportStatus(report);
  elements.identity.textContent = receipt?.subject?.name || receipt?.receipt_id || "Unnamed receipt";
  elements.integrity.textContent = report.integrity_valid ? "Verified" : "Failed";
  elements.artifacts.textContent = `${matches} / ${total}`;
  elements.gates.textContent = `${heldGates} held`;
  elements.decision.textContent = report.recorded_decision || "Unknown";
  elements.receiptHash.textContent = `SHA-256 ${shortHash(report.receipt_hash.computed)}`;
  elements.boundary.textContent = report.claim_boundary || "No claim boundary recorded.";
  elements.artifactSummary.textContent = `${matches} of ${total} matched`;
  elements.gateSummary.textContent = report.promotion_allowed ? "Promotion gate clear" : "Promotion held";
  elements.verificationTime.textContent = new Date(report.verified_utc).toLocaleString();
  elements.headerStatusDot.className = `status-dot ${report.integrity_valid ? (report.promotion_allowed ? "pass" : "open") : "fail"}`;
  elements.headerStatus.textContent = status;
  elements.verificationLive.textContent = `${status}. ${matches} of ${total} artifacts match. ${heldGates} required gates are held.`;
  renderArtifactRows(report);
  renderGateRows(report);

  const logLines = [
    `receipt ${report.receipt_hash.matches ? "PASS" : "FAIL"} ${report.receipt_hash.computed || "unavailable"}`,
    `artifacts ${matches}/${total} matched`,
    `required gates held ${heldGates}`,
    `decision ${report.recorded_decision || "INVALID"}`,
  ];
  report.errors.forEach((error) => logLines.push(`error ${error}`));
  report.warnings.forEach((warning) => logLines.push(`warning ${warning}`));
  elements.eventLog.textContent = logLines.join("\n");
  elements.export.disabled = !report.integrity_valid;
  Lattice.setState({ receipt, report });
}

async function loadArtifact(path) {
  const target = Core.resolveArtifactUrl(path, window.location.href);
  const response = await fetch(target, {
    cache: "no-store",
    credentials: "same-origin",
    redirect: "error",
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.arrayBuffer();
}

async function fetchCanonicalSample() {
  const target = new URL("sample_receipt.json", window.location.href);
  if (target.origin !== window.location.origin) throw new Error("Sample receipt escaped same-origin boundary");
  const response = await fetch(target, { cache: "no-store", credentials: "same-origin", redirect: "error" });
  if (!response.ok) throw new Error(`Unable to load sample receipt: HTTP ${response.status}`);
  const text = Core.normalizeEditorText(await response.text());
  return { text, receipt: JSON.parse(text) };
}

function setCommandState(disabled) {
  elements.load.disabled = disabled;
  elements.verify.disabled = disabled;
  elements.guided.disabled = disabled;
  elements.editor.readOnly = disabled;
}

async function runVerification(options = {}) {
  const previousVerifyState = elements.verify.disabled;
  elements.verify.disabled = true;
  elements.eventLog.textContent = options.stage === "tamper"
    ? "Verifying the guided in-memory mutation..."
    : "Verifying canonical receipt and repository artifacts...";
  let receipt = options.receipt || null;
  try {
    if (!receipt) receipt = JSON.parse(elements.editor.value);
    latestReport = await Core.verifyReceipt(receipt, { loadArtifact });
    renderReport(latestReport, receipt);
    return latestReport;
  } catch (error) {
    latestReport = null;
    const failure = Core.parseFailureReport(error);
    renderReport(failure, receipt);
    elements.export.disabled = true;
    return failure;
  } finally {
    elements.verify.disabled = previousVerifyState;
  }
}

async function loadSample(options = {}) {
  elements.eventLog.textContent = "Loading canonical sample receipt...";
  const sample = await fetchCanonicalSample();
  canonicalSampleText = sample.text;
  elements.editor.value = sample.text;
  if (options.verify !== false) await runVerification({ receipt: sample.receipt, stage: "canonical" });
  return sample;
}

async function runGuidedProof() {
  if (guidedProofRunning) return;
  guidedProofRunning = true;
  setCommandState(true);
  elements.guided.textContent = "Guided proof running";
  try {
    const result = await Lattice.runGuidedProof({
      loadSample: async () => {
        const sample = await fetchCanonicalSample();
        canonicalSampleText = sample.text;
        elements.editor.value = sample.text;
        return sample;
      },
      verify: async ({ receipt, text, stage }) => {
        elements.editor.value = text;
        return runVerification({ receipt, stage });
      },
    });
    if (result.status === "restored" && elements.editor.value !== canonicalSampleText) {
      throw new Error("Guided proof did not restore the exact canonical sample text");
    }
  } catch (error) {
    const failure = Core.parseFailureReport(error);
    renderReport(failure, null);
  } finally {
    elements.guided.textContent = "Run guided proof";
    setCommandState(false);
    guidedProofRunning = false;
  }
}

function exportReport() {
  if (!latestReport) return;
  const blob = new Blob([`${JSON.stringify(latestReport, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `prooflock_verification_${latestReport.receipt_id || "report"}.json`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

try {
  const visualRuntime = Lattice.initialize({
    canvas: elements.latticeCanvas,
    statusElement: elements.latticeStatus,
  });
  document.body.dataset.latticeMode = visualRuntime.mode;
} catch (error) {
  elements.latticeStatus.textContent = `Visual fallback unavailable: ${error instanceof Error ? error.message : String(error)}`;
}

elements.load.addEventListener("click", () => loadSample().catch((error) => {
  renderReport(Core.parseFailureReport(error), null);
}));
elements.verify.addEventListener("click", () => runVerification());
elements.guided.addEventListener("click", runGuidedProof);
elements.export.addEventListener("click", exportReport);
window.addEventListener("pagehide", () => Lattice.destroy(), { once: true });

loadSample().catch((error) => {
  renderReport(Core.parseFailureReport(error), null);
});
