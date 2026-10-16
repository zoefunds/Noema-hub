import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const rpc = process.env.NEXT_PUBLIC_GENLAYER_RPC_URL || "https://studio.genlayer.com/api";
  const hub = process.env.NEXT_PUBLIC_NOEMA_HUB_ADDRESS || "";
  const validHub = /^0x[0-9a-fA-F]{40}$/.test(hub);
  try {
    if (!validHub) throw new Error("No valid Hub address is configured.");
    const [chainResponse, codeResponse] = await Promise.all([
      fetch(rpc, { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_chainId", params: [] }), cache: "no-store" }),
      fetch(rpc, { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 2, method: "gen_getContractCode", params: [hub] }), cache: "no-store" }),
    ]);
    const [chainPayload, codePayload] = await Promise.all([chainResponse.json(), codeResponse.json()]);
    const chainId = typeof chainPayload.result === "string" ? parseInt(chainPayload.result, 16) : null;
    const hubCodeAvailable = typeof codePayload.result === "string" && codePayload.result.length > 0;
    const ok = chainResponse.ok && codeResponse.ok && chainId === 61999 && hubCodeAvailable;
    return NextResponse.json({ ok, service: "Noema Web", network: "GenLayer Studionet", chainId, hub,
      rpcReachable: chainResponse.ok && codeResponse.ok, hubCodeAvailable,
      checkedAt: new Date().toISOString() }, { status: ok ? 200 : 503 });
  } catch (error) {
    return NextResponse.json({ ok: false, service: "Noema Web", network: "GenLayer Studionet", hub,
      rpcReachable: false, hubCodeAvailable: false, error: error instanceof Error ? error.message : "RPC health check failed",
      checkedAt: new Date().toISOString() }, { status: 503 });
  }
}
