import fs from "node:fs/promises";
import path from "node:path";
import {
  FileBlob,
  PresentationFile,
} from "@oai/artifact-tool";

const ROOT = "C:\\LumaTrader\\INSTITUTIONAL_STACK_V2";
const WORKSPACE = path.join(ROOT, "tmp", "launchtn_deck_20260729");
const STARTER = path.join(WORKSPACE, "template-starter.pptx");
const FINAL = path.join(
  ROOT,
  "grant_submissions",
  "LAUNCHTN_3686_PITCH_2026",
  "LUMENCORE_3686_PITCH_DECK_2026-07-29_REVIEW_REQUIRED.pptx",
);
const QA_DIR = path.join(WORKSPACE, "final");
const FOOTER = "LUMENCORE | 3686 PITCH REVIEW COPY | 2026-07-29";

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

function rewrite(id, oldText, newText) {
  const target = presentation.resolve(id);
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

const footerIds = [
  "sh/vmdcj2xw",
  "sh/9o7ulg3y",
  "sh/a9kfadwn",
  "sh/ilwf69kv",
  "sh/zmlk3yhk",
  "sh/lg76d8zy",
  "sh/s3ml0v61",
  "sh/jq5w365o",
  "sh/rutwv65w",
  "sh/f2h8jitg",
  "sh/tsnip0ny",
];
for (const id of footerIds) {
  rewrite(
    id,
    "LUMENCORE | EVIDENCE-TO-PILOT BRIEF | 2026-07-29",
    FOOTER,
  );
}

rewrite(
  "sh/k3yl0zql",
  "Evidence-to-pilot infrastructure\nfor reviewable AI decisions",
  "Evidence-to-pilot infrastructure\nfor decisions buyers can review",
);
rewrite(
  "sh/7qp4be9c",
  "Turn a candidate method into a reproducible decision packet before any field or performance claim.",
  "Turn candidate methods into reproducible decision packets before field, savings, or performance claims.",
);
rewrite(
  "sh/ts7md4r2",
  "CURRENT REVIEW BUILD",
  "PITCH REVIEW COPY",
);
rewrite(
  "sh/fu94fe98",
  "INDEPENDENT VALIDATION NEXT",
  "$10K PRIZE PLAN GATED",
);
rewrite(
  "sh/utg3698n",
  "Robert Ashworth | Founder\nLumenCore | 2026",
  "Robert Ashworth | Founder\nLaunch Tennessee 3686 | 2026",
);

rewrite("sh/algfy50n", "FUNDING DISCIPLINE", "TEAM + PRIZE USE");
rewrite(
  "sh/xc3mho32",
  "Near-term funding should buy independent evidence",
  "A $10,000 prize would buy buyer-ready proof",
);
rewrite(
  "sh/kzu5c32t",
  "MILESTONE-ELIGIBLE USES",
  "FOUNDER + COMPANY",
);
rewrite("sh/725onyl4", "What funding unlocks", "What is established");
rewrite(
  "sh/d87uxg3m",
  "Outcome-independent evaluator",
  "Robert Ashworth | founder and systems architect",
);
rewrite(
  "sh/0bit8b2d",
  "Controlled-data integration",
  "Working software, custody, and frozen protocols",
);
rewrite(
  "sh/fapcz6ls",
  "Security, insurance, and compliance work",
  "Company and Tennessee eligibility require founder confirmation",
);
rewrite(
  "sh/xwnupgvy",
  "Buyer design sessions with written gates",
  "No customer, contract, revenue, or financing claim",
);
rewrite(
  "sh/wvetgbud",
  "Milestone: an independently reproducible receipt and a written paid-expansion decision.",
  "Upload remains blocked until legal entity, Tennessee eligibility, team, and company-stage facts are founder-confirmed.",
);
rewrite(
  "sh/lk7ut0va",
  "EXCLUDED WITHOUT APPROVAL",
  "PROPOSED $10K PRIZE USE",
);
rewrite(
  "sh/kjytkvup",
  "What this deck does not authorize",
  "What the prize would fund",
);
rewrite(
  "sh/1o3ahwvq",
  "Valuation, dilution, or financing terms",
  "Outcome-independent protocol reproduction",
);
rewrite(
  "sh/ru18r2to",
  "Unrestricted scale or marketing spend",
  "Buyer-controlled dataset integration",
);
rewrite(
  "sh/exsrmhsf",
  "Live trading or autonomous external action",
  "Security and compliance preparation",
);
rewrite(
  "sh/103qxcbq",
  "Patent, legal, or certification assertions",
  "Pilot acceptance-test and receipt package",
);
rewrite(
  "sh/u187adsv",
  "Amount, pricing, dilution, legal terms, and spend remain unapproved.",
  "Competition ask: $10,000 prize. No equity raise, valuation, financing term, or spend is authorized by this deck.",
);

rewrite("sh/xcryxg7y", "THE ASK", "THE 3686 ASK");
rewrite(
  "sh/wbih4b6d",
  "Help us earn the first\nindependent proof receipt.",
  "Help LumenCore earn its first\nindependent proof receipt.",
);
rewrite(
  "sh/n69grmpw",
  "LumenCore is ready for one named buyer, one accepted baseline, one controlled dataset, and one result an independent party can reproduce.",
  "The next milestone is not a louder claim. It is one named buyer, one accepted baseline, one controlled dataset, and one result a third party can reproduce.",
);
rewrite(
  "sh/98rytw72",
  "WHAT WE NEED FROM A DESIGN PARTNER",
  "WHAT WE ASK FROM 3686",
);
rewrite(
  "sh/72t03qp0",
  "Buyer introduction in energy, infrastructure, or agency work",
  "A fair hearing for the $10,000 pitch prize",
);
rewrite(
  "sh/9gza9sze",
  "Outcome-independent evaluator with a frozen protocol",
  "Buyer and design-partner introductions",
);
rewrite(
  "sh/0b6tc3yx",
  "Qualified prime or contracting route when relevant",
  "An outcome-independent evaluator",
);
rewrite(
  "sh/zaxs3yhc",
  "Scoped paid pilot after written acceptance gates",
  "Pilot-scope discipline after written gates",
);
rewrite(
  "sh/cn6t83y1",
  "Robert Ashworth | Founder, LumenCore",
  "Robert Ashworth | Founder, LumenCore",
);
rewrite(
  "sh/dofa18z6",
  "Current software and protocol evidence. External performance validation next.",
  "Current software and protocol evidence. No external performance claim.",
);

const launchTnNote = [
  "",
  "[LaunchTN 3686 review controls]",
  "- Local: grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_APPLICATION_MANIFEST_2026-07-29.json",
  "- Prize and deadline facts are bound to the current application manifest.",
  "- Legal entity, Tennessee eligibility, financing, upload, attestation, and submission remain founder-gated.",
].join("\n");

for (const slide of presentation.slides.items) {
  const existing = slide.speakerNotes.textFrame.text || "";
  if (!existing.includes("[LaunchTN 3686 review controls]")) {
    slide.speakerNotes.textFrame.setText(`${existing.trim()}${launchTnNote}`);
  }
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

for (const required of [
  "140 registered families; 35 implementations present",
  "126 direct comparisons across 23 candidate-source cards",
  "0 global Holm-positive comparisons",
  "0 promoted champions",
  "A $10,000 prize would buy buyer-ready proof",
  "Competition ask: $10,000 prize.",
  "No external performance claim.",
]) {
  if (!finalText.includes(required)) {
    throw new Error(`Required evidence or venue text missing: ${required}`);
  }
}

for (const blocked of [
  "world best",
  "guaranteed",
  "validated savings",
  "signed customer",
  "approved valuation",
]) {
  if (finalText.toLowerCase().includes(blocked)) {
    throw new Error(`Blocked unsupported text remains: ${blocked}`);
  }
}

await fs.mkdir(path.dirname(FINAL), { recursive: true });
const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(FINAL);

console.log(
  JSON.stringify(
    {
      schema: "lumencore.launchtn_3686_pitch_deck.v1",
      status: "CURRENT_FOUNDER_REVIEW_REQUIRED",
      external_release_authorized: false,
      slides: presentation.slides.items.length,
      output: FINAL,
      qa_dir: QA_DIR,
    },
    null,
    2,
  ),
);
