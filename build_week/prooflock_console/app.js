"use strict";

const elements = {
  editor: document.querySelector("#receiptEditor"),
  load: document.querySelector("#loadSampleButton"),
  verify: document.querySelector("#verifyButton"),
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
};

let latestReport = null;

function canonicalize(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalize(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

async function sha256Bytes(bytes) {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function sha256Text(text) {
  return sha256Bytes(new TextEncoder().encode(text));
}

function safeArtifactUrl(path) {
  if (!path || path.includes("..") || path.includes(":") || path.startsWith("/")) {
    throw new Error(`Unsafe artifact path: ${path || "<missing>"}`);
  }
  if (!path.startsWith("assets/")) throw new Error(`Only public assets/ paths are allowed: ${path}`);
  return new URL(`../../${path}`, window.location.href);
}

function receiptPayload(receipt) {
  const payload = JSON.parse(JSON.stringify(receipt));
  delete payload.receipt_sha256;
  return payload;
}

async function verifyArtifact(artifact) {
  const result = {
    artifact_id: artifact.artifact_id || "",
    role: artifact.role || "",
    repo_relative_path: artifact.repo_relative_path || "",
    expected_sha256: String(artifact.expected_sha256 || "").toLowerCase(),
    observed_sha256: "",
    bytes: 0,
    hash_matches: false,
    error: "",
  };
  try {
    const response = await fetch(safeArtifactUrl(result.repo_relative_path), { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const bytes = await response.arrayBuffer();
    result.bytes = bytes.byteLength;
    result.observed_sha256 = await sha256Bytes(bytes);
    result.hash_matches = result.observed_sha256 === result.expected_sha256;
    if (!result.hash_matches) result.error = "Hash mismatch";
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }
  return result;
}

async function verifyReceipt(receipt) {
  const errors = [];
  if (receipt.schema !== "lumencore.prooflock_receipt.v1") errors.push("Unsupported or missing receipt schema");
  if (!String(receipt.claim_boundary || "").trim()) errors.push("claim_boundary is required");

  const computedReceiptHash = await sha256Text(canonicalize(receiptPayload(receipt)));
  const expectedReceiptHash = String(receipt.receipt_sha256 || "").toLowerCase();
  const receiptHashMatches = computedReceiptHash === expectedReceiptHash;
  if (!receiptHashMatches) errors.push("Receipt hash does not match canonical JSON");

  const artifacts = [];
  for (const artifact of Array.isArray(receipt.artifacts) ? receipt.artifacts : []) {
    const result = await verifyArtifact(artifact);
    if (!result.hash_matches) errors.push(`${result.artifact_id || "artifact"}: ${result.error || "hash mismatch"}`);
    artifacts.push(result);
  }
  if (!artifacts.length) errors.push("At least one artifact is required");

  const allowedStatuses = new Set(["PASS", "FAIL", "OPEN", "NOT_APPLICABLE"]);
  const gates = Array.isArray(receipt.gates) ? receipt.gates : [];
  const requiredOpenOrFailed = [];
  const seen = new Set();
  for (const gate of gates) {
    if (!gate.gate_id || seen.has(gate.gate_id)) errors.push(`Missing or duplicate gate_id: ${gate.gate_id || "<missing>"}`);
    seen.add(gate.gate_id);
    if (!allowedStatuses.has(gate.status)) errors.push(`Invalid gate status: ${gate.gate_id || "<missing>"}`);
    if (gate.required_for_promotion && gate.status !== "PASS") requiredOpenOrFailed.push(gate.gate_id);
  }
  if (!gates.length) errors.push("At least one gate is required");

  const decision = String(receipt.decision || "").toUpperCase();
  if (!new Set(["HOLD", "PROMOTE", "REJECT"]).has(decision)) errors.push("Decision must be HOLD, PROMOTE, or REJECT");
  if (decision === "PROMOTE" && requiredOpenOrFailed.length) errors.push("PROMOTE is blocked by required gates");

  return {
    schema: "lumencore.prooflock_verification_report.v1",
    verified_utc: new Date().toISOString(),
    receipt_id: receipt.receipt_id || "",
    integrity_valid: errors.length === 0,
    promotion_allowed: errors.length === 0 && requiredOpenOrFailed.length === 0,
    recorded_decision: decision,
    receipt_hash: { expected: expectedReceiptHash, computed: computedReceiptHash, matches: receiptHashMatches },
    artifacts,
    artifact_count: artifacts.length,
    artifact_hash_match_count: artifacts.filter((row) => row.hash_matches).length,
    gates,
    required_open_or_failed_gates: requiredOpenOrFailed,
    errors,
    claim_boundary: receipt.claim_boundary || "",
  };
}

function statusPill(status) {
  const normalized = String(status || "OPEN").toLowerCase();
  return `<span class="pill ${normalized === "pass" ? "pass" : normalized === "fail" ? "fail" : "open"}">${String(status || "OPEN")}</span>`;
}

function shortHash(hash) {
  return hash ? `${hash.slice(0, 14)}...${hash.slice(-10)}` : "not available";
}

function renderReport(report, receipt) {
  const matches = report.artifact_hash_match_count;
  const total = report.artifact_count;
  elements.identity.textContent = receipt.subject?.name || receipt.receipt_id || "Unnamed receipt";
  elements.integrity.textContent = report.integrity_valid ? "Verified" : "Failed";
  elements.artifacts.textContent = `${matches} / ${total}`;
  elements.gates.textContent = `${report.required_open_or_failed_gates.length} open`;
  elements.decision.textContent = report.recorded_decision || "Unknown";
  elements.receiptHash.textContent = `SHA-256 ${shortHash(report.receipt_hash.computed)}`;
  elements.boundary.textContent = report.claim_boundary || "No claim boundary recorded.";
  elements.artifactSummary.textContent = `${matches} of ${total} matched`;
  elements.gateSummary.textContent = report.promotion_allowed ? "Promotion gate clear" : "Promotion held";
  elements.verificationTime.textContent = new Date(report.verified_utc).toLocaleString();

  elements.headerStatusDot.className = `status-dot ${report.integrity_valid ? (report.promotion_allowed ? "pass" : "open") : "fail"}`;
  elements.headerStatus.textContent = report.integrity_valid ? (report.promotion_allowed ? "Verified and releasable" : "Verified, promotion held") : "Verification failed";

  elements.artifactRows.innerHTML = report.artifacts.map((row) => `
    <tr>
      <td data-label="Artifact"><strong>${escapeHtml(row.artifact_id)}</strong><br><code>${escapeHtml(row.repo_relative_path)}</code></td>
      <td data-label="Role">${escapeHtml(row.role)}</td>
      <td data-label="Observed SHA-256"><code>${escapeHtml(shortHash(row.observed_sha256))}</code></td>
      <td data-label="Status">${statusPill(row.hash_matches ? "PASS" : "FAIL")}</td>
    </tr>
  `).join("") || '<tr><td colspan="4" class="empty-cell">No artifacts declared</td></tr>';

  elements.gateGrid.innerHTML = report.gates.map((gate) => `
    <article class="gate-row">
      <header><h3>${escapeHtml(gate.label || gate.gate_id)}</h3>${statusPill(gate.status)}</header>
      <p>${escapeHtml(gate.basis || "No basis recorded.")}</p>
    </article>
  `).join("");

  const logLines = [
    `receipt ${report.receipt_hash.matches ? "PASS" : "FAIL"} ${report.receipt_hash.computed}`,
    `artifacts ${matches}/${total} matched`,
    `required gates open/failed ${report.required_open_or_failed_gates.length}`,
    `decision ${report.recorded_decision}`,
  ];
  for (const error of report.errors) logLines.push(`error ${error}`);
  elements.eventLog.textContent = logLines.join("\n");
  elements.export.disabled = false;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}

async function loadSample() {
  elements.eventLog.textContent = "Loading sample receipt...";
  const response = await fetch("sample_receipt.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`Unable to load sample receipt: HTTP ${response.status}`);
  const receipt = await response.json();
  elements.editor.value = JSON.stringify(receipt, null, 2);
  await runVerification();
}

async function runVerification() {
  elements.verify.disabled = true;
  elements.eventLog.textContent = "Verifying canonical receipt and repository artifacts...";
  try {
    const receipt = JSON.parse(elements.editor.value);
    latestReport = await verifyReceipt(receipt);
    renderReport(latestReport, receipt);
  } catch (error) {
    latestReport = null;
    elements.headerStatusDot.className = "status-dot fail";
    elements.headerStatus.textContent = "Verification failed";
    elements.integrity.textContent = "Failed";
    elements.eventLog.textContent = error instanceof Error ? error.message : String(error);
    elements.export.disabled = true;
  } finally {
    elements.verify.disabled = false;
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

elements.load.addEventListener("click", () => loadSample().catch((error) => { elements.eventLog.textContent = error.message; }));
elements.verify.addEventListener("click", runVerification);
elements.export.addEventListener("click", exportReport);
loadSample().catch((error) => { elements.eventLog.textContent = error.message; });
