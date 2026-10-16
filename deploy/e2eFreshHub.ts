import { createHash, randomBytes } from "node:crypto";
import { existsSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import path from "node:path";
import { createAccount, createClient, generatePrivateKey } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionHashVariant, TransactionStatus } from "genlayer-js/types";
import type { GenLayerClient, TransactionHash } from "genlayer-js/types";
import { selectSponsorKey, sweepableSponsorBalance } from "./sponsorKey.js";

const E2E_PATH = path.resolve(process.cwd(), "deployments/e2e-studionet.json");
const RPC_ENDPOINT = "https://studio.genlayer.com/api";
const SPONSOR_FUNDING = 3_000_000_000_000_000n;
const SPONSOR_REWARD = 1_000_000_000_000_000n;

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

function readJson(file: string): any { return JSON.parse(readFileSync(file, "utf8")); }
async function rawRpc(method: string, params: unknown[]): Promise<any> {
  const payload: any = await retryTransient(`StudioNet ${method}`, async () => {
    const response = await fetch(RPC_ENDPOINT, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }), signal: AbortSignal.timeout(20_000) });
    if (!response.ok) throw new Error(`StudioNet RPC HTTP ${response.status} for ${method}`);
    return response.json();
  });
  if (payload?.error) throw new Error(`StudioNet RPC ${method} failed: ${JSON.stringify(payload.error)}`);
  return payload?.result;
}
async function retryTransient<T>(label: string, operation: () => Promise<T>, attempts = 5): Promise<T> {
  for (let attempt = 0; ; attempt += 1) {
    try { return await operation(); } catch (error) {
      const message = String(error instanceof Error ? error.message : error).toLowerCase();
      const temporary = /(fetch failed|econnreset|unexpected token|not valid json|429|502|503|504|rate limit|temporarily unavailable|aborted|timeout)/.test(message);
      if (!temporary || attempt >= attempts) throw error;
      await new Promise((resolve) => setTimeout(resolve, Math.min(1_000 * 2 ** attempt, 10_000)));
      if (attempt === attempts - 1) console.warn(`${label} is still retrying after a transient StudioNet RPC failure.`);
    }
  }
}
function saveRun(update: Record<string, unknown>): void {
  const current = existsSync(E2E_PATH) ? readJson(E2E_PATH) : {};
  current.freshRedeploymentRun = { ...(current.freshRedeploymentRun ?? {}), ...update, updatedAt: new Date().toISOString() };
  writeFileSync(E2E_PATH, JSON.stringify(current, null, 2) + "\n");
}
function startRun(update: Record<string, unknown>): void {
  const current = existsSync(E2E_PATH) ? readJson(E2E_PATH) : {};
  if (current.freshRedeploymentRun) {
    current.freshRedeploymentHistory = [...(current.freshRedeploymentHistory ?? []), current.freshRedeploymentRun];
  }
  current.freshRedeploymentRun = { ...update, updatedAt: new Date().toISOString() };
  writeFileSync(E2E_PATH, JSON.stringify(current, null, 2) + "\n");
}
function assertSuccess(receipt: any, operation: string): void {
  const status = String(receipt?.statusName ?? receipt?.status_name ?? "").toUpperCase();
  const execution = String(receipt?.txExecutionResultName ?? receipt?.tx_execution_result_name ?? "").toUpperCase();
  const leader = Array.isArray(receipt?.consensus_data?.leader_receipt)
    ? receipt.consensus_data.leader_receipt.find((item: any) => item?.mode === "leader") : undefined;
  const nestedSuccess = String(leader?.execution_result ?? "").toUpperCase() === "SUCCESS"
    && String(leader?.result?.status ?? "").toLowerCase() === "return";
  if (status !== "FINALIZED" || !(execution === "FINISHED_WITH_RETURN" || execution === "FINISHEDWITHRETURN" || nestedSuccess)) {
    throw new Error(`${operation} failed: ${status || "UNKNOWN"} / ${execution || "UNKNOWN"}; receipt=${JSON.stringify(normalize(receipt))}`);
  }
}

