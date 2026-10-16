import { describe, expect, it } from "vitest";
import { disclosureCommitment } from "./liveProtocol";

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
