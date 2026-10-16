import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import type { DecodedDeployData, GenLayerClient, TransactionHash } from "genlayer-js/types";
import { TransactionStatus } from "genlayer-js/types";

function receiptAccepted(receipt: any): boolean {
  const status = String(receipt?.statusName ?? receipt?.status_name ?? "").toUpperCase();
  const execution = String(receipt?.txExecutionResultName ?? receipt?.tx_execution_result_name ?? "").toUpperCase();
  const leader = Array.isArray(receipt?.consensus_data?.leader_receipt)
    ? receipt.consensus_data.leader_receipt.find((item: any) => item?.mode === "leader") : undefined;
  const nestedSuccess = String(leader?.execution_result ?? "").toUpperCase() === "SUCCESS"
    && String(leader?.result?.status ?? "").toLowerCase() === "return";
  return status === "FINALIZED" && (["FINISHED_WITH_RETURN", "FINISHEDWITHRETURN"].includes(execution) || nestedSuccess);
}

async function deploy(client: GenLayerClient<any>, file: string, args: unknown[] = []) {
  const code = new Uint8Array(readFileSync(path.resolve(process.cwd(), file)));
  const hash = await client.deployContract({ code, args } as any);
  const receipt: any = await client.waitForTransactionReceipt({ hash: hash as TransactionHash,
    status: TransactionStatus.FINALIZED, retries: 240, interval: 5000 } as any);
  if (!receiptAccepted(receipt)) throw new Error(`Deployment failed for ${file}: ${JSON.stringify(receipt)}`);
  const address = (receipt?.txDataDecoded as DecodedDeployData | undefined)?.contractAddress
    || receipt?.data?.contract_address || receipt?.contract_address || receipt?.recipient;
  if (!address) throw new Error(`No address returned for ${file}`);
  return { address: String(address), txHash: String(hash) };
}

export default async function main(client: GenLayerClient<any>) {
  const chainId = Number((client as any)?.chain?.id);
  if (chainId !== 61999) throw new Error(`Noema deployment is locked to Studionet 61999; received ${chainId}`);

  const manifestPath = path.resolve(process.cwd(), "deployments/studionet.json");
  if (existsSync(manifestPath) && process.env.NOEMA_FORCE_REDEPLOY !== "1") {
    return JSON.parse(readFileSync(manifestPath, "utf8"));
  }

  const hub = await deploy(client, "contracts/noema_hub.py", ["", ""]);
  const witness = await deploy(client, "contracts/source_witness.py", [hub.address]);
  const engine = await deploy(client, "contracts/verdict_engine.py", [hub.address]);
  const configureHash = await (client as any).writeContract({ address: hub.address,
    functionName: "configure", args: [witness.address, engine.address], value: 0n });
  const configureReceipt: any = await client.waitForTransactionReceipt({ hash: configureHash as TransactionHash,
    status: TransactionStatus.FINALIZED, retries: 240, interval: 5000 } as any);
  if (!receiptAccepted(configureReceipt)) throw new Error(`One-time worker binding failed: ${JSON.stringify(configureReceipt)}`);

  const manifest = { product: "Noema", network: "studionet", chainId: 61999,
    rpc: "https://studio.genlayer.com/api", explorer: "https://explorer-studio.genlayer.com",
    deployedAt: new Date().toISOString(), contracts: { hub, witness, engine, configureTxHash: String(configureHash) } };
  mkdirSync(path.resolve(process.cwd(), "deployments"), { recursive: true });
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + "\n");
  writeFileSync(path.resolve(process.cwd(), "frontend/.env.local"), [
    "NEXT_PUBLIC_GENLAYER_CHAIN_ID=61999",
    "NEXT_PUBLIC_GENLAYER_RPC_URL=https://studio.genlayer.com/api",
    "NEXT_PUBLIC_GENLAYER_EXPLORER=https://explorer-studio.genlayer.com",
    `NEXT_PUBLIC_NOEMA_HUB_ADDRESS=${hub.address}`,
    `NEXT_PUBLIC_NOEMA_WITNESS_ADDRESS=${witness.address}`,
    `NEXT_PUBLIC_NOEMA_ENGINE_ADDRESS=${engine.address}`,
    "",
  ].join("\n"));
  return manifest;
}
