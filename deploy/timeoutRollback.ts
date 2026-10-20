import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import type { GenLayerClient, TransactionHash } from "genlayer-js/types";
import { TransactionHashVariant, TransactionStatus } from "genlayer-js/types";

const OUT = path.resolve(process.cwd(), "deployments/studionet-timeout-rollback.json");
const REWARD = 1_000_000_000_000_000n;

function normalize(value: any): any {
  if (value instanceof Map) return Object.fromEntries(Array.from(value.entries()).map(([key, item]) => [String(key), normalize(item)]));
  if (Array.isArray(value)) return value.map(normalize);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, normalize(item)]));
  return typeof value === "bigint" ? value.toString() : value;
}

function save(value: Record<string, unknown>): void {
  writeFileSync(OUT, JSON.stringify(normalize(value), null, 2) + "\n");
}

async function retryTransient<T>(label: string, operation: () => Promise<T>, attempts = 8): Promise<T> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      const message = String(error instanceof Error ? error.message : error).toLowerCase();
      const transient = /(fetch failed|econnreset|etimedout|429|502|503|504|rate limit|temporarily unavailable|aborted|timeout)/.test(message);
      if (!transient || attempt >= attempts) throw new Error(`${label}: ${String(error)}`);
      await new Promise((resolve) => setTimeout(resolve, Math.min(1_000 * 2 ** attempt, 15_000)));
    }
  }
}

function receiptSucceeded(receipt: any): boolean {
  const status = String(receipt?.statusName ?? receipt?.status_name ?? "").toUpperCase();
  const execution = String(receipt?.txExecutionResultName ?? receipt?.tx_execution_result_name ?? "").toUpperCase();
  const leader = Array.isArray(receipt?.consensus_data?.leader_receipt)
    ? receipt.consensus_data.leader_receipt.find((item: any) => item?.mode === "leader") : undefined;
  return status === "FINALIZED" && (["FINISHED_WITH_RETURN", "FINISHEDWITHRETURN"].includes(execution)
    || (String(leader?.execution_result ?? "").toUpperCase() === "SUCCESS"
      && String(leader?.result?.status ?? "").toLowerCase() === "return"));
}

async function write(client: GenLayerClient<any>, hub: `0x${string}`, method: string,
  args: unknown[], value = 0n): Promise<{ hash: string; receipt: any }> {
  const hash = await client.writeContract({ address: hub, functionName: method, args: args as any[], value });
  const receipt: any = await retryTransient(`${method} finality`, () => client.waitForTransactionReceipt({
    hash: hash as TransactionHash, status: TransactionStatus.FINALIZED, retries: 240, interval: 5_000 } as any));
  if (!receiptSucceeded(receipt)) throw new Error(`${method} failed: ${JSON.stringify(normalize(receipt))}`);
  return { hash: String(hash), receipt: normalize(receipt) };
}

async function read(client: GenLayerClient<any>, hub: `0x${string}`, method: string, args: unknown[] = []): Promise<any> {
  return normalize(await retryTransient(`${method} read`, () => client.readContract({
    address: hub, functionName: method, args: args as any[],
    transactionHashVariant: TransactionHashVariant.LATEST_NONFINAL } as any)));
}

