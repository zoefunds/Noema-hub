import { existsSync, unlinkSync } from "node:fs";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
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

const ephemeralKey = process.env.NOEMA_E2E_DEPLOYER_PRIVATE_KEY;
delete process.env.NOEMA_E2E_DEPLOYER_PRIVATE_KEY;
if (ephemeralKey) {
  if (!/^0x[0-9a-fA-F]{64}$/.test(ephemeralKey)) throw new Error("The ephemeral deployer key must be a 32-byte 0x-prefixed value");
  const [{ createAccount, createClient }, { studionet }] = await Promise.all([
    import("genlayer-js"), import("genlayer-js/chains"),
  ]);
  const account = createAccount(ephemeralKey);
  const client = createClient({ chain: studionet, endpoint: "https://studio.genlayer.com/api", account });
  const balance = await client.getBalance({ address: account.address });
  if (balance < 5_000_000_000_000_000n) {
    throw new Error(`Ephemeral signer ${account.address} has insufficient GEN for deployment and the funded E2E (balance ${balance} atto).`);
  }
  delete process.env.NOEMA_SOURCE_COMMIT;
  process.env.NOEMA_SOURCE_COMMIT = revision.stdout.trim();
  console.log(`Running with ephemeral StudioNet signer ${account.address}; private key remains process-memory only.`);
  if (process.env.NOEMA_E2E_SKIP_DEPLOY === "1") {
    const manifest = JSON.parse(readFileSync(path.join(root, "deployments/studionet.json"), "utf8"));
    if (manifest.network !== "studionet" || manifest.chainId !== 61999) throw new Error("E2E retry is locked to the deployed StudioNet manifest");
    for (const [name, file] of [["hub", "contracts/noema_hub.py"], ["witness", "contracts/source_witness.py"], ["engine", "contracts/verdict_engine.py"]]) {
      const localHash = createHash("sha256").update(readFileSync(path.join(root, file))).digest("hex");
      if (manifest.contracts?.[name]?.sourceSha256 !== localHash || manifest.contracts?.[name]?.deployedSourceMatchesLocal !== true) {
        throw new Error(`Refusing E2E retry: the deployed ${name} source does not match the local contract source.`);
      }
    }
    console.log("Reusing the verified deployment; contract source hashes match the local Hub, Witness, and Engine.");
  } else {
    const { default: deploy } = await import("./deploy/deployNoema.ts");
    await deploy(client);
  }
  process.env.NOEMA_E2E_FRESH = "1";
  const { default: freshE2E } = await import("./deploy/e2eFreshHub.ts");
  const result = await freshE2E(client);
  console.log(JSON.stringify(result, null, 2));
  process.exit(0);
}

const result = spawnSync("genlayer", ["deploy"], {
  cwd: root,
  env: { ...process.env, NOEMA_E2E_FRESH: "1", NOEMA_SOURCE_COMMIT: process.env.NOEMA_SOURCE_COMMIT || revision.stdout.trim() },
  stdio: "inherit",
});
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
