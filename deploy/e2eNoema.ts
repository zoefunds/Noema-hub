import { createHash, randomBytes } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import type { GenLayerClient, TransactionHash } from "genlayer-js/types";
import { TransactionHashVariant, TransactionStatus } from "genlayer-js/types";

const SPONSOR = "0x7401c129edfc26e68fe19309fe461eb3db1058eb";
const RESEARCHER = "0x7452084e1cf767bf19c743051cff27d9f7a87a4d";
const E2E_PATH = path.resolve(process.cwd(), "deployments/e2e-studionet.json");

function stableJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.entries(value as Record<string, unknown>)
    .sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => `${JSON.stringify(key)}:${stableJson(item)}`).join(",")}}`;
  return JSON.stringify(value);
}

function normalize(value: any): any {
  if (value instanceof Map) return Object.fromEntries(Array.from(value.entries()).map(([key, item]) => [String(key), normalize(item)]));
  if (Array.isArray(value)) return value.map(normalize);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, normalize(item)]));
  return typeof value === "bigint" ? value.toString() : value;
}

function sha256(value: string): string { return createHash("sha256").update(value, "utf8").digest("hex"); }
function loadManifest(): any { return JSON.parse(readFileSync(path.resolve(process.cwd(), "deployments/studionet.json"), "utf8")); }
function loadRun(): any { return existsSync(E2E_PATH) ? JSON.parse(readFileSync(E2E_PATH, "utf8")) : {}; }
function saveRun(run: any): void { writeFileSync(E2E_PATH, JSON.stringify(run, null, 2) + "\n"); }

function assertSameAddress(actual: unknown, expected: string, label: string): void {
  if (String(actual ?? "").toLowerCase() !== expected.toLowerCase()) {
    throw new Error(`${label} mismatch: expected ${expected}, received ${String(actual ?? "")}`);
  }
}

async function write(client: GenLayerClient<any>, hub: `0x${string}`, functionName: string, args: unknown[], value = 0n): Promise<string> {
  const hash = await client.writeContract({ address: hub, functionName, args: args as any[], value });
  const receipt: any = await client.waitForTransactionReceipt({ hash: hash as TransactionHash,
    status: TransactionStatus.FINALIZED, retries: 240, interval: 5_000 });
  const status = String(receipt?.statusName ?? receipt?.status_name ?? "").toUpperCase();
  const execution = String(receipt?.txExecutionResultName ?? receipt?.tx_execution_result_name ?? "").toUpperCase();
  const leader = Array.isArray(receipt?.consensus_data?.leader_receipt)
    ? receipt.consensus_data.leader_receipt.find((item: any) => item?.mode === "leader") : undefined;
  const nestedSuccess = String(leader?.execution_result ?? "").toUpperCase() === "SUCCESS"
    && String(leader?.result?.status ?? "").toLowerCase() === "return";
  if (status !== "FINALIZED" || !(["FINISHED_WITH_RETURN", "FINISHEDWITHRETURN"].includes(execution) || nestedSuccess)) {
    throw new Error(`${functionName} failed: ${status || "UNKNOWN"} / ${execution || "UNKNOWN"} / ${JSON.stringify(receipt)}`);
  }
  return String(hash);
}

async function read(client: GenLayerClient<any>, hub: `0x${string}`, functionName: string, args: unknown[] = [], latest = true): Promise<any> {
  return normalize(await client.readContract({ address: hub, functionName, args: args as any[],
    transactionHashVariant: latest ? TransactionHashVariant.LATEST_NONFINAL : TransactionHashVariant.LATEST_FINAL }));
}

async function waitFor(client: GenLayerClient<any>, hub: `0x${string}`, dossierId: string,
  predicate: (dossier: any) => boolean, label: string): Promise<any> {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const dossier = await read(client, hub, "get_dossier", [dossierId]);
    if (predicate(dossier)) return dossier;
    await new Promise((resolve) => setTimeout(resolve, 15_000));
  }
  throw new Error(`Timed out waiting for ${label}`);
}

export default async function main(client: GenLayerClient<any>) {
  const phase = process.env.NOEMA_E2E_PHASE;
  if (!phase) return { skipped: true };
  const manifest = loadManifest();
  const hub = manifest.contracts.hub.address as `0x${string}`;
  const run = loadRun();

  if (phase === "sponsor") {
    if (run.refreshedDeploymentRun && run.refreshedDeploymentRun.verified !== true) {
      throw new Error(`An incomplete sponsor phase already exists for ${run.refreshedDeploymentRun.dossierId}; reconcile it before creating another dossier`);
    }
    const baselineUrl = "https://api.github.com/repos/openai/codex/git/trees/main";
    const baselineClaim = "The official openai/codex default-branch Git tree lists the root path LICENSE as a blob, but the tree metadata contains no license text.";
    const closesAt = BigInt(Math.floor(Date.now() / 1000) + 6 * 60 * 60);
    const txHash = await write(client, hub, "open_dossier", [
      "OpenAI Codex default-branch license declaration",
      "Does the official openai/codex default-branch root LICENSE file expressly declare Apache License 2.0?",
      "Choose Position A only when the root LICENSE file served from the official openai/codex default branch explicitly names Apache License Version 2.0. Choose Position B only when that official file explicitly names another license or explicitly states that no license applies. If the official document does not establish either condition, leave the dossier unresolved.",
      "Apache-2.0 declared",
      "Apache-2.0 not declared",
      "Accept only the official openai/codex default-branch tree metadata from api.github.com and document text from raw.githubusercontent.com/openai/codex/main. Exclude forks, mirrors, reposts, social media, search snippets, and third-party summaries.",
      JSON.stringify([{ url: baselineUrl, claim: baselineClaim }]),
      closesAt,
    ], 1_000_000_000_000_000n);
    const dossierId = await read(client, hub, "find_latest_dossier_by_sponsor", [SPONSOR]);
    const started = { ...run, product: "Noema", network: "studionet", startedAt: new Date().toISOString(), sponsor: SPONSOR,
      researcher: RESEARCHER, dossierId, sponsorTxHash: txHash, baseline: { url: baselineUrl, claim: baselineClaim } };
    saveRun(started);
    const dossier = await waitFor(client, hub, dossierId, (value) => value.status === "OPEN" || value.status === "CLOSED_REFUNDED", "baseline adjudication");
    saveRun({ ...started, dossierAfterBaseline: dossier });
    if (dossier.status !== "OPEN") throw new Error(`Baseline did not open: ${JSON.stringify(dossier)}`);
    return { dossierId, txHash, status: dossier.status };
  }

  if (phase === "research") {
    if (!run.dossierId) throw new Error("Run the sponsor phase first");
    assertSameAddress(await read(client, hub, "find_latest_dossier_by_sponsor", [SPONSOR]), run.dossierId, "Latest sponsor dossier");
    const initialDossier = await read(client, hub, "get_dossier", [run.dossierId]);
    if (initialDossier.status !== "OPEN") throw new Error(`Research phase requires an OPEN dossier, received ${initialDossier.status}`);
    const url = "https://raw.githubusercontent.com/openai/codex/main/LICENSE";
    const claim = "The root LICENSE file begins with Apache License Version 2.0, January 2004, and states the Apache License's terms, so it explicitly declares Apache License 2.0.";
    const salt = randomBytes(32).toString("hex");
    const packet = { domain: "NOEMA_DISCLOSURE_V1", chain_id: "61999", hub: hub.toLowerCase(), dossier_id: run.dossierId,
      researcher: RESEARCHER.toLowerCase(), url, claim, salt };
    const commitment = sha256(stableJson(packet));
    const dossier = await read(client, hub, "get_dossier", [run.dossierId]);
    const sealTxHash = await write(client, hub, "seal_disclosure", [run.dossierId, commitment], BigInt(dossier.bond_atto));
    const sealedSubmissionId = await read(client, hub, "get_submission_for_commitment", [commitment]);
    if (!sealedSubmissionId) throw new Error("Seal receipt finalized but authoritative commitment lookup returned no submission");
    const submissionId = sealedSubmissionId;
    Object.assign(run, { researchPhase: { startedAt: new Date().toISOString(), url, claim, commitment, salt,
      sealTxHash, submissionId, sealedAt: new Date().toISOString() } });
    saveRun(run);
    const discloseTxHash = await write(client, hub, "disclose", [submissionId, url, claim, salt]);
    Object.assign(run.researchPhase, { discloseTxHash, disclosedAt: new Date().toISOString() });
    saveRun(run);
    const resolved = await waitFor(client, hub, run.dossierId,
      (value) => ["RESOLVED", "CLOSED_REFUNDED"].includes(value.status), "candidate witnessing and final verdict");
    const submission = await read(client, hub, "get_submission", [submissionId]);
    const stats = await read(client, hub, "get_stats", []);
    const researcherCredit = await read(client, hub, "get_credit", [RESEARCHER]);
    const sponsorCredit = await read(client, hub, "get_credit", [SPONSOR]);
    if (resolved.status !== "RESOLVED" || resolved.winner.toLowerCase() !== RESEARCHER || submission.status !== "DECISIVE" || !stats.accounting_ok) {
      throw new Error(`Settlement invariants failed: ${JSON.stringify({ resolved, submission, stats })}`);
    }
    Object.assign(run, { completedAt: new Date().toISOString(), candidate: { url, claim, commitment, salt }, submissionId,
      sealTxHash, discloseTxHash, finalDossier: resolved, finalSubmission: submission, credits: { researcher: researcherCredit, sponsor: sponsorCredit }, stats });
    saveRun(run);
    return { dossierId: run.dossierId, submissionId, status: resolved.status, resolution: resolved.resolution,
      decisiveIds: resolved.decisive_ids, researcherCredit, accountingOk: stats.accounting_ok };
  }
  if (phase === "withdraw") {
    const latest = await read(client, hub, "find_latest_dossier_by_sponsor", [SPONSOR]);
    if (run.dossierId) assertSameAddress(latest, run.dossierId, "Latest sponsor dossier");
    const creditBefore = await read(client, hub, "get_credit", [RESEARCHER]);
    if (BigInt(creditBefore) === 0n) throw new Error("No researcher credit is available for withdrawal proof");
    const walletBefore = await client.getBalance({ address: RESEARCHER as `0x${string}` });
    const withdrawalTxHash = await write(client, hub, "withdraw", []);
    const childHashes: string[] = await (client as any).getTriggeredTransactionIds({ hash: withdrawalTxHash as TransactionHash });
    if (!Array.isArray(childHashes) || childHashes.length !== 1) {
      throw new Error(`Expected one external payout child, found ${JSON.stringify(childHashes)}`);
    }
    const childHash = childHashes[0];
    const childReceipt: any = await client.waitForTransactionReceipt({ hash: childHash as TransactionHash,
      status: TransactionStatus.FINALIZED, retries: 240, interval: 5_000 } as any);
    const childStatus = String(childReceipt?.statusName ?? childReceipt?.status_name ?? "").toUpperCase();
    const childRecipient = String(childReceipt?.to_address ?? childReceipt?.recipient ?? "").toLowerCase();
    const childValue = BigInt(childReceipt?.value ?? 0);
    if (childStatus !== "FINALIZED" || childReceipt?.value_credited !== true
      || childRecipient !== RESEARCHER || childValue !== BigInt(creditBefore)) {
      throw new Error(`External payout child did not prove successful delivery: ${JSON.stringify(normalize(childReceipt))}`);
    }
    const creditAfter = await read(client, hub, "get_credit", [RESEARCHER]);
    let walletAfter = await client.getBalance({ address: RESEARCHER as `0x${string}` });
    for (let attempt = 0; attempt < 60 && BigInt(walletAfter) <= BigInt(walletBefore); attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 5_000));
      walletAfter = await client.getBalance({ address: RESEARCHER as `0x${string}` });
    }
    const statsAfterWithdrawal = await read(client, hub, "get_stats", []);
    const withdrawalAttempt = { withdrawalTxHash, childTxHash: childHash, childStatus,
      childRecipient, childValue: childValue.toString(), valueCredited: childReceipt.value_credited,
      creditBefore, creditAfter,
      walletBefore: walletBefore.toString(), walletAfter: walletAfter.toString(),
      accountingOk: statsAfterWithdrawal.accounting_ok, completedAt: new Date().toISOString(),
      verifiedPayout: BigInt(creditAfter) === 0n && BigInt(walletAfter) === BigInt(walletBefore) + BigInt(creditBefore)
        && Boolean(statsAfterWithdrawal.accounting_ok) };
    Object.assign(run, { withdrawalAttempt });
    saveRun(run);
    if (BigInt(creditAfter) !== 0n || BigInt(walletAfter) !== BigInt(walletBefore) + BigInt(creditBefore) || !statsAfterWithdrawal.accounting_ok) {
      throw new Error(`Withdrawal invariants failed: ${JSON.stringify({ creditBefore, creditAfter,
        walletBefore: walletBefore.toString(), walletAfter: walletAfter.toString(), statsAfterWithdrawal })}`);
    }
    let duplicateRejected = false;
    try { await write(client, hub, "withdraw", []); } catch { duplicateRejected = true; }
    if (!duplicateRejected) throw new Error("Duplicate withdrawal unexpectedly succeeded");
    Object.assign(run, { withdrawal: { withdrawalTxHash, creditBefore, creditAfter,
      walletBefore: walletBefore.toString(), walletAfter: walletAfter.toString(), duplicateRejected,
      accountingOk: statsAfterWithdrawal.accounting_ok, completedAt: new Date().toISOString() } });
    saveRun(run);
    return run.withdrawal;
  }
  throw new Error(`Unknown NOEMA_E2E_PHASE: ${phase}`);
}
