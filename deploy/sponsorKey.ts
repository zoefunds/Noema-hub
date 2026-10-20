export type SponsorKeySelection = {
  privateKey: `0x${string}`;
  persistUntilSweep: boolean;
  handling: "provided_ephemerally_not_persisted" | "generated_and_persisted_until_sweep";
};

export function selectSponsorKey(providedValue: string | undefined, generatedKey: `0x${string}`): SponsorKeySelection {
  const provided = providedValue?.trim();
  if (provided && !/^0x[0-9a-fA-F]{64}$/.test(provided)) {
    throw new Error("NOEMA_E2E_SPONSOR_PRIVATE_KEY must be a 32-byte 0x-prefixed key");
  }
  return provided
    ? { privateKey: provided as `0x${string}`, persistUntilSweep: false, handling: "provided_ephemerally_not_persisted" }
    : { privateKey: generatedKey, persistUntilSweep: true, handling: "generated_and_persisted_until_sweep" };
}

export function sweepableSponsorBalance(currentBalance: bigint, openingBalance: bigint, ephemeralKey: boolean): bigint {
  if (!ephemeralKey) return currentBalance;
  return currentBalance > openingBalance ? currentBalance - openingBalance : 0n;
}

// `genlayer deploy` evaluates every TypeScript module in this directory.
// This module is a shared helper, so its deployment entry point is a no-op.
export default async function main() {
  return { skipped: true, module: "sponsorKey helper" };
}
