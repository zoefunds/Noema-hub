import { existsSync, unlinkSync } from "node:fs";
import path from "node:path";

/**
 * GenLayer CLI treats every JavaScript file under deploy/ as a runnable script.
 * If a prior CLI run was interrupted, its generated .compiled.js can be picked
 * up on the next invocation before the TypeScript source. Remove only the two
 * known generated outputs so an old harness can never submit stale test terms.
 */
export default async function main() {
  const staleBundles = ["deployNoema.compiled.js", "e2eNoema.compiled.js"];
  const removed: string[] = [];
  for (const name of staleBundles) {
    const target = path.resolve(process.cwd(), "deploy", name);
    if (existsSync(target)) {
      unlinkSync(target);
      removed.push(name);
    }
  }
  return { removedStaleBundles: removed };
}