export default async function main(client: GenLayerClient<any>) {
  if (process.env.NOEMA_TIMEOUT_E2E !== "1") return { skipped: true };
  const manifest = JSON.parse(readFileSync(path.resolve(process.cwd(), "deployments/studionet.json"), "utf8"));
  if (manifest.chainId !== 61999 || manifest.network !== "studionet") throw new Error("Timeout E2E is locked to StudioNet 61999");
  const hub = manifest.contracts.hub.address as `0x${string}`;
  const sponsor = (client as any).account?.address as `0x${string}` | undefined;
  if (!sponsor) throw new Error("An unlocked sponsor account is required");
  const baselineUrl = "https://httpbin.org/uuid";
  const prior = (() => {
    try { return JSON.parse(readFileSync(OUT, "utf8")); } catch { return null; }
  })();
  const resuming = prior?.phase === "AWAITING_REAL_STAGE_TIMEOUT" && prior?.hub === hub
    && String(prior?.sponsor).toLowerCase() === sponsor.toLowerCase();
  const beforeCredit = resuming ? prior.beforeCredit : await read(client, hub, "get_credit", [sponsor]);
  const startedAt = resuming ? prior.startedAt : new Date().toISOString();
  let opening: { hash: string; receipt?: any };
  let dossierId: string;
  let childIds: string[];
  if (resuming) {
    opening = { hash: prior.openDossierTx };
    dossierId = prior.dossierId;
    childIds = prior.asyncChildTransactionIds;
  } else {
    const closesAt = BigInt(Math.floor(Date.now() / 1000) + 2 * 60 * 60);
    opening = await write(client, hub, "open_dossier", [
      "StudioNet asynchronous timeout rollback",
      "Do independently fetched dynamic UUID responses establish one stable beacon value?",
      "Choose Position A only when every independently authenticated response contains the same UUID. Choose Position B only when every response explicitly contains a different fixed UUID. Conflicting or changing values are unresolved.",
      "One stable UUID", "A different fixed UUID",
      "Accept only a direct HTTPS response from httpbin.org/uuid. The response is intentionally dynamic for this timeout-consensus test; reject redirects, mirrors, and claimed publisher metadata.",
      JSON.stringify([{ url: baselineUrl, claim: "The direct response contains one UUID value." }]),
      closesAt,
    ], REWARD);
    dossierId = await read(client, hub, "find_latest_dossier_by_sponsor", [sponsor]);
    childIds = normalize(await retryTransient("triggered child lookup",
      () => (client as any).getTriggeredTransactionIds({ hash: opening.hash as TransactionHash })));
  }
  let dossier = await read(client, hub, "get_dossier", [dossierId]);
  save({ product: "Noema", network: "studionet", sourceCommit: manifest.sourceCommit, hub, sponsor,
    startedAt, phase: "AWAITING_REAL_STAGE_TIMEOUT", rewardAtto: REWARD, beforeCredit, baselineUrl,
    dossierId, openDossierTx: opening.hash, asyncChildTransactionIds: childIds, dossierBeforeTimeout: dossier });
  const deadline = Number(dossier.stage_deadline);
  if (!deadline || !String(dossier.pending_id).startsWith("baseline:")) {
    throw new Error(`Expected an asynchronous baseline stage, received ${JSON.stringify(dossier)}`);
  }
  while (Math.floor(Date.now() / 1000) <= deadline) {
    await new Promise((resolve) => setTimeout(resolve, 15_000));
    dossier = await read(client, hub, "get_dossier", [dossierId]);
    if (dossier.status !== "BASELINE_WITNESSING" || !String(dossier.pending_id).startsWith("baseline:")) {
      throw new Error(`Stage did not remain pending until timeout: ${JSON.stringify(dossier)}`);
    }
  }
  const expiration = await write(client, hub, "expire_stage", [dossierId]);
  const finalDossier = await read(client, hub, "get_dossier", [dossierId]);
  const afterCredit = await read(client, hub, "get_credit", [sponsor]);
  const stats = await read(client, hub, "get_stats", []);
  if (finalDossier.status !== "CLOSED_REFUNDED" || finalDossier.resolution !== "BASELINE_STAGE_TIMEOUT"
    || BigInt(afterCredit) - BigInt(beforeCredit) !== REWARD || finalDossier.reward_atto !== "0" || !stats.accounting_ok) {
    throw new Error(`Timeout rollback invariants failed: ${JSON.stringify({ finalDossier, beforeCredit, afterCredit, stats })}`);
  }
  const result = { product: "Noema", network: "studionet", sourceCommit: manifest.sourceCommit, hub, sponsor,
    startedAt, finishedAt: new Date().toISOString(), phase: "COMPLETE", rewardAtto: REWARD.toString(),
    baselineUrl, dossierId, openDossierTx: opening.hash, asyncChildTransactionIds: childIds,
    stageDeadline: String(deadline), dossierBeforeTimeout: dossier, expireStageTx: expiration.hash,
    finalDossier, beforeCredit, afterCredit, creditDelta: (BigInt(afterCredit) - BigInt(beforeCredit)).toString(), stats };
  save(result);
  return result;
}
