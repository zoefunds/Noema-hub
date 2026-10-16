"use client";

import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionHashVariant } from "genlayer-js/types";
import { sha256, stringToHex } from "viem";
import type { Dossier, PendingDisclosure, PendingPayout } from "./types";

export const CHAIN_ID = 61999;
export const CHAIN_HEX = `0x${CHAIN_ID.toString(16)}`;
export const RPC_URL = process.env.NEXT_PUBLIC_GENLAYER_RPC_URL || "https://studio.genlayer.com/api";
export const EXPLORER_URL = process.env.NEXT_PUBLIC_GENLAYER_EXPLORER || "https://explorer-studio.genlayer.com";
export const HUB_ADDRESS = process.env.NEXT_PUBLIC_NOEMA_HUB_ADDRESS || "";
export const NATIVE_PAYOUTS_ENABLED = process.env.NEXT_PUBLIC_NATIVE_PAYOUTS_ENABLED === "true";
const storageKey = "noema:pending-disclosures:v1";
const payoutStorageKey = "noema:pending-payouts:v1";
const rpcTimes: number[] = [];
const readCache = new Map<string, { expires: number; value: unknown }>();

export type Eip1193Provider = { request: (args: { method: string; params?: unknown[] | Record<string, unknown> }) => Promise<unknown> };
function provider(): Eip1193Provider | null { return typeof window === "undefined" ? null : (window as any).ethereum || null; }
function assertHub(): `0x${string}` {
  if (!/^0x[0-9a-fA-F]{40}$/.test(HUB_ADDRESS)) throw new Error("Noema Hub is not configured for this deployment.");
  return HUB_ADDRESS as `0x${string}`;
}
async function reserveRpc(): Promise<void> {
  while (true) { const now = Date.now(); while (rpcTimes.length && now - rpcTimes[0] >= 60_000) rpcTimes.shift();
    if (rpcTimes.length < 24) { rpcTimes.push(now); return; }
    await new Promise((resolve) => setTimeout(resolve, Math.max(500, 60_050 - (now - rpcTimes[0])))); }
}
async function withRpc<T>(work: () => Promise<T>): Promise<T> {
  let wait = 1200;
  for (let attempt = 0; ; attempt += 1) { await reserveRpc(); try { return await work(); } catch (error) {
    const message = String(error instanceof Error ? error.message : error).toLowerCase();
    if (attempt >= 3 || !/(429|rate limit|too many|fetch failed)/.test(message)) throw error;
    await new Promise((resolve) => setTimeout(resolve, wait)); wait *= 2; } }
}
function normalize(value: unknown): any {
  if (value instanceof Map) return Object.fromEntries(Array.from(value.entries()).map(([key, item]) => [String(key), normalize(item)]));
  if (Array.isArray(value)) return value.map(normalize);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, normalize(item)]));
  return typeof value === "bigint" ? value.toString() : value;
}
function readClient() { return createClient({ chain: studionet, endpoint: RPC_URL } as any); }
async function read<T>(functionName: string, args: unknown[] = [], latest = false): Promise<T> {
  const key = JSON.stringify([functionName, args.map((item) => typeof item === "bigint" ? item.toString() : item), latest]);
  const cached = readCache.get(key); if (cached && cached.expires > Date.now()) return cached.value as T;
  const value = normalize(await withRpc(() => readClient().readContract({ address: assertHub(), functionName, args,
    transactionHashVariant: latest ? TransactionHashVariant.LATEST_NONFINAL : TransactionHashVariant.LATEST_FINAL } as any)));
  readCache.set(key, { value, expires: Date.now() + (latest ? 2_000 : 8_000) }); return value as T;
}

export async function listDossiers(offset = 0, limit = 24): Promise<Dossier[]> { return read("list_dossiers", [BigInt(offset), BigInt(limit)]); }
export async function getDossier(id: string, latest = false): Promise<Dossier> { return read("get_dossier", [id], latest); }
export async function getStats(): Promise<Record<string, unknown>> { return read("get_stats"); }
export async function getCredit(address: string, latest = false): Promise<string> { return read("get_credit", [address], latest); }
export async function listSubmissions(id: string, latest = false): Promise<any[]> { return read("list_submissions", [id], latest); }
export async function findLatestDossier(address: string): Promise<string> { return read("find_latest_dossier_by_sponsor", [address]); }
export async function getSubmissionForCommitment(commitment: string, latest = false): Promise<string> { return read("get_submission_for_commitment", [commitment], latest); }
export async function getSubmission(id: string, latest = false): Promise<any> { return read("get_submission", [id], latest); }

