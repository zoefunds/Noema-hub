import { createAccount, createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

const key = process.env.NOEMA_TIMEOUT_DEPLOYER_PRIVATE_KEY;
delete process.env.NOEMA_TIMEOUT_DEPLOYER_PRIVATE_KEY;
if (!key || !/^0x[0-9a-fA-F]{64}$/.test(key)) {
  throw new Error("NOEMA_TIMEOUT_DEPLOYER_PRIVATE_KEY must be a 32-byte 0x-prefixed value");
}
const account = createAccount(key);
const client = createClient({ chain: studionet, endpoint: "https://studio.genlayer.com/api", account });
console.log(`Running the real StudioNet timeout acceptance harness with signer ${account.address}; key remains process-memory only.`);

process.env.NOEMA_TIMEOUT_E2E = "1";
const { default: timeoutRollback } = await import("./deploy/timeoutRollback.ts");
const result = await timeoutRollback(client);
console.log(JSON.stringify(result, null, 2));
process.exit(0);