async function write(client: GenLayerClient<any>, address: `0x${string}`, method: string, args: unknown[] = [], value = 0n,
  onSubmitted?: (hash: string) => void): Promise<string> {
  const hash = await client.writeContract({ address, functionName: method, args: args as any[], value });
  onSubmitted?.(String(hash));
  const receipt = await retryTransient(`${method} finality`, () => client.waitForTransactionReceipt({ hash: hash as TransactionHash,
    status: TransactionStatus.FINALIZED, retries: 240, interval: 5_000 } as any));
  assertSuccess(receipt, method);
  return String(hash);
}

async function read(client: GenLayerClient<any>, address: `0x${string}`, method: string, args: unknown[] = [], latest = true): Promise<any> {
  return normalize(await retryTransient(`${method} read`, () => client.readContract({ address, functionName: method, args: args as any[],
    transactionHashVariant: latest ? TransactionHashVariant.LATEST_NONFINAL : TransactionHashVariant.LATEST_FINAL } as any)));
}

async function waitForDossier(client: GenLayerClient<any>, hub: `0x${string}`, id: string,
  predicate: (dossier: any) => boolean, description: string): Promise<any> {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const dossier = await read(client, hub, "get_dossier", [id]);
    if (predicate(dossier)) return dossier;
    await new Promise((resolve) => setTimeout(resolve, 15_000));
  }
  throw new Error(`Timed out waiting for ${description}`);
}

async function waitForEvmReceipt(_client: GenLayerClient<any>, hash: string): Promise<any> {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const receipt = await rawRpc("eth_getTransactionReceipt", [hash]);
    if (receipt) {
      if (String(receipt.status).toLowerCase() !== "0x1") throw new Error(`Sponsor test funding reverted: ${hash}`);
      return normalize(receipt);
    }
    await new Promise((resolve) => setTimeout(resolve, 2_000));
  }
  throw new Error(`Timed out waiting for sponsor test funding transaction ${hash}`);
}

async function evmBalance(_client: GenLayerClient<any>, address: `0x${string}`): Promise<bigint> {
  const value = await rawRpc("eth_getBalance", [address, "latest"]);
  if (typeof value !== "string" || !/^0x[0-9a-f]+$/i.test(value)) throw new Error(`Invalid EVM balance for ${address}`);
  return BigInt(value);
}

async function waitForBalanceAtLeast(client: GenLayerClient<any>, address: `0x${string}`, minimum: bigint): Promise<bigint> {
  let balance = 0n;
  for (let attempt = 0; attempt < 60; attempt += 1) {
    balance = await evmBalance(client, address);
    if (balance >= minimum) return balance;
    await new Promise((resolve) => setTimeout(resolve, 2_000));
  }
  return balance;
}

async function sweepTemporarySponsor(sponsorClient: GenLayerClient<any>, researcher: `0x${string}`,
  maximumSweep?: bigint): Promise<any> {
  const wallet: any = sponsorClient;
  const sponsorAddress = wallet.account?.address;
  if (!sponsorAddress) return { attempted: false, reason: "temporary sponsor address unavailable" };
  const balance = await evmBalance(sponsorClient, sponsorAddress);
  const gasPriceRaw = await rawRpc("eth_gasPrice", []);
  const gasPrice = BigInt(String(gasPriceRaw));
  const gasReserve = gasPrice * 30_000n;
  const spendable = balance > gasReserve ? balance - gasReserve : 0n;
  const amount = maximumSweep === undefined || maximumSweep > spendable ? spendable : maximumSweep;
  if (amount <= 0n) return { attempted: false, balance: balance.toString(), gasReserve: gasReserve.toString() };
  const hash = await wallet.sendTransaction({ to: researcher, value: amount } as any);
  const receipt = await waitForEvmReceipt(sponsorClient, String(hash));
  return { attempted: true, hash: String(hash), amount: amount.toString(), receiptStatus: receipt.status };
}

