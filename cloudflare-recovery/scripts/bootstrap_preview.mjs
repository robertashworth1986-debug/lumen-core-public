import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const APPROVAL_PHRASE = "BOOTSTRAP_CLOUDFLARE_RECOVERY_PREVIEW";
const approval = process.env.CLOUDFLARE_RECOVERY_BOOTSTRAP_APPROVAL;

if (approval !== APPROVAL_PHRASE) {
  console.error(
    "First upload is blocked. Set CLOUDFLARE_RECOVERY_BOOTSTRAP_APPROVAL=" +
      APPROVAL_PHRASE +
      " only after approving the one-time Cloudflare Worker bootstrap."
  );
  process.exit(2);
}

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const recoveryRoot = path.resolve(scriptDirectory, "..");
const wranglerBin = path.join(
  recoveryRoot,
  "node_modules",
  "wrangler",
  "bin",
  "wrangler.js"
);

const result = spawnSync(
  process.execPath,
  [
    wranglerBin,
    "deploy",
    "--message",
    "One-time bootstrap for exact governed LumenCore static recovery release 1ce7c359",
    "--strict"
  ],
  {
    cwd: recoveryRoot,
    env: process.env,
    stdio: "inherit"
  }
);

if (result.error) {
  throw result.error;
}
process.exit(result.status ?? 1);
