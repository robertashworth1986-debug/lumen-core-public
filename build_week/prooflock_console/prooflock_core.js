"use strict";

(function exposeProofLockCore(root, factory) {
  const api = factory(root);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.ProofLockCore = api;
}(typeof globalThis !== "undefined" ? globalThis : window, (root) => {
  const RECEIPT_SCHEMA = "lumencore.prooflock_receipt.v1";
  const REPORT_SCHEMA = "lumencore.prooflock_verification_report.v1";
  const ALLOWED_GATE_STATUSES = new Set(["PASS", "FAIL", "OPEN", "NOT_APPLICABLE"]);
  const ALLOWED_DECISIONS = new Set(["HOLD", "PROMOTE", "REJECT"]);
  const SHA256_PATTERN = /^[0-9a-f]{64}$/;
  const SAFE_ARTIFACT_PATTERN = /^assets\/[A-Za-z0-9._/-]+$/;
  const SCHEME_PATTERN = /^[A-Za-z][A-Za-z0-9+.-]*:/;

  function asciiJsonString(value) {
    return JSON.stringify(value).replace(/[^\x00-\x7f]/gu, (character) => {
      const codePoint = character.codePointAt(0);
      if (codePoint <= 0xffff) return `\\u${codePoint.toString(16).padStart(4, "0")}`;
      const adjusted = codePoint - 0x10000;
      const high = 0xd800 + (adjusted >> 10);
      const low = 0xdc00 + (adjusted & 0x3ff);
      return `\\u${high.toString(16)}\\u${low.toString(16)}`;
    });
  }

  function normalizeEditorText(value) {
    return String(value ?? "").replace(/\r\n?/gu, "\n");
  }

  function canonicalize(value) {
    if (Array.isArray(value)) return `[${value.map(canonicalize).join(",")}]`;
    if (value && typeof value === "object") {
      const entries = Object.keys(value)
        .sort()
        .map((key) => `${asciiJsonString(key)}:${canonicalize(value[key])}`);
      return `{${entries.join(",")}}`;
    }
    return asciiJsonString(value);
  }

  function toUint8Array(value) {
    if (value instanceof Uint8Array) return value;
    if (value instanceof ArrayBuffer) return new Uint8Array(value);
    if (ArrayBuffer.isView(value)) return new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
    throw new TypeError("Artifact loader must return bytes");
  }

  async function sha256Bytes(value) {
    const bytes = toUint8Array(value);
    if (!root.crypto?.subtle) throw new Error("Web Crypto SHA-256 is unavailable");
    const digest = await root.crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  async function sha256Text(text) {
    return sha256Bytes(new TextEncoder().encode(text));
  }

  function receiptPayload(receipt) {
    const payload = JSON.parse(JSON.stringify(receipt));
    delete payload.receipt_sha256;
    return payload;
  }

  function normalizeArtifactPath(input) {
    if (typeof input !== "string" || !input || input !== input.trim()) {
      throw new Error("artifact path is missing or malformed");
    }
    if (input.includes("\\") || input.includes("\0") || input.startsWith("/") || SCHEME_PATTERN.test(input)) {
      throw new Error(`unsafe artifact path: ${input}`);
    }
    let decoded;
    try {
      decoded = decodeURIComponent(input);
    } catch (_error) {
      throw new Error(`invalid encoded artifact path: ${input}`);
    }
    if (decoded !== input) throw new Error(`encoded artifact path is prohibited: ${input}`);
    const segments = input.split("/");
    if (segments.some((segment) => !segment || segment === "." || segment === "..")) {
      throw new Error(`artifact path traversal is prohibited: ${input}`);
    }
    if (!SAFE_ARTIFACT_PATTERN.test(input)) throw new Error(`only repository assets/ paths are allowed: ${input}`);
    return input;
  }

  function resolveArtifactUrl(input, pageUrl) {
    const normalized = normalizeArtifactPath(input);
    const page = new URL(pageUrl);
    const repositoryRoot = new URL("../../", page);
    const target = new URL(normalized, repositoryRoot);
    if (target.origin !== page.origin || !target.pathname.startsWith(`${repositoryRoot.pathname}assets/`)) {
      throw new Error(`artifact URL escaped the same-origin allowlist: ${input}`);
    }
    return target;
  }

  function makeArtifactResult(row) {
    return {
      artifact_id: String(row?.artifact_id || ""),
      role: String(row?.role || ""),
      repo_relative_path: String(row?.repo_relative_path || ""),
      expected_sha256: String(row?.expected_sha256 || "").toLowerCase(),
      observed_sha256: "",
      bytes: 0,
      exists: false,
      hash_matches: false,
      error: "",
    };
  }

  async function verifyReceipt(receipt, options = {}) {
    const errors = [];
    const warnings = [];
    const safeReceipt = receipt && typeof receipt === "object" && !Array.isArray(receipt) ? receipt : {};
    if (safeReceipt.schema !== RECEIPT_SCHEMA) errors.push("unsupported or missing receipt schema");
    if (!String(safeReceipt.claim_boundary || "").trim()) errors.push("claim_boundary is required");

    const expectedReceiptHash = String(safeReceipt.receipt_sha256 || "").toLowerCase();
    const computedReceiptHash = await sha256Text(canonicalize(receiptPayload(safeReceipt)));
    const receiptHashMatches = expectedReceiptHash === computedReceiptHash;
    if (!receiptHashMatches) errors.push("receipt_sha256 does not match the canonical receipt payload");

    const artifactRows = Array.isArray(safeReceipt.artifacts) ? safeReceipt.artifacts : [];
    if (!Array.isArray(safeReceipt.artifacts)) errors.push("artifacts must be an array");
    if (!artifactRows.length) errors.push("at least one artifact is required");
    const artifacts = [];
    const seenArtifactIds = new Set();
    for (const row of artifactRows) {
      const result = makeArtifactResult(row);
      if (!result.artifact_id || seenArtifactIds.has(result.artifact_id)) {
        errors.push(`missing or duplicate artifact_id: ${result.artifact_id || "<missing>"}`);
      }
      seenArtifactIds.add(result.artifact_id);
      if (!SHA256_PATTERN.test(result.expected_sha256)) {
        errors.push(`invalid expected_sha256: ${result.artifact_id || "<missing>"}`);
        result.error = "Invalid expected SHA-256";
        artifacts.push(result);
        continue;
      }
      try {
        result.repo_relative_path = normalizeArtifactPath(result.repo_relative_path);
        if (typeof options.loadArtifact !== "function") throw new Error("artifact loader is unavailable");
        const bytes = toUint8Array(await options.loadArtifact(result.repo_relative_path));
        result.exists = true;
        result.bytes = bytes.byteLength;
        result.observed_sha256 = await sha256Bytes(bytes);
        result.hash_matches = result.observed_sha256 === result.expected_sha256;
        if (!result.hash_matches) result.error = "Hash mismatch";
      } catch (error) {
        result.error = error instanceof Error ? error.message : String(error);
      }
      if (!result.hash_matches) errors.push(`${result.artifact_id || "artifact"}: ${result.error || "hash mismatch"}`);
      artifacts.push(result);
    }

    const gates = Array.isArray(safeReceipt.gates) ? safeReceipt.gates : [];
    if (!Array.isArray(safeReceipt.gates)) errors.push("gates must be an array");
    if (!gates.length) errors.push("at least one gate is required");
    const gateCounts = Object.fromEntries(Array.from(ALLOWED_GATE_STATUSES, (status) => [status, 0]));
    const requiredOpenOrFailed = [];
    const seenGateIds = new Set();
    for (const gate of gates) {
      const gateId = String(gate?.gate_id || "");
      const status = String(gate?.status || "");
      if (!gateId || seenGateIds.has(gateId)) errors.push(`missing or duplicate gate_id: ${gateId || "<missing>"}`);
      seenGateIds.add(gateId);
      if (!ALLOWED_GATE_STATUSES.has(status)) {
        errors.push(`invalid gate status for ${gateId || "<missing>"}: ${status}`);
      } else {
        gateCounts[status] += 1;
        if (gate?.required_for_promotion && status !== "PASS") requiredOpenOrFailed.push(gateId);
      }
    }

    const decision = String(safeReceipt.decision || "").toUpperCase();
    if (!ALLOWED_DECISIONS.has(decision)) errors.push("decision must be HOLD, PROMOTE, or REJECT");
    if (decision === "PROMOTE" && requiredOpenOrFailed.length) {
      errors.push("PROMOTE is prohibited while required gates are not PASS");
    }
    if (!Array.isArray(safeReceipt.limitations) || !safeReceipt.limitations.length) warnings.push("no limitations were recorded");

    const verifiedUtc = typeof options.now === "function" ? options.now() : new Date().toISOString();
    return {
      schema: REPORT_SCHEMA,
      verified_utc: verifiedUtc,
      receipt_id: String(safeReceipt.receipt_id || ""),
      integrity_valid: errors.length === 0,
      promotion_allowed:
        errors.length === 0 && requiredOpenOrFailed.length === 0 && decision === "PROMOTE",
      recorded_decision: decision,
      receipt_hash: {
        expected: expectedReceiptHash,
        computed: computedReceiptHash,
        matches: receiptHashMatches,
      },
      artifacts,
      artifact_count: artifacts.length,
      artifact_hash_match_count: artifacts.filter((row) => row.hash_matches).length,
      gates,
      gate_counts: gateCounts,
      required_open_or_failed_gates: requiredOpenOrFailed,
      errors,
      warnings,
      claim_boundary: String(safeReceipt.claim_boundary || ""),
    };
  }

  function parseFailureReport(error) {
    return {
      schema: REPORT_SCHEMA,
      verified_utc: new Date().toISOString(),
      receipt_id: "",
      integrity_valid: false,
      promotion_allowed: false,
      recorded_decision: "INVALID",
      receipt_hash: { expected: "", computed: "", matches: false },
      artifacts: [],
      artifact_count: 0,
      artifact_hash_match_count: 0,
      gates: [],
      gate_counts: Object.fromEntries(Array.from(ALLOWED_GATE_STATUSES, (status) => [status, 0])),
      required_open_or_failed_gates: [],
      errors: [error instanceof Error ? error.message : String(error)],
      warnings: [],
      claim_boundary: "",
    };
  }

  return Object.freeze({
    RECEIPT_SCHEMA,
    REPORT_SCHEMA,
    canonicalize,
    normalizeEditorText,
    normalizeArtifactPath,
    parseFailureReport,
    receiptPayload,
    resolveArtifactUrl,
    sha256Bytes,
    sha256Text,
    verifyReceipt,
  });
}));
