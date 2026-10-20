import assert from "node:assert/strict";
import test from "node:test";
import { selectSponsorKey, sweepableSponsorBalance } from "../deploy/sponsorKey.ts";

const generated = `0x${"b".repeat(64)}` as `0x${string}`;
const provided = `0x${"a".repeat(64)}`;

test("provided throwaway key stays ephemeral", () => {
  assert.deepEqual(selectSponsorKey(` ${provided} `, generated), {
    privateKey: provided,
    persistUntilSweep: false,
    handling: "provided_ephemerally_not_persisted",
  });
});

test("generated key remains recoverable until sweep", () => {
  assert.deepEqual(selectSponsorKey(undefined, generated), {
    privateKey: generated,
    persistUntilSweep: true,
    handling: "generated_and_persisted_until_sweep",
  });
});

test("malformed provided secrets are rejected without echoing them", () => {
  const secretLike = "not-a-key-secret-value";
  assert.throws(() => selectSponsorKey(secretLike, generated), (error: Error) => {
    assert.equal(error.message.includes(secretLike), false);
    return error.message.includes("32-byte 0x-prefixed key");
  });
});

test("ephemeral-key sweep cannot consume pre-existing wallet funds", () => {
  assert.equal(sweepableSponsorBalance(2_000n, 3_000n, true), 0n);
  assert.equal(sweepableSponsorBalance(4_000n, 3_000n, true), 1_000n);
  assert.equal(sweepableSponsorBalance(4_000n, 3_000n, false), 4_000n);
});
