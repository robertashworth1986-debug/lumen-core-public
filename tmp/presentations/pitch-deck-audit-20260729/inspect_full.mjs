import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const [sourcePptx, outputPath] = process.argv.slice(2);
if (!sourcePptx || !outputPath) {
  throw new Error("Usage: node inspect_full.mjs <source.pptx> <output.ndjson>");
}

const presentation = await PresentationFile.importPptx(
  await FileBlob.load(sourcePptx),
);
const snapshot = await presentation.inspect({
  kind: "slide,textbox,shape,image,table,chart,notes,layout",
  include:
    "id,slide,name,title,text,textPreview,textChars,textLines,bbox,bboxUnit," +
    "isPlaceholder,placeholders,chartType,rows,cols,preview",
  maxChars: 1000000,
});

await fs.writeFile(outputPath, snapshot.ndjson || "", "utf8");