export default async function main(researcherClient: GenLayerClient<any>) {
  if (process.env.NOEMA_E2E_FRESH !== "1") return { skipped: true };
  const manifest = readJson(path.resolve(process.cwd(), "deployments/studionet.json"));
  if (manifest.chainId !== 61999 || manifest.network !== "studionet") throw new Error("Fresh Hub E2E is locked to StudioNet 61999");
  const hub = manifest.contracts.hub.address as `0x${string}`;
  const researcher = (researcherClient as any).account?.address as `0x${string}` | undefined;
  if (!researcher || !/^0x[0-9a-f]{40}$/i.test(researcher)) throw new Error("Activate an unlocked EOA account before the fresh Hub E2E");
  const previous = existsSync(E2E_PATH) ? readJson(E2E_PATH).freshRedeploymentRun : undefined;
  const resuming = previous?.hub === hub && previous?.phase === "FAILED_OR_INTERRUPTED"
    && Boolean(previous?.dossierId && previous?.submissionId && previous?.sealTx && previous?.revealTx);
  if ((await read(researcherClient, hub, "list_dossiers", [0n, 1n])).length !== 0 && !resuming) {
    throw new Error("Fresh Hub E2E requires a clean Hub; refusing to replace or append to unknown test state");
  }

  const selection = selectSponsorKey(process.env.NOEMA_E2E_SPONSOR_PRIVATE_KEY, generatePrivateKey());
  let privateKey = selection.privateKey;
  let temporaryKeyFile: string | undefined = selection.persistUntilSweep
    ? path.join("/private/tmp", `noema-e2e-sponsor-${Date.now()}-${process.pid}.key`) : undefined;
  if (selection.persistUntilSweep && previous?.temporaryKeyFile && existsSync(previous.temporaryKeyFile) && previous.hub === hub) {
    const priorKey = readFileSync(previous.temporaryKeyFile, "utf8").trim() as `0x${string}`;
    const priorAccount = createAccount(priorKey);
    if (priorAccount.address.toLowerCase() === String(previous.sponsor).toLowerCase()) {
      privateKey = priorKey;
      temporaryKeyFile = previous.temporaryKeyFile;
    }
  }
  const sponsorAccount = createAccount(privateKey);
  if (sponsorAccount.address.toLowerCase() === researcher.toLowerCase()) {
    throw new Error("Fresh Hub E2E requires distinct sponsor and researcher accounts");
  }
  // A resumed run already has a finalized sponsor funding/open-dossier
  // transaction. Its original ephemeral sponsor key may have been safely
  // swept and deleted; no sponsor authority is needed to resume researcher
  // settlement, so do not require or recreate that signer.
  const sponsorClient = createClient({ chain: studionet, endpoint: manifest.rpc, account: sponsorAccount } as any);
  if (temporaryKeyFile && !existsSync(temporaryKeyFile)) {
    writeFileSync(temporaryKeyFile, privateKey, { mode: 0o600, flag: "wx" });
  }
  // Keep the one-time test key recoverable on disk until the funded account
  // has been swept or its balance is proven to be zero.
  startRun({ ...(resuming ? previous : {}), startedAt: new Date().toISOString(), hub, sponsor: sponsorAccount.address,
    researcher, sourceCommit: manifest.sourceCommit,
    sponsorKeyHandling: selection.handling,
    ...(temporaryKeyFile ? { temporaryKeyFile } : {}), phase: resuming ? "RESUMING" : "PREFLIGHT" });
  const initialResearcherBalance = await evmBalance(researcherClient, researcher);
  saveRun({ researcherWalletBeforeFunding: String(initialResearcherBalance), phase: resuming ? "RESUMING_EXISTING_DOSSIER" : "FUNDING_TEMPORARY_SPONSOR" });

  let sponsorFundingHash = previous?.sponsor === sponsorAccount.address ? String(previous.sponsorFundingHash ?? "") : "";
  let sponsorFundingAmount = 0n;
  let sponsorOpeningBalance: bigint | null = null;
  let completed: any = null;
  let sponsorSweep: any = null;
  try {
    let fundedSponsorBalance = 0n;
    if (!resuming) {
      fundedSponsorBalance = await evmBalance(researcherClient, sponsorAccount.address);
      sponsorOpeningBalance = fundedSponsorBalance;
      if (fundedSponsorBalance < SPONSOR_REWARD) {
        const fundingAmount = SPONSOR_FUNDING > fundedSponsorBalance ? SPONSOR_FUNDING - fundedSponsorBalance : 0n;
        sponsorFundingAmount = fundingAmount;
        sponsorFundingHash = String(await (researcherClient as any).sendTransaction({ to: sponsorAccount.address,
          value: fundingAmount } as any));
        const fundingReceipt = await waitForEvmReceipt(researcherClient, sponsorFundingHash);
        fundedSponsorBalance = await waitForBalanceAtLeast(researcherClient, sponsorAccount.address, SPONSOR_FUNDING);
        if (fundedSponsorBalance < SPONSOR_REWARD) throw new Error(`Temporary sponsor did not receive enough GEN: ${fundedSponsorBalance}`);
        saveRun({ sponsorFundingHash, sponsorFunding: { hash: sponsorFundingHash,
          amount: fundingAmount.toString(), receiptStatus: fundingReceipt.status } });
      } else {
        fundedSponsorBalance = await waitForBalanceAtLeast(researcherClient, sponsorAccount.address, SPONSOR_REWARD);
      }
      const fundingReceipt = sponsorFundingHash ? await waitForEvmReceipt(researcherClient, sponsorFundingHash) : null;
      saveRun({ phase: "SPONSOR_BASELINE", sponsorFunding: { hash: sponsorFundingHash,
        amount: sponsorFundingAmount.toString(), receiptStatus: fundingReceipt?.status ?? "NO_NEW_FUNDING_REQUIRED",
        sponsorBalanceAfter: String(fundedSponsorBalance), researcherBalanceBefore: String(initialResearcherBalance),
        researcherBalanceAfterFunding: String(await evmBalance(researcherClient, researcher)) } });
    } else {
      saveRun({ phase: "RESUMING_EXISTING_DOSSIER", sponsorFunding: { skipped: "dossier and sponsor funding are already finalized" } });
    }

    const baselineUrl = "https://api.github.com/repos/openai/codex/git/trees/main";
    const baselineClaim = "The official openai/codex default-branch Git tree lists the root path LICENSE as a blob, but the tree metadata contains no license text.";
    const closesAt = BigInt(Math.floor(Date.now() / 1000) + 6 * 60 * 60);
    let dossierId: string;
    let sponsorTx: string;
    let afterBaseline: any;
    if (resuming) {
      dossierId = String(previous.dossierId);
      sponsorTx = String(previous.sponsorTransaction);
      afterBaseline = await read(researcherClient, hub, "get_dossier", [dossierId]);
    } else {
      sponsorTx = await write(sponsorClient, hub, "open_dossier", [
        "OpenAI Codex default-branch license declaration",
        "Does the official openai/codex default-branch root LICENSE file expressly declare Apache License 2.0?",
        "Choose Position A only when the root LICENSE file served from the official openai/codex default branch explicitly names Apache License Version 2.0. Choose Position B only when that official file explicitly names another license or explicitly states that no license applies. If the official document does not establish either condition, leave the dossier unresolved.",
        "Apache-2.0 declared", "Apache-2.0 not declared",
        "Accept only the official openai/codex default-branch tree metadata from api.github.com and document text from raw.githubusercontent.com/openai/codex/main. Exclude forks, mirrors, reposts, social media, search snippets, and third-party summaries.",
        JSON.stringify([{ url: baselineUrl, claim: baselineClaim }]), closesAt,
      ], SPONSOR_REWARD);
      dossierId = await read(researcherClient, hub, "find_latest_dossier_by_sponsor", [sponsorAccount.address]);
      afterBaseline = await waitForDossier(researcherClient, hub, dossierId,
        (value) => value.status === "OPEN" || value.status === "CLOSED_REFUNDED", "baseline witnessing and adjudication");
    }
    saveRun({ phase: "RESEARCH", dossierId, sponsorTransaction: sponsorTx, baselineUrl, baselineClaim,
      dossierAfterBaseline: afterBaseline, sponsorBalanceAfterOpening: (await evmBalance(sponsorClient, sponsorAccount.address)).toString() });
    if (afterBaseline.status !== "OPEN" && !["RESOLVED", "CLOSED_REFUNDED"].includes(afterBaseline.status)) {
      throw new Error(`Dossier is not ready to continue the E2E: ${afterBaseline.status}`);
    }

    const url = "https://raw.githubusercontent.com/openai/codex/main/LICENSE";
    const claim = "The root LICENSE file begins with Apache License Version 2.0, January 2004, and states the Apache License's terms, so it explicitly declares Apache License 2.0.";
    const salt = resuming ? String(previous.salt) : randomBytes(32).toString("hex");
    const packet = { domain: "NOEMA_DISCLOSURE_V1", chain_id: "61999", hub: hub.toLowerCase(), dossier_id: dossierId,
      researcher: researcher.toLowerCase(), url, claim, salt };
    const commitment = createHash("sha256").update(stableJson(packet), "utf8").digest("hex");
    let sealTx: string;
    let submissionId: string;
    let revealTx: string;
    if (resuming) {
      sealTx = String(previous.sealTx);
      submissionId = String(previous.submissionId);
      revealTx = String(previous.revealTx);
      if (String(await read(researcherClient, hub, "get_submission_for_commitment", [commitment])) !== submissionId) {
        throw new Error("Resume state does not match the authoritative commitment lookup");
      }
    } else {
      const dossier = await read(researcherClient, hub, "get_dossier", [dossierId]);
      sealTx = await write(researcherClient, hub, "seal_disclosure", [dossierId, commitment], BigInt(dossier.bond_atto));
      submissionId = await read(researcherClient, hub, "get_submission_for_commitment", [commitment]);
      if (!submissionId) throw new Error("Sealed commitment was not returned by authoritative Hub readback");
      revealTx = await write(researcherClient, hub, "disclose", [submissionId, url, claim, salt]);
    }
    const dossier = await read(researcherClient, hub, "get_dossier", [dossierId]);
    saveRun({ phase: "SOURCE_WITNESS_AND_VERDICT", dossierId, researcher, url, claim, salt, commitment, submissionId,
      sealTx, revealTx, sealedSubmission: await read(researcherClient, hub, "get_submission", [submissionId]) });

    const observed = await read(researcherClient, hub, "get_dossier", [dossierId]);
    const resolved = ["RESOLVED", "CLOSED_REFUNDED"].includes(observed.status) ? observed : await waitForDossier(researcherClient, hub, dossierId,
      (value) => ["RESOLVED", "CLOSED_REFUNDED"].includes(value.status), "source witnessing and verdict settlement");
    const submission = await read(researcherClient, hub, "get_submission", [submissionId]);
    const currentCredit = await read(researcherClient, hub, "get_credit", [researcher]);
    const currentStats = await read(researcherClient, hub, "get_stats", []);
    const resumingPayout = Boolean(resuming && previous?.withdrawalTx && previous?.childHash);
    const creditBefore = resumingPayout ? String(previous.creditBeforeWithdrawal) : currentCredit;
    const statsBefore = resumingPayout ? (previous.statsBeforeWithdrawal ?? currentStats) : currentStats;
    if (resumingPayout) {
      const pending = await read(researcherClient, hub, "get_latest_withdrawal", [researcher]);
      const pendingAmount = pending?.amount === undefined ? -1n : BigInt(pending.amount);
      const outboundMatches = pending?.status === "PENDING"
        ? currentStats.pending_outbound === creditBefore
        : pending?.status === "DELIVERED" && currentStats.pending_outbound === "0";
      if (currentCredit !== "0" || !outboundMatches || pendingAmount !== BigInt(creditBefore)) {
        throw new Error(`Interrupted payout no longer matches authoritative withdrawal state: ${JSON.stringify({ currentCredit, currentStats, pending })}`);
      }
    }
    if (resolved.status !== "RESOLVED" || resolved.winner.toLowerCase() !== researcher.toLowerCase()
      || submission.status !== "DECISIVE" || !submission.verdict?.contribution_required
      || submission.verdict?.counterfactual_outcome !== "UNRESOLVED" || !statsBefore.accounting_ok
      || BigInt(creditBefore) !== SPONSOR_REWARD + BigInt(dossier.bond_atto)) {
      throw new Error(`Resolution/credit invariants failed: ${JSON.stringify({ resolved, submission, creditBefore, statsBefore })}`);
    }
    saveRun({ phase: "WITHDRAWAL", resolvedDossier: resolved, finalSubmission: submission,
      creditBeforeWithdrawal: creditBefore, statsBeforeWithdrawal: statsBefore,
      researcherWalletBeforeWithdrawal: String(await evmBalance(researcherClient, researcher)) });

    const walletBefore = resumingPayout
      ? BigInt(previous.walletBefore ?? previous.researcherWalletBeforeWithdrawal)
      : await evmBalance(researcherClient, researcher);
    // Resume hashes belong to this failed run only. A prior E2E can have the
    // same recipient, payout amount, and even a finalized child, but it must
    // never be mistaken for delivery from this Hub or dossier.
    let withdrawalTx = resuming ? String(previous?.withdrawalTx ?? "") : "";
    let childHash = resuming ? String(previous?.childHash ?? "") : "";
    if (!withdrawalTx && BigInt(creditBefore) > 0n) {
      withdrawalTx = await write(researcherClient, hub, "withdraw", []);
      saveRun({ withdrawalTx, phase: "WITHDRAWAL_PARENT_FINALIZED", walletBefore: String(walletBefore), creditBeforeWithdrawal: creditBefore });
      const childHashes: string[] = await (researcherClient as any).getTriggeredTransactionIds({ hash: withdrawalTx as TransactionHash });
      if (!Array.isArray(childHashes) || childHashes.length !== 1) throw new Error(`Expected one payout child; got ${JSON.stringify(childHashes)}`);
      childHash = childHashes[0];
      saveRun({ withdrawalTx, childHash, phase: "WITHDRAWAL_CHILD_PENDING", walletBefore: String(walletBefore), creditBeforeWithdrawal: creditBefore });
    } else if (!withdrawalTx) {
      throw new Error("Researcher credit is zero but no prior withdrawal transaction was recorded");
    }
    const child: any = await retryTransient("native payout child finality", () => researcherClient.waitForTransactionReceipt({ hash: childHash as TransactionHash,
      status: TransactionStatus.FINALIZED, retries: 240, interval: 5_000 } as any));
    const childStatus = String(child?.statusName ?? child?.status_name ?? "").toUpperCase();
    const execution = String(child?.txExecutionResultName ?? child?.tx_execution_result_name ?? "").toUpperCase();
    const recipient = String(child?.to_address ?? child?.recipient ?? "").toLowerCase();
    const value = BigInt(child?.value ?? 0);
    const valueCredited = child?.value_credited === true;
    if (childStatus !== "FINALIZED" || !valueCredited || recipient !== researcher.toLowerCase() || value !== BigInt(creditBefore)) {
      throw new Error(`Outgoing child did not prove exact successful delivery: ${JSON.stringify(normalize(child))}`);
    }
    const pendingWithdrawal = await read(researcherClient, hub, "get_latest_withdrawal", [researcher]);
    if (!pendingWithdrawal?.id || pendingWithdrawal.recipient.toLowerCase() !== researcher.toLowerCase()
      || BigInt(pendingWithdrawal.amount) !== BigInt(creditBefore)) {
      throw new Error(`Authoritative pending withdrawal does not match the emitted payment: ${JSON.stringify(pendingWithdrawal)}`);
    }
    let reconcileTx = resuming ? String(previous?.reconcileTx ?? "") : "";
    let reconciledWithdrawal = await read(researcherClient, hub, "get_withdrawal", [pendingWithdrawal.id]);
    if (reconciledWithdrawal.status === "PENDING") {
      reconcileTx = await write(researcherClient, hub, "reconcile_withdrawal", [pendingWithdrawal.id, withdrawalTx, childHash], 0n,
        (hash) => saveRun({ phase: "RECONCILE_PENDING", reconcileTx: hash, withdrawalId: pendingWithdrawal.id,
          withdrawalParent: withdrawalTx, withdrawalChild: childHash }));
      reconciledWithdrawal = await read(researcherClient, hub, "get_withdrawal", [pendingWithdrawal.id]);
    }
    if (reconciledWithdrawal.status !== "DELIVERED"
      || reconciledWithdrawal.parent_tx.toLowerCase() !== withdrawalTx.toLowerCase()
      || reconciledWithdrawal.child_tx.toLowerCase() !== childHash.toLowerCase()) {
      throw new Error(`Final payout reconciliation did not confirm exact delivery: ${JSON.stringify(reconciledWithdrawal)}`);
    }
    const creditAfter = await read(researcherClient, hub, "get_credit", [researcher]);
    let walletAfter = await evmBalance(researcherClient, researcher);
    for (let attempt = 0; attempt < 60 && BigInt(walletAfter) < BigInt(walletBefore) + BigInt(creditBefore); attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 2_000));
      walletAfter = await evmBalance(researcherClient, researcher);
    }
    const statsAfter = await read(researcherClient, hub, "get_stats", []);
    if (BigInt(creditAfter) !== 0n || BigInt(walletAfter) < BigInt(walletBefore) + BigInt(creditBefore) || !statsAfter.accounting_ok) {
      throw new Error("Withdrawal did not reconcile Hub credit, recipient balance, and accounting");
    }
    let duplicateRejected = false;
    try { await write(researcherClient, hub, "withdraw", []); } catch { duplicateRejected = true; }
    if (!duplicateRejected) throw new Error("Duplicate withdrawal unexpectedly executed successfully");

    completed = { phase: "COMPLETE", finishedAt: new Date().toISOString(), hub, sponsor: sponsorAccount.address,
      researcher, sponsorFundingHash, sponsorFundingAmount: sponsorFundingAmount.toString(), sponsorReward: SPONSOR_REWARD.toString(),
      dossierId, sponsorTx, baselineUrl, baselineClaim, afterBaseline, url, claim, commitment, submissionId, sealTx, revealTx,
      resolvedDossier: resolved, finalSubmission: submission, creditBeforeWithdrawal: creditBefore, creditAfterWithdrawal: creditAfter,
      withdrawalTx, childHash, childStatus, execution, recipient, value: value.toString(), valueCredited,
      withdrawalId: pendingWithdrawal.id, reconcileTx, reconciledWithdrawal,
      walletBefore: String(walletBefore), walletAfter: String(walletAfter), duplicateRejected,
      statsBeforeWithdrawal: statsBefore, statsAfterWithdrawal: statsAfter };
  } catch (error) {
    saveRun({ phase: "FAILED_OR_INTERRUPTED", error: error instanceof Error ? error.message : String(error), sponsorFundingHash });
    throw error;
  } finally {
    try {
      const balanceBeforeSweep = await evmBalance(sponsorClient, sponsorAccount.address);
      const maximumSweep = sponsorOpeningBalance === null ? (selection.persistUntilSweep ? undefined : 0n)
        : sweepableSponsorBalance(balanceBeforeSweep, sponsorOpeningBalance, !selection.persistUntilSweep);
      sponsorSweep = await sweepTemporarySponsor(sponsorClient, researcher, maximumSweep);
      const finalBalance = await evmBalance(sponsorClient, sponsorAccount.address);
      if (temporaryKeyFile && finalBalance === 0n && existsSync(temporaryKeyFile)) unlinkSync(temporaryKeyFile);
      saveRun({ ...(temporaryKeyFile ? { temporaryKeyFile } : {}),
        temporarySponsorBalanceAfterSweep: finalBalance.toString(), temporarySponsorSweep: sponsorSweep });
      if (finalBalance > 0n && temporaryKeyFile) {
        saveRun({ temporaryKeyFile, temporarySponsorBalanceNotZero: finalBalance.toString() });
      }
    } catch (error) {
      saveRun({ ...(temporaryKeyFile ? { temporaryKeyFile } : {}),
        temporarySponsorSweepError: error instanceof Error ? error.message : String(error) });
    }
  }
  const final = { ...completed, temporarySponsorSweep: sponsorSweep,
    ...(temporaryKeyFile ? { temporaryKeyFile: existsSync(temporaryKeyFile) ? temporaryKeyFile : "removed after sweep" }
      : { sponsorKeyHandling: "provided_ephemerally_not_persisted" }) };
  saveRun(final);
  return normalize(final);
}
