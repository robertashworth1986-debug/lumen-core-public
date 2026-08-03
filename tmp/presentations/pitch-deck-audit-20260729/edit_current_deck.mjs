import fs from "node:fs/promises";
import path from "node:path";
import {
  FileBlob,
  PresentationFile,
} from "@oai/artifact-tool";

const ROOT = "C:\\LumaTrader\\INSTITUTIONAL_STACK_V2";
const WORKSPACE = path.join(
  ROOT,
  "tmp",
  "presentations",
  "pitch-deck-audit-20260729",
);
const STARTER = path.join(WORKSPACE, "launchtn", "template-starter.pptx");
const FINAL = path.join(
  ROOT,
  "output",
  "pptx",
  "LumenCore_Evidence_to_Pilot_Deck_CURRENT_REVIEW_REQUIRED.pptx",
);
const QA_DIR = path.join(WORKSPACE, "launchtn", "final");

async function saveBlob(filePath, blob) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function recordsFrom(snapshot) {
  return String(snapshot.ndjson || "")
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

const presentation = await PresentationFile.importPptx(
  await FileBlob.load(STARTER),
);
const before = await presentation.inspect({
  kind: "slide,textbox,shape,image,notes",
  include:
    "id,slide,name,title,text,textPreview,textChars,textLines,bbox,bboxUnit,alt,fit,crop",
  maxChars: 1000000,
});
const records = recordsFrom(before);
const textboxes = records.filter(
  (record) => record.kind === "textbox" && typeof record.text === "string",
);
const images = records.filter((record) => record.kind === "image");

function exactTextbox(slide, oldText) {
  const matches = textboxes.filter(
    (record) => record.slide === slide && record.text === oldText,
  );
  if (matches.length !== 1) {
    throw new Error(
      `Expected one textbox on slide ${slide} with text ${JSON.stringify(oldText)}; found ${matches.length}.`,
    );
  }
  return matches[0];
}

function replaceExact(slide, oldText, newText) {
  if (oldText === newText) return;
  const record = exactTextbox(slide, oldText);
  const target = presentation.resolve(record.id);
  const oldLines = oldText.split("\n");
  const newLines = newText.split("\n");
  if (oldLines.length > 1 && oldLines.length === newLines.length) {
    for (let index = 0; index < oldLines.length; index += 1) {
      target.text.replace(oldLines[index], newLines[index]);
    }
    return;
  }
  target.text.replace(oldText, newText);
}

function replaceOrdered(slide, oldText, newTexts) {
  const matches = textboxes
    .filter((record) => record.slide === slide && record.text === oldText)
    .sort((left, right) => {
      const leftBox = left.bbox || [0, 0];
      const rightBox = right.bbox || [0, 0];
      return leftBox[1] - rightBox[1] || leftBox[0] - rightBox[0];
    });
  if (matches.length !== newTexts.length) {
    throw new Error(
      `Expected ${newTexts.length} occurrences of ${JSON.stringify(oldText)} on slide ${slide}; found ${matches.length}.`,
    );
  }
  for (let index = 0; index < matches.length; index += 1) {
    presentation.resolve(matches[index].id).text.replace(oldText, newTexts[index]);
  }
}

const footer = "LUMENCORE | EVIDENCE-TO-PILOT BRIEF | 2026-07-29";

const replacements = [
  [1, "Proof-to-pilot AI validation\nfor energy and infrastructure", "Evidence-to-pilot infrastructure\nfor reviewable AI decisions"],
  [1, "Turn a promising model into a decision a serious buyer can audit, reproduce, and price.", "Turn a candidate method into a reproducible decision packet before any field or performance claim."],
  [1, "WORKING MVP", "CURRENT REVIEW BUILD"],
  [1, "EXTERNAL VALIDATION NEXT", "INDEPENDENT VALIDATION NEXT"],
  [1, "Robert Ashworth | Founder\nLaunch Tennessee 3686 | 2026", "Robert Ashworth | Founder\nLumenCore | 2026"],
  [1, "Product proof room | local reviewer view", "Local proof room snapshot | 2026-07-29"],
  [1, "LUMENCORE | 3686 PITCH APPLICATION | 2026-07-17", footer],

  [2, "AI scores arrive faster than buyer trust", "Evidence fails before models do"],
  [2, "In high-consequence operations, the buyer is not purchasing a score. The buyer is purchasing a defensible decision.", "In high-consequence operations, a buyer is not purchasing a score. The buyer is purchasing a defensible decision."],
  [2, "A strong model can still fail procurement when the evidence trail cannot answer four basic questions.", "A strong result can still fail review when the evidence trail cannot answer four basic questions."],
  [2, "LUMENCORE | 3686 PITCH APPLICATION | 2026-07-17", footer],

  [3, "One bounded workflow from claim to pilot", "One bounded workflow from claim to decision"],
  [3, "LumenCore makes the evidence path explicit before it makes the claim louder.", "LumenCore makes the evidence path explicit before any claim is promoted."],
  [3, "HUMAN APPROVAL BEFORE EXTERNAL CLAIM", "HUMAN APPROVAL BEFORE EXTERNAL RELEASE"],
  [3, "Output: a buyer-readable packet that can be reproduced, challenged, and converted into a scoped field pilot.", "Output: a reviewer-readable packet that can be reproduced, challenged, and used to decide whether a scoped pilot is warranted."],
  [3, "LUMENCORE | 3686 PITCH APPLICATION | 2026-07-17", footer],

  [4, "Initial wedge: organizations with costly reliability, planning, or forecasting errors and an existing baseline they already trust.", "Target hypothesis: organizations with costly reliability, planning, or forecasting errors and an incumbent baseline they already trust."],
  [4, "Scoped pilot + economic acceptance gate", "Scoped pilot + accepted evidence gate"],
  [4, "LUMENCORE | 3686 PITCH APPLICATION | 2026-07-17", footer],

  [5, "The MVP is real; the next value gate is external", "Current evidence is measurable, including the negative result"],
  [5, "PROVEN IN CURRENT ARTIFACTS", "CURRENT SOURCE-NATIVE LEDGER"],
  [5, "Working review room", "Retrospective benchmark state"],
  [5, "Canonical review cards and evidence artifacts present", "140 registered families; 35 implementations present"],
  [5, "Claim gates separate outreach from field validation", "120 direct comparisons across 22 candidate-source cards"],
  [5, "Hashable packets and custody records are supported", "0 global Holm-positive comparisons"],
  [5, "Negative-result and abstention states remain visible", "0 promoted champions"],
  [5, "What this supports today: a bounded buyer conversation and a reproducible pilot design.", "Supports bounded software, custody, and protocol review. No alpha, superiority, savings, or field claim."],
  [5, "REQUIRES OUTSIDE EVIDENCE", "FROZEN PROSPECTIVE GATE"],
  [5, "Field validation", "Future-only validation"],
  [5, "Buyer-controlled data and accepted incumbent baseline", "Eight source-native baselines"],
  [5, "Independent reproduction by a named third party", "Sixteen one-sided Holm contrasts"],
  [5, "Measured operational or economic outcome", "520 future daily sessions or 60 monthly releases"],
  [5, "Reference customer, contract, or production deployment", "Zero eligible future observations today"],
  [5, "No claim in this deck crosses this boundary. The application asks for the introductions and discipline needed to cross it.", "Protocol LUMENCORE_TS_SOURCE_NATIVE_20260729_V1 is frozen and waiting for new source rows."],
  [5, "LUMENCORE | 3686 PITCH APPLICATION | 2026-07-17", footer],

  [6, "Sell the proof path before the platform", "Commercial path begins with an accepted evidence contract"],
  [6, "Three offers create a low-friction entry, a paid validation event, and a repeatable expansion path.", "Three offers create a bounded entry, a controlled validation event, and a post-pilot expansion path."],
  [6, "1. EVIDENCE REVIEW", "1. EVIDENCE REVIEW"],
  [6, "$5k-$10k", "SCOPED"],
  [6, "Scope the decision, lock the incumbent baseline, and produce a reviewer-ready evidence packet.", "Define the decision, lock the incumbent baseline, and produce a reviewer-ready evidence plan."],
  [6, "Buyer: Technical sponsor", "Buyer: Technical sponsor"],
  [6, "2. CONTROLLED PILOT", "2. CONTROLLED PILOT"],
  [6, "$20k-$50k", "GATED"],
  [6, "Replay on buyer-controlled data, measure against a preregistered acceptance gate, and issue a receipt.", "Replay buyer-controlled data against a written acceptance gate and issue an auditable receipt."],
  [6, "Buyer: Design partner", "Buyer: Design partner"],
  [6, "3. PLATFORM LICENSE", "3. PROGRAM LICENSE"],
  [6, "$60k-$150k / yr", "POST-PILOT"],
  [6, "Automate repeatable reviews, evidence custody, governance, support, and approved operating workflows.", "Automate repeatable reviews, evidence custody, governance, support, and approved workflows."],
  [6, "Buyer: Program owner", "Buyer: Program owner"],
  [6, "All pricing is a founder-review assumption. No paid pilot, customer commitment, or contract is claimed.", "No pricing, paid customer, savings, or contract is claimed. Scope and price require founder approval."],
  [6, "LUMENCORE | 3686 PITCH APPLICATION | 2026-07-17", footer],

  [7, "LUMENCORE | 3686 PITCH APPLICATION | 2026-07-17", footer],

  [8, "90-DAY FOCUS", "QUALIFICATION GATE"],
  [8, "10 qualified conversations  |  3 controlled-data design sessions  |  1 paid or independently reproduced pilot", "Named owner  |  accepted baseline  |  controlled dataset  |  written acceptance test"],
  [8, "LUMENCORE | 3686 PITCH APPLICATION | 2026-07-17", footer],

  [9, "EVIDENCE POSTURE", "PILOT CONTRACT"],
  [9, "The MVP is real; the next value gate is external", "A paid pilot is defined by acceptance, not a sales claim"],
  [9, "05", "09"],
  [9, "PROVEN IN CURRENT ARTIFACTS", "BUYER SUPPLIES"],
  [9, "Working review room", "Controlled problem"],
  [9, "Canonical review cards and evidence artifacts present", "Named decision owner and operating question"],
  [9, "Claim gates separate outreach from field validation", "Lawfully controlled data with allowed-use terms"],
  [9, "Hashable packets and custody records are supported", "Accepted incumbent baseline and metric"],
  [9, "Negative-result and abstention states remain visible", "Written cost-of-error and acceptance gate"],
  [9, "What this supports today: a bounded buyer conversation and a reproducible pilot design.", "Inputs define the decision contract before any pilot price, schedule, or outcome is represented."],
  [9, "REQUIRES OUTSIDE EVIDENCE", "LUMENCORE RETURNS"],
  [9, "Field validation", "Auditable receipt"],
  [9, "Buyer-controlled data and accepted incumbent baseline", "Frozen configuration and custody receipt"],
  [9, "Independent reproduction by a named third party", "Past-only replay against the accepted baseline"],
  [9, "Measured operational or economic outcome", "Favorable, neutral, negative, and invalid outcomes"],
  [9, "Reference customer, contract, or production deployment", "Human-owned next decision with no automatic release"],
  [9, "No claim in this deck crosses this boundary. The application asks for the introductions and discipline needed to cross it.", "No savings, ROI, or field-performance claim before a buyer-controlled result."],
  [9, "LUMENCORE | 3686 PITCH APPLICATION | 2026-07-17", footer],
  [9, "5/11", "9/11"],

  [10, "EVIDENCE POSTURE", "FUNDING DISCIPLINE"],
  [10, "The MVP is real; the next value gate is external", "Near-term funding should buy independent evidence"],
  [10, "05", "10"],
  [10, "PROVEN IN CURRENT ARTIFACTS", "MILESTONE-ELIGIBLE USES"],
  [10, "Working review room", "What funding unlocks"],
  [10, "Canonical review cards and evidence artifacts present", "Outcome-independent evaluator"],
  [10, "Claim gates separate outreach from field validation", "Controlled-data integration"],
  [10, "Hashable packets and custody records are supported", "Security, insurance, and compliance work"],
  [10, "Negative-result and abstention states remain visible", "Buyer design sessions with written gates"],
  [10, "What this supports today: a bounded buyer conversation and a reproducible pilot design.", "Milestone: an independently reproducible receipt and a written paid-expansion decision."],
  [10, "REQUIRES OUTSIDE EVIDENCE", "EXCLUDED WITHOUT APPROVAL"],
  [10, "Field validation", "What this deck does not authorize"],
  [10, "Buyer-controlled data and accepted incumbent baseline", "Valuation, dilution, or financing terms"],
  [10, "Independent reproduction by a named third party", "Unrestricted scale or marketing spend"],
  [10, "Measured operational or economic outcome", "Live trading or autonomous external action"],
  [10, "Reference customer, contract, or production deployment", "Patent, legal, or certification assertions"],
  [10, "No claim in this deck crosses this boundary. The application asks for the introductions and discipline needed to cross it.", "Amount, pricing, dilution, legal terms, and spend remain unapproved."],
  [10, "LUMENCORE | 3686 PITCH APPLICATION | 2026-07-17", footer],
  [10, "5/11", "10/11"],

  [11, "LumenCore is ready for the next disciplined step: one buyer, one accepted baseline, one controlled dataset, and one result that another party can reproduce.", "LumenCore is ready for one named buyer, one accepted baseline, one controlled dataset, and one result an independent party can reproduce."],
  [11, "WHAT WE NEED FROM LAUNCHTN", "WHAT WE NEED FROM A DESIGN PARTNER"],
  [11, "Buyer introductions in energy and infrastructure", "Buyer introduction in energy, infrastructure, or agency work"],
  [11, "Pricing and pilot-scope discipline", "Outcome-independent evaluator with a frozen protocol"],
  [11, "Pitch coaching grounded in evidence", "Qualified prime or contracting route when relevant"],
  [11, "3686 exposure to serious design partners", "Scoped paid pilot after written acceptance gates"],
  [11, "Working MVP. Honest boundaries. External validation next.", "Current software and protocol evidence. External performance validation next."],
  [11, "LUMENCORE | 3686 PITCH APPLICATION | 2026-07-17", footer],
];

for (const [slide, oldText, newText] of replacements) {
  replaceExact(slide, oldText, newText);
}

replaceOrdered(5, "Y", ["1", "2", "3", "4"]);
replaceOrdered(6, "Planning range", [
  "Price unquoted",
  "Buyer-defined gate",
  "After accepted receipt",
]);
replaceOrdered(9, "Y", ["1", "2", "3", "4"]);
replaceOrdered(9, "!", ["1", "2", "3", "4"]);
replaceOrdered(10, "Y", ["1", "2", "3", "4"]);
replaceOrdered(10, "!", ["1", "2", "3", "4"]);

const proofRoomImages = images.filter((record) => record.slide === 1);
if (proofRoomImages.length !== 1) {
  throw new Error(
    `Expected one proof-room image on slide 1; found ${proofRoomImages.length}.`,
  );
}
const proofRoomImage = presentation.resolve(proofRoomImages[0].id);
proofRoomImage.fit = "contain";
proofRoomImage.crop = { left: 0, top: 0, right: 0, bottom: 0 };
proofRoomImage.alt =
  "Dated local LumenCore proof-room screenshot; not external validation.";

const notes = [
  `[Sources]\n- Local: docs/LUMENCORE_SOURCE_NATIVE_BENCHMARK_WHITEPAPER_CURRENT.md\n- Local: config/prooflock_opportunity_ops_pilot_v1.json\n- Boundary: current software and protocol evidence; no external performance claim.`,
  `[Sources]\n- Local: config/federal_reviewer_objection_register_v1.json\n- Local: config/prooflock_opportunity_ops_pilot_v1.json\n- The trust-break framing is an internal operating hypothesis, not a market statistic.`,
  `[Sources]\n- Local: config/prooflock_opportunity_ops_pilot_v1.json\n- Local: out/ops/prooflock_opportunity_ops_pilot/latest/prooflock_opportunity_ops_pilot_definition.json`,
  `[Sources]\n- Local: config/prooflock_opportunity_ops_pilot_v1.json\n- Target sectors and buyer roles are positioning hypotheses; no customer adoption is claimed.`,
  `[Sources]\n- Local: out/ops/source_native_family_baseline_ledger_latest.json\n- Local: out/ops/market_signal_source_native_benchmark_latest.json\n- Local: config/time_series_source_native_prospective_protocol_v1.json\n- Local: out/ops/time_series_source_native_prospective_protocol_status.json`,
  `[Sources]\n- Local: config/prooflock_opportunity_ops_pilot_v1.json\n- Pricing is intentionally unquoted and requires buyer-specific founder approval.`,
  `[Sources]\n- Local: config/prooflock_opportunity_ops_pilot_v1.json\n- Competitive placement is a positioning hypothesis; no market share or superiority claim.`,
  `[Sources]\n- Local: config/prooflock_opportunity_ops_pilot_v1.json\n- Qualification gates are operating controls, not forecast conversion rates.`,
  `[Sources]\n- Local: config/prooflock_opportunity_ops_pilot_v1.json\n- Local: out/ops/prooflock_opportunity_ops_pilot/latest/prooflock_opportunity_ops_pilot_definition.json`,
  `[Sources]\n- Local: docs/LUMENCORE_SOURCE_NATIVE_BENCHMARK_WHITEPAPER_CURRENT.md\n- Local: config/prooflock_opportunity_ops_pilot_v1.json\n- No funding amount, valuation, dilution, or spend authorization is represented.`,
  `[Sources]\n- Local: docs/LUMENCORE_SOURCE_NATIVE_BENCHMARK_WHITEPAPER_CURRENT.md\n- Local: config/prooflock_opportunity_ops_pilot_v1.json\n- The ask is for a bounded validation relationship, not an external performance claim.`,
];

for (let index = 0; index < presentation.slides.items.length; index += 1) {
  const slide = presentation.slides.items[index];
  slide.speakerNotes.textFrame.setText(notes[index]);
  slide.speakerNotes.setVisible(true);
}

await fs.mkdir(QA_DIR, { recursive: true });
for (let index = 0; index < presentation.slides.items.length; index += 1) {
  const slide = presentation.slides.items[index];
  const stem = `final-slide-${String(index + 1).padStart(2, "0")}`;
  await saveBlob(
    path.join(QA_DIR, `${stem}.png`),
    await presentation.export({ slide, format: "png", scale: 1.5 }),
  );
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(
    path.join(QA_DIR, `${stem}.layout.json`),
    await layout.text(),
    "utf8",
  );
}

await saveBlob(
  path.join(QA_DIR, "final-montage.webp"),
  await presentation.export({ format: "webp", montage: true, scale: 1 }),
);

const after = await presentation.inspect({
  kind: "slide,textbox,shape,image,notes",
  include:
    "id,slide,name,title,text,textPreview,textChars,textLines,bbox,bboxUnit,alt,fit,crop",
  maxChars: 1000000,
});
await fs.writeFile(
  path.join(QA_DIR, "final-inspect.ndjson"),
  after.ndjson || "",
  "utf8",
);

const finalText = recordsFrom(after)
  .filter((record) => record.kind === "textbox")
  .map((record) => record.text || "")
  .join("\n");
for (const banned of [
  "$250k",
  "$65k",
  "~75%",
  "$5k-$10k",
  "$20k-$50k",
  "$60k-$150k / yr",
  "Modeled positive EBITDA",
  "Launch Tennessee",
  "3686",
]) {
  if (finalText.includes(banned)) {
    throw new Error(`Blocked stale or unapproved deck text remains: ${banned}`);
  }
}
for (const required of [
  "140 registered families; 35 implementations present",
  "120 direct comparisons across 22 candidate-source cards",
  "0 promoted champions",
  "Zero eligible future observations today",
]) {
  if (!finalText.includes(required)) {
    throw new Error(`Required evidence text missing: ${required}`);
  }
}

await fs.mkdir(path.dirname(FINAL), { recursive: true });
const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(FINAL);

console.log(
  JSON.stringify(
    {
      schema: "lumencore.current_evidence_to_pilot_deck.v1",
      status: "CURRENT_HUMAN_REVIEW_REQUIRED",
      external_release_authorized: false,
      slides: presentation.slides.items.length,
      output: FINAL,
      qa_dir: QA_DIR,
    },
    null,
    2,
  ),
);
