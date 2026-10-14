"use strict";

(function exposeProofLockCore(root, factory) {
  const api = factory(root);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.ProofLockCore = api;
}(typeof globalThis !== "undefined" ? globalThis : window, (root) => {
  const RECEIPT_SCHEMA = "lumencore.prooflock_receipt.v1";
  const RECEIPT_SCHEMA_V2 = "lumencore.prooflock_receipt.v2";
  const CANONICALIZATION_V1 = "lumencore.prooflock_c14n.legacy.v1";
  const CANONICALIZATION_V2 = "lumencore.prooflock_c14n.binary64.v2";
  const MAX_JSON_TEXT = 2000000;
  const MAX_DEPTH = 100;
  const REPORT_SCHEMA = "lumencore.prooflock_verification_report.v1";
  const ALLOWED_GATE_STATUSES = new Set(["PASS", "FAIL", "OPEN", "NOT_APPLICABLE"]);
  const ALLOWED_DECISIONS = new Set(["HOLD", "PROMOTE", "REJECT"]);
  const CANONICAL_REQUIRED_GATE_IDS = new Set([
    "artifact_hashes",
    "lineage_manifest",
    "baseline_contract",
    "held_out_evaluation",
    "independent_review",
    "human_release",
  ]);
  const VERIFIER_DERIVED_GATE_IDS = new Set(["artifact_hashes", "lineage_manifest"]);
  const SHA256_PATTERN = /^[0-9a-f]{64}$/;
  const SAFE_ARTIFACT_PATTERN = /^assets\/[A-Za-z0-9._/-]+$/;
  const SCHEME_PATTERN = /^[A-Za-z][A-Za-z0-9+.-]*:/;

  function asciiJsonString(value, profile) {
    const expression = profile === CANONICALIZATION_V2 ? /[^\x00-\x7e]/gu : /[^\x00-\x7f]/gu;
    return JSON.stringify(value).replace(expression, (character) => {
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

  function scalarString(value) {
    for (const character of value) {
      const code = character.codePointAt(0);
      if (code >= 0xd800 && code <= 0xdfff) throw new Error("unpaired Unicode surrogate is prohibited");
    }
    return value;
  }

  function compareUnicode(left, right) {
    const a = Array.from(left, (c) => c.codePointAt(0));
    const b = Array.from(right, (c) => c.codePointAt(0));
    for (let i = 0; i < Math.min(a.length, b.length); i++) if (a[i] !== b[i]) return a[i] - b[i];
    return a.length - b.length;
  }

  function serializationProfile(receipt) {
    const profile = receipt?.schema === RECEIPT_SCHEMA_V2 ? CANONICALIZATION_V2 : CANONICALIZATION_V1;
    if (receipt?.canonicalization !== undefined && receipt.canonicalization !== profile) throw new Error("unsupported canonicalization profile");
    if (receipt?.schema === RECEIPT_SCHEMA_V2 && receipt.canonicalization !== profile) throw new Error("v2 receipts require an explicit canonicalization profile");
    return profile;
  }

  function canonicalize(value, profile = serializationProfile(value)) {
    if (![CANONICALIZATION_V1, CANONICALIZATION_V2].includes(profile)) throw new Error("unsupported canonicalization profile");
    function encode(item, depth) {
      if (depth > MAX_DEPTH) throw new Error("canonical payload exceeds the nesting limit");
      if (item === null) return "null";
      if (typeof item === "boolean") return item ? "true" : "false";
      if (typeof item === "string") {
        scalarString(item);
        if (profile === CANONICALIZATION_V1 && item.includes("\x7f")) throw new Error("v1 does not support DEL characters; use an explicit v2 receipt");
        return asciiJsonString(item, profile);
      }
      if (typeof item === "number") {
        if (!Number.isFinite(item) || (Number.isInteger(item) && !Number.isSafeInteger(item))) throw new Error("nonfinite or unsafe integer number is prohibited");
        if (profile === CANONICALIZATION_V1) {
          if (!Number.isInteger(item) || Object.is(item, -0)) throw new Error("v1 supports safe integer numbers only; use an explicit v2 receipt");
          return String(item);
        }
        const view = new DataView(new ArrayBuffer(8));
        view.setFloat64(0, item === 0 ? 0 : item, false);
        return `N${Array.from(new Uint8Array(view.buffer), (b) => b.toString(16).padStart(2, "0")).join("")};`;
      }
      if (Array.isArray(item)) return `[${item.map((entry) => encode(entry, depth + 1)).join(",")}]`;
      if (item && typeof item === "object" && [Object.prototype, null].includes(Object.getPrototypeOf(item))) {
        const keys = Object.keys(item);
        for (const key of keys) {
          scalarString(key);
          if (profile === CANONICALIZATION_V1 && /[^\x00-\x7e]/u.test(key)) throw new Error("v1 requires ASCII object keys; use an explicit v2 receipt");
        }
        keys.sort(profile === CANONICALIZATION_V2 ? compareUnicode : undefined);
        return `{${keys.map((key) => `${asciiJsonString(key, profile)}:${encode(item[key], depth + 1)}`).join(",")}}`;
      }
      throw new Error("canonical payload must contain only JSON data types");
    }
    return encode(value, 0);
  }

  // Parse raw text before object construction so decoded duplicate keys and
  // unsafe integers cannot disappear through JSON.parse's last-wins/rounding.
  function parseStrictJson(text, options = {}) {
    if (typeof text !== "string" || text.length > MAX_JSON_TEXT || new TextEncoder().encode(text).length > MAX_JSON_TEXT) throw new Error("JSON input exceeds the text limit");
    let at = 0;
    const numericTokens = [];
    const whitespace = () => { while (/[\x20\t\r\n]/u.test(text[at] || "!") ) at++; };
    function string() {
      const start = at++;
      while (at < text.length) {
        const char = text[at++];
        if (char === '"') return scalarString(JSON.parse(text.slice(start, at)));
        if (char === "\\") at++;
      }
      throw new Error("unterminated JSON string");
    }
    function value(depth) {
      if (depth > MAX_DEPTH) throw new Error("JSON input exceeds the nesting limit");
      whitespace();
      if (text[at] === '"') return string();
      if (text[at] === "{") {
        at++; whitespace(); const object = Object.create(null), keys = new Set();
        if (text[at] === "}") { at++; return object; }
        while (at < text.length) {
          whitespace(); if (text[at] !== '"') throw new Error("expected a JSON object key");
          const key = string(); if (keys.has(key)) throw new Error(`duplicate decoded JSON key: ${key}`); keys.add(key);
          whitespace(); if (text[at++] !== ":") throw new Error("expected a JSON colon");
          object[key] = value(depth + 1); whitespace();
          const end = text[at++]; if (end === "}") return object; if (end !== ",") throw new Error("expected a JSON comma");
        }
        throw new Error("unterminated JSON object");
      }
      if (text[at] === "[") {
        at++; whitespace(); const array = [];
        if (text[at] === "]") { at++; return array; }
        while (at < text.length) { array.push(value(depth + 1)); whitespace(); const end = text[at++]; if (end === "]") return array; if (end !== ",") throw new Error("expected a JSON comma"); }
        throw new Error("unterminated JSON array");
      }
      for (const [literal, parsed] of [["true", true], ["false", false], ["null", null]]) if (text.startsWith(literal, at)) { at += literal.length; return parsed; }
      const token = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/u.exec(text.slice(at))?.[0];
      if (!token) throw new Error("invalid JSON value");
      at += token.length; const number = Number(token);
      if (!Number.isFinite(number) || (Number.isInteger(number) && !Number.isSafeInteger(number))) throw new Error("nonfinite or unsafe integer number is prohibited");
      numericTokens.push(token); return number;
    }
    const parsed = value(0); whitespace(); if (at !== text.length) throw new Error("unexpected trailing JSON content");
    const profile = options.profile || (parsed?.schema === RECEIPT_SCHEMA ? CANONICALIZATION_V1 : parsed?.schema === RECEIPT_SCHEMA_V2 ? CANONICALIZATION_V2 : null);
    if (profile === CANONICALIZATION_V1 && numericTokens.some((token) => !/^-?(?:0|[1-9][0-9]*)$/u.test(token) || token === "-0")) throw new Error("v1 raw JSON supports safe integer lexemes only; use an explicit v2 receipt");
    if (profile) canonicalize(parsed, profile);
    return parsed;
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
    const payload = Object.create(null);
    for (const key of Object.keys(receipt)) if (key !== "receipt_sha256") payload[key] = receipt[key];
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

  function deriveLineageStatus(receipt, manifestPayloads) {
    const current = manifestPayloads.get("current_protocol_manifest");
    const predecessor = manifestPayloads.get("predecessor_protocol_manifest");
    const lineageIsObject = Boolean(receipt.lineage && typeof receipt.lineage === "object" && !Array.isArray(receipt.lineage));
    const subjectIsObject = Boolean(receipt.subject && typeof receipt.subject === "object" && !Array.isArray(receipt.subject));
    const lineage = lineageIsObject ? receipt.lineage : {};
    const subject = subjectIsObject ? receipt.subject : {};
    const failures = [];

    if (!current) failures.push("current concept manifest is missing or invalid JSON");
    if (!predecessor) failures.push("predecessor concept manifest is missing or invalid JSON");
    if (!lineageIsObject) failures.push("receipt lineage must be an object");
    if (!subjectIsObject) failures.push("receipt subject must be an object");

    if (!failures.length) {
      const currentId = String(current.asset_id || "");
      const predecessorId = String(predecessor.asset_id || "");
      if (!currentId || currentId !== String(lineage.current_asset_id || "")) {
        failures.push("current manifest asset_id does not match receipt lineage");
      }
      if (!predecessorId || predecessorId !== String(lineage.predecessor_asset_id || "")) {
        failures.push("predecessor manifest asset_id does not match receipt lineage");
      }
      if (String(current.supersedes_asset_id || "") !== predecessorId) {
        failures.push("current manifest does not supersede the predecessor asset_id");
      }
      if (String(subject.asset_id || "") !== currentId) {
        failures.push("receipt subject does not match the current manifest asset_id");
      }
      const provenance = current.generation_provenance;
      if (!provenance || typeof provenance !== "object" || Array.isArray(provenance)
        || String(provenance.input_asset_id || "") !== predecessorId) {
        failures.push("current manifest provenance does not reference the predecessor asset_id");
      }
    }

    if (failures.length) return { status: "FAIL", basis: failures.join("; ") };
    return {
      status: "PASS",
      basis: "Verifier parsed both hash-matched manifests and confirmed the declared current, predecessor, supersession, subject, and generation-provenance identifiers.",
    };
  }

  async function verifyReceipt(receipt, options = {}) {
    const integrityErrors = [];
    const policyErrors = [];
    const warnings = [];
    const receiptIsObject = Boolean(receipt && typeof receipt === "object" && !Array.isArray(receipt));
    const safeReceipt = receiptIsObject ? receipt : {};
    if (!receiptIsObject) integrityErrors.push("receipt must be an object");
    if (![RECEIPT_SCHEMA, RECEIPT_SCHEMA_V2].includes(safeReceipt.schema)) integrityErrors.push("unsupported or missing receipt schema");
    if (!String(safeReceipt.claim_boundary || "").trim()) integrityErrors.push("claim_boundary is required");

    const expectedReceiptHash = String(safeReceipt.receipt_sha256 || "").toLowerCase();
    let computedReceiptHash = "", profile = "";
    try { profile = serializationProfile(safeReceipt); computedReceiptHash = await sha256Text(canonicalize(receiptPayload(safeReceipt), profile)); }
    catch (error) { integrityErrors.push(`unsupported canonical receipt payload: ${error instanceof Error ? error.message : String(error)}`); }
    const receiptHashMatches = Boolean(computedReceiptHash) && expectedReceiptHash === computedReceiptHash;
    if (!receiptHashMatches) integrityErrors.push("receipt_sha256 does not match the canonical receipt payload");

    const artifactRows = Array.isArray(safeReceipt.artifacts) ? safeReceipt.artifacts : [];
    if (!Array.isArray(safeReceipt.artifacts)) integrityErrors.push("artifacts must be an array");
    if (!artifactRows.length) integrityErrors.push("at least one artifact is required");
    const artifacts = [];
    const manifestPayloads = new Map();
    const seenArtifactIds = new Set();
    for (const [index, row] of artifactRows.entries()) {
      const rowIsObject = Boolean(row && typeof row === "object" && !Array.isArray(row));
      const safeRow = rowIsObject ? row : {};
      if (!rowIsObject) integrityErrors.push(`artifact row ${index} must be an object`);
      const result = makeArtifactResult(safeRow);
      if (!result.artifact_id || seenArtifactIds.has(result.artifact_id)) {
        integrityErrors.push(`missing or duplicate artifact_id: ${result.artifact_id || "<missing>"}`);
      }
      seenArtifactIds.add(result.artifact_id);
      if (!SHA256_PATTERN.test(result.expected_sha256)) {
        integrityErrors.push(`invalid expected_sha256: ${result.artifact_id || "<missing>"}`);
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
        if (result.hash_matches && ["current_protocol_manifest", "predecessor_protocol_manifest"].includes(result.role)) {
          try {
            const payload = parseStrictJson(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
            if (payload && typeof payload === "object" && !Array.isArray(payload)) {
              manifestPayloads.set(result.role, payload);
            }
          } catch (_error) {
            // Invalid manifest JSON is reflected by the verifier-derived lineage gate.
          }
        }
      } catch (error) {
        result.error = error instanceof Error ? error.message : String(error);
      }
      if (!result.hash_matches) integrityErrors.push(`${result.artifact_id || "artifact"}: ${result.error || "hash mismatch"}`);
      artifacts.push(result);
    }

    const artifactStatus = artifacts.length && artifacts.length === artifactRows.length
      && artifacts.every((row) => row.hash_matches) ? "PASS" : "FAIL";
    const lineageStatus = deriveLineageStatus(safeReceipt, manifestPayloads);
    const derivedGates = new Map([
      ["artifact_hashes", {
        status: artifactStatus,
        basis: `Verifier rehashed ${artifacts.filter((row) => row.hash_matches).length}/${artifacts.length} declared repository artifacts.`,
      }],
      ["lineage_manifest", lineageStatus],
    ]);

    const gates = Array.isArray(safeReceipt.gates) ? safeReceipt.gates : [];
    if (!Array.isArray(safeReceipt.gates)) integrityErrors.push("gates must be an array");
    if (!gates.length) integrityErrors.push("at least one gate is required");
    const gateCounts = Object.fromEntries(Array.from(ALLOWED_GATE_STATUSES, (status) => [status, 0]));
    const recordedGateCounts = Object.fromEntries(Array.from(ALLOWED_GATE_STATUSES, (status) => [status, 0]));
    const requiredOpenOrFailed = [];
    const seenGateIds = new Set();
    const gateReports = [];
    for (const [index, gate] of gates.entries()) {
      const gateIsObject = Boolean(gate && typeof gate === "object" && !Array.isArray(gate));
      const safeGate = gateIsObject ? gate : {};
      if (!gateIsObject) integrityErrors.push(`gate row ${index} must be an object`);
      const gateId = String(safeGate.gate_id || "");
      const recordedStatus = String(safeGate.status || "");
      const required = Boolean(safeGate.required_for_promotion);
      if (!gateId || seenGateIds.has(gateId)) integrityErrors.push(`missing or duplicate gate_id: ${gateId || "<missing>"}`);
      seenGateIds.add(gateId);
      if (CANONICAL_REQUIRED_GATE_IDS.has(gateId) && !required) {
        integrityErrors.push(`canonical gate must remain required for promotion: ${gateId}`);
      }

      let effectiveStatus;
      let authoritySource;
      let verificationBasis;
      if (!ALLOWED_GATE_STATUSES.has(recordedStatus)) {
        integrityErrors.push(`invalid gate status for ${gateId || "<missing>"}: ${recordedStatus}`);
        effectiveStatus = "FAIL";
        authoritySource = "INVALID_RECEIPT_DECLARATION";
        verificationBasis = "The recorded status is outside the receipt contract.";
      } else if (VERIFIER_DERIVED_GATE_IDS.has(gateId)) {
        recordedGateCounts[recordedStatus] += 1;
        const derived = derivedGates.get(gateId);
        effectiveStatus = derived.status;
        authoritySource = "VERIFIER_DERIVED";
        verificationBasis = derived.basis;
        if (recordedStatus !== effectiveStatus) {
          warnings.push(`recorded ${recordedStatus} for ${gateId} was replaced by verifier-derived ${effectiveStatus}`);
        }
      } else if (recordedStatus === "PASS") {
        recordedGateCounts[recordedStatus] += 1;
        effectiveStatus = "OPEN";
        authoritySource = "UNTRUSTED_RECEIPT_DECLARATION";
        verificationBasis = "Recorded PASS was not accepted because this gate requires evidence from a trusted external or human authority verifier.";
        if (required) {
          policyErrors.push(`required gate ${gateId || "<missing>"} has no verifier-supported authority; recorded PASS was not accepted`);
        }
      } else {
        recordedGateCounts[recordedStatus] += 1;
        effectiveStatus = recordedStatus;
        authoritySource = "RECORDED_HOLD_OR_FAILURE";
        verificationBasis = "A self-authored receipt may preserve a hold or failure, but it cannot mint a PASS for this authority gate.";
      }

      gateCounts[effectiveStatus] += 1;
      gateReports.push({
        gate_id: gateId,
        label: String(safeGate.label || ""),
        status: effectiveStatus,
        recorded_status: recordedStatus,
        effective_status: effectiveStatus,
        required_for_promotion: required,
        basis: String(safeGate.basis || ""),
        authority_source: authoritySource,
        verification_basis: verificationBasis,
      });
      if (required && effectiveStatus !== "PASS") requiredOpenOrFailed.push(gateId);
    }

    const missingCanonicalGates = Array.from(CANONICAL_REQUIRED_GATE_IDS)
      .filter((gateId) => !seenGateIds.has(gateId))
      .sort();
    if (missingCanonicalGates.length) {
      integrityErrors.push(`missing canonical required gates: ${missingCanonicalGates.join(", ")}`);
    }

    const decision = String(safeReceipt.decision || "").toUpperCase();
    if (!ALLOWED_DECISIONS.has(decision)) integrityErrors.push("decision must be HOLD, PROMOTE, or REJECT");
    if (decision === "PROMOTE" && requiredOpenOrFailed.length) {
      policyErrors.push("PROMOTE is prohibited while required effective gates are not PASS");
    }
    if (!Array.isArray(safeReceipt.limitations) || !safeReceipt.limitations.length) warnings.push("no limitations were recorded");

    const integrityValid = integrityErrors.length === 0;
    const policyValid = policyErrors.length === 0;
    const errors = [...integrityErrors, ...policyErrors];
    const verifiedUtc = typeof options.now === "function" ? options.now() : new Date().toISOString();
    return {
      schema: REPORT_SCHEMA,
      serialization_profile: profile,
      verified_utc: verifiedUtc,
      receipt_id: String(safeReceipt.receipt_id || ""),
      integrity_valid: integrityValid,
      policy_valid: policyValid,
      promotion_allowed:
        integrityValid && policyValid && requiredOpenOrFailed.length === 0 && decision === "PROMOTE",
      recorded_decision: decision,
      receipt_hash: {
        expected: expectedReceiptHash,
        computed: computedReceiptHash,
        matches: receiptHashMatches,
      },
      artifacts,
      artifact_count: artifacts.length,
      artifact_hash_match_count: artifacts.filter((row) => row.hash_matches).length,
      gates: gateReports,
      gate_counts: gateCounts,
      recorded_gate_counts: recordedGateCounts,
      required_open_or_failed_gates: requiredOpenOrFailed,
      integrity_errors: integrityErrors,
      policy_errors: policyErrors,
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
      policy_valid: false,
      promotion_allowed: false,
      recorded_decision: "INVALID",
      receipt_hash: { expected: "", computed: "", matches: false },
      artifacts: [],
      artifact_count: 0,
      artifact_hash_match_count: 0,
      gates: [],
      gate_counts: Object.fromEntries(Array.from(ALLOWED_GATE_STATUSES, (status) => [status, 0])),
      recorded_gate_counts: Object.fromEntries(Array.from(ALLOWED_GATE_STATUSES, (status) => [status, 0])),
      required_open_or_failed_gates: [],
      integrity_errors: [error instanceof Error ? error.message : String(error)],
      policy_errors: [],
      errors: [error instanceof Error ? error.message : String(error)],
      warnings: [],
      claim_boundary: "",
    };
  }

  return Object.freeze({
    RECEIPT_SCHEMA,
    RECEIPT_SCHEMA_V2,
    CANONICALIZATION_V1,
    CANONICALIZATION_V2,
    REPORT_SCHEMA,
    canonicalize,
    normalizeEditorText,
    normalizeArtifactPath,
    parseFailureReport,
    parseStrictJson,
    receiptPayload,
    resolveArtifactUrl,
    sha256Bytes,
    sha256Text,
    serializationProfile,
    verifyReceipt,
  });
}));
