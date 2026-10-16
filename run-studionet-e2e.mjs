import { existsSync, unlinkSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const generatedBundles = [
  "00_cleanup.compiled.js",
  "deployNoema.compiled.js",
  "e2eNoema.compiled.js",
  "e2eFreshHub.compiled.js",
];

for (const name of generatedBundles) {
  const bundle = path.join(root, "deploy", name);
  if (existsSync(bundle)) unlinkSync(bundle);
}

const revision = spawnSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" });
if (revision.error) throw revision.error;
if (revision.status !== 0 || !revision.stdout.trim()) throw new Error("Unable to resolve the exact source commit for the deployment manifest");

const result = spawnSync("genlayer", ["deploy"], {
  cwd: root,
  env: { ...process.env, NOEMA_E2E_FRESH: "1", NOEMA_SOURCE_COMMIT: process.env.NOEMA_SOURCE_COMMIT || revision.stdout.trim() },
  stdio: "inherit",
});
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