export async function ensureStudionet(): Promise<void> {
  const injected = provider(); if (!injected) throw new Error("Install an injected EIP-1193 wallet to continue.");
  const current = await injected.request({ method: "eth_chainId" }); if (typeof current === "string" && parseInt(current, 16) === CHAIN_ID) return;
  try { await injected.request({ method: "wallet_switchEthereumChain", params: [{ chainId: CHAIN_HEX }] }); }
  catch (error: any) { if (error?.code !== 4902) throw error; await injected.request({ method: "wallet_addEthereumChain", params: [{ chainId: CHAIN_HEX,
    chainName: "GenLayer Studionet", nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 }, rpcUrls: [RPC_URL], blockExplorerUrls: [EXPLORER_URL] }] }); }
}
export async function connectWallet(): Promise<string> {
  const injected = provider(); if (!injected) throw new Error("Install an injected EIP-1193 wallet to continue.");
  const result = await injected.request({ method: "eth_requestAccounts" });
  if (!Array.isArray(result) || typeof result[0] !== "string") throw new Error("No wallet account was returned.");
  await ensureStudionet(); return result[0];
}
export async function submitHubWrite(address: string, functionName: string, args: unknown[] = [], value = 0n): Promise<string> {
  const injected = provider(); if (!injected) throw new Error("No injected wallet found.");
  const client = createClient({ chain: studionet, endpoint: RPC_URL, account: address as `0x${string}`, provider: injected } as any);
  const hash = await withRpc(() => client.writeContract({ address: assertHub(), functionName, args, value } as any)); readCache.clear(); return String(hash);
}
export function assertSuccessfulReceipt(receipt: any): void {
  const status = String(receipt?.statusName ?? receipt?.status_name ?? "").toUpperCase();
  const execution = String(receipt?.txExecutionResultName ?? receipt?.tx_execution_result_name ?? "").toUpperCase();
  const leader = Array.isArray(receipt?.consensus_data?.leader_receipt)
    ? receipt.consensus_data.leader_receipt.find((item: any) => item?.mode === "leader") : undefined;
  const nestedSuccess = String(leader?.execution_result ?? "").toUpperCase() === "SUCCESS"
    && String(leader?.result?.status ?? "").toLowerCase() === "return";
  const namedSuccess = ["FINISHED_WITH_RETURN", "FINISHEDWITHRETURN"].includes(execution);
  if (status !== "FINALIZED" || !(namedSuccess || nestedSuccess)) {
    throw new Error(`GenVM execution failed (${status || "UNKNOWN"} / ${execution || "UNKNOWN"}).`);
  }
}
export async function waitForFinalization(hash: string): Promise<unknown> {
  const receipt: any = await withRpc(() => readClient().waitForTransactionReceipt({ hash: hash as any,
    status: "FINALIZED" as any, retries: 240, interval: 15_000 }));
  assertSuccessfulReceipt(receipt);
  return receipt;
}
export async function readWalletBalance(address: string): Promise<bigint> {
  const injected = provider(); if (!injected) throw new Error("No injected wallet found for balance verification.");
  const result = await withRpc(() => injected.request({ method: "eth_getBalance", params: [address, "latest"] }));
  if (typeof result !== "string" || !/^0x[0-9a-f]+$/i.test(result)) throw new Error("Wallet returned an invalid native balance.");
  return BigInt(result);
}
export function hasEmptyCode(code: unknown): boolean { return typeof code === "string" && code.toLowerCase() === "0x"; }
export async function assertExternalEoaRecipient(address: string): Promise<void> {
  if (!/^0x[0-9a-f]{40}$/i.test(address)) throw new Error("The payout recipient address is invalid.");
  const injected = provider(); if (!injected) throw new Error("No injected wallet found for recipient verification.");
  await ensureStudionet();
  const code = await withRpc(() => injected.request({ method: "eth_getCode", params: [address, "latest"] }));
  if (!hasEmptyCode(code)) {
    throw new Error("Native GEN payouts require an externally owned wallet address; contract-wallet recipients are not supported by this deployment.");
  }
}
export function isVerifiedNativeTransfer(child: any, recipient: string, expectedAmount: bigint): boolean {
  const status = String(child?.statusName ?? child?.status_name ?? "").toUpperCase();
  let value: bigint;
  try { value = typeof child?.value === "bigint" ? child.value : BigInt(String(child?.value ?? "0")); }
  catch { return false; }
  const destination = String(child?.to_address ?? child?.recipient ?? "").toLowerCase();
  return status === "FINALIZED" && child?.value_credited === true
    && destination === recipient.toLowerCase() && value === expectedAmount;
}
export async function waitForNativeTransfer(parentHash: string, recipient: string, expectedAmount: bigint,
  balanceBefore: bigint): Promise<{ childHash: string; balanceAfter: bigint }> {
  const client: any = readClient();
  const childHashes: string[] = await withRpc(() => client.getTriggeredTransactionIds({ hash: parentHash as any }));
  if (!Array.isArray(childHashes) || childHashes.length === 0) {
    throw new Error("Withdrawal parent finalized, but no outgoing child transfer was recorded.");
  }
  let deliveredChild = "";
  for (const childHash of childHashes) {
    let child: any;
    try { child = await withRpc(() => client.waitForTransactionReceipt({ hash: childHash as any,
      status: "FINALIZED", retries: 240, interval: 5_000 })); }
    catch { continue; }
    if (isVerifiedNativeTransfer(child, recipient, expectedAmount)) {
      deliveredChild = childHash; break;
    }
  }
  if (!deliveredChild) throw new Error("Withdrawal parent finalized, but no child transfer finalized with the expected recipient, amount, and credited flag.");
  let balanceAfter = await readWalletBalance(recipient);
  for (let attempt = 0; attempt < 60 && balanceAfter < balanceBefore + expectedAmount; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 2_000));
    balanceAfter = await readWalletBalance(recipient);
  }
  if (balanceAfter < balanceBefore + expectedAmount) throw new Error(`Child transfer ${deliveredChild} finalized, but recipient balance has not increased by the expected amount.`);
  return { childHash: deliveredChild, balanceAfter };
}
export function parseGen(value: string): bigint {
  if (!/^\d+(\.\d{1,18})?$/.test(value.trim())) throw new Error("Enter a valid GEN amount.");
  const [whole, fraction = ""] = value.trim().split("."); return BigInt(whole) * 10n ** 18n + BigInt(fraction.padEnd(18, "0"));
}
export function formatGen(atto: string): string {
  const value = BigInt(atto || "0"); const whole = value / 10n ** 18n;
  const fraction = (value % 10n ** 18n).toString().padStart(18, "0").replace(/0+$/, "").slice(0, 4);
  return `${whole}${fraction ? `.${fraction}` : ""}`;
}
export function randomSalt(): string { const bytes = crypto.getRandomValues(new Uint8Array(32)); return Array.from(bytes, (v) => v.toString(16).padStart(2, "0")).join(""); }
export function disclosureCommitment(input: Omit<PendingDisclosure, "commitment" | "createdAt" | "submissionId">, hub: string, researcher: string): string {
  const packet = JSON.stringify({ chain_id: "61999", claim: input.claim.trim(), dossier_id: input.dossierId,
    domain: "NOEMA_DISCLOSURE_V1", hub: hub.toLowerCase(), researcher: researcher.toLowerCase(), salt: input.salt, url: input.url.trim() });
  return sha256(stringToHex(packet)).slice(2);
}
export function loadPending(): PendingDisclosure[] { if (typeof window === "undefined") return []; try { return JSON.parse(localStorage.getItem(storageKey) ?? "[]"); } catch { return []; } }
export function savePending(item: PendingDisclosure): void { const prior = loadPending().filter((x) => x.commitment !== item.commitment); localStorage.setItem(storageKey, JSON.stringify([item, ...prior].slice(0, 24))); }
export function updatePending(commitment: string, updates: Partial<PendingDisclosure>): void { localStorage.setItem(storageKey, JSON.stringify(loadPending().map((x) => x.commitment === commitment ? { ...x, ...updates } : x))); }
export function removePending(commitment: string): void { localStorage.setItem(storageKey, JSON.stringify(loadPending().filter((x) => x.commitment !== commitment))); }
export function loadPendingPayouts(account?: string): PendingPayout[] {
  if (typeof window === "undefined") return [];
  try { const records: PendingPayout[] = JSON.parse(localStorage.getItem(payoutStorageKey) ?? "[]");
    if (!Array.isArray(records)) return [];
    return records.filter((item) => item && typeof item.account === "string" && typeof item.parentHash === "string"
      && (!account || item.account.toLowerCase() === account.toLowerCase()));
  } catch { return []; }
}
export function upsertPendingPayout(records: PendingPayout[], item: PendingPayout): PendingPayout[] {
  const next = records.filter((prior) => prior.parentHash.toLowerCase() !== item.parentHash.toLowerCase());
  return [item, ...next].slice(0, 24);
}
export function savePendingPayout(item: PendingPayout): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(payoutStorageKey, JSON.stringify(upsertPendingPayout(loadPendingPayouts(), item)));
}
export function removePendingPayout(parentHash: string): void {
  if (typeof window === "undefined") return;
  try { const records: PendingPayout[] = JSON.parse(localStorage.getItem(payoutStorageKey) ?? "[]");
    localStorage.setItem(payoutStorageKey, JSON.stringify(records.filter((item) => item.parentHash.toLowerCase() !== parentHash.toLowerCase())));
  } catch { localStorage.removeItem(payoutStorageKey); }
}
