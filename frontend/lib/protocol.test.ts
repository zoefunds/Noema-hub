import { describe, expect, it } from "vitest";
import { assertSuccessfulReceipt, disclosureCommitment, hasEmptyCode, isMatchingFinalizedNativeTransfer, isVerifiedNativeTransfer, upsertPendingPayout } from "./liveProtocol";

describe("disclosure commitment", () => {
  const input = { dossierId: "noema-7", url: "https://example.org/report", claim: "The release shipped.", salt: "ab".repeat(32) };
  it("is stable and lowercase", () => {
    const value = disclosureCommitment(input, `0x${"1".repeat(40)}`, `0x${"2".repeat(40)}`);
    expect(value).toMatch(/^[0-9a-f]{64}$/);
    expect(value).toBe(disclosureCommitment(input, `0x${"1".repeat(40)}`, `0x${"2".repeat(40)}`));
  });
  it("binds the researcher and salt", () => {
    const original = disclosureCommitment(input, `0x${"1".repeat(40)}`, `0x${"2".repeat(40)}`);
    expect(original).not.toBe(disclosureCommitment(input, `0x${"1".repeat(40)}`, `0x${"3".repeat(40)}`));
    expect(original).not.toBe(disclosureCommitment({ ...input, salt: "cd".repeat(32) }, `0x${"1".repeat(40)}`, `0x${"2".repeat(40)}`));
  });
});

describe("GenVM receipt acceptance", () => {
  it("requires finality and successful execution", () => {
    expect(() => assertSuccessfulReceipt({ statusName: "Finalized", txExecutionResultName: "FinishedWithReturn" })).not.toThrow();
    expect(() => assertSuccessfulReceipt({ status_name: "FINALIZED", consensus_data: { leader_receipt: [
      { mode: "leader", execution_result: "SUCCESS", result: { status: "return" } },
    ] } })).not.toThrow();
    expect(() => assertSuccessfulReceipt({ statusName: "Finalized", txExecutionResultName: "FinishedWithError" })).toThrow(/execution failed/);
    expect(() => assertSuccessfulReceipt({ status_name: "FINALIZED", consensus_data: { leader_receipt: [
      { mode: "leader", execution_result: "SUCCESS", result: { status: "error" } },
    ] } })).toThrow(/execution failed/);
    expect(() => assertSuccessfulReceipt({ statusName: "Accepted", txExecutionResultName: "FinishedWithReturn" })).toThrow(/execution failed/);
  });
});

describe("native payout acceptance", () => {
  const recipient = `0x${"7".repeat(40)}`;
  const child = { status_name: "FINALIZED", to_address: recipient, value: 1_100_000_000_000_000n, value_credited: true };
  it("requires a finalized credited child to the exact recipient and amount", () => {
    expect(isVerifiedNativeTransfer(child, recipient, 1_100_000_000_000_000n)).toBe(true);
    expect(isVerifiedNativeTransfer({ ...child, value_credited: false }, recipient, 1_100_000_000_000_000n)).toBe(false);
    expect(isVerifiedNativeTransfer({ ...child, status_name: "ERROR" }, recipient, 1_100_000_000_000_000n)).toBe(false);
    expect(isVerifiedNativeTransfer({ ...child, to_address: `0x${"8".repeat(40)}` }, recipient, 1_100_000_000_000_000n)).toBe(false);
    expect(isVerifiedNativeTransfer({ ...child, value: 5n }, recipient, 1_100_000_000_000_000n)).toBe(false);
  });
  it("recognizes finalized failed transfers for on-chain reconciliation without calling them paid", () => {
    const failed = { ...child, value_credited: false };
    expect(isMatchingFinalizedNativeTransfer(failed, recipient, 1_100_000_000_000_000n)).toBe(true);
    expect(isVerifiedNativeTransfer(failed, recipient, 1_100_000_000_000_000n)).toBe(false);
    expect(isMatchingFinalizedNativeTransfer({ ...failed, status_name: "ACCEPTED" }, recipient, 1_100_000_000_000_000n)).toBe(false);
    expect(isMatchingFinalizedNativeTransfer({ ...failed, to_address: `0x${"8".repeat(40)}` }, recipient, 1_100_000_000_000_000n)).toBe(false);
  });
  it("only treats empty-code addresses as externally owned payout recipients", () => {
    expect(hasEmptyCode("0x")).toBe(true);
    expect(hasEmptyCode("0x60006000")).toBe(false);
    expect(hasEmptyCode(undefined)).toBe(false);
  });
  it("retains multiple pending withdrawals for one account without replacing older recovery records", () => {
    const first = { account: recipient, parentHash: `0x${"1".repeat(64)}`, amount: "7", walletBefore: "10", createdAt: "2026-10-16T00:00:00.000Z" };
    const second = { ...first, parentHash: `0x${"2".repeat(64)}`, amount: "11" };
    const records = upsertPendingPayout(upsertPendingPayout([], first), second);
    expect(records.map((item) => item.parentHash)).toEqual([second.parentHash, first.parentHash]);
    const refreshed = upsertPendingPayout(records, { ...first, amount: "9" });
    expect(refreshed).toHaveLength(2);
    expect(refreshed[0].amount).toBe("9");
  });
});
