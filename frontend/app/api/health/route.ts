import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const rpc = process.env.NEXT_PUBLIC_GENLAYER_RPC_URL || "https://studio.genlayer.com/api";
  const hub = process.env.NEXT_PUBLIC_NOEMA_HUB_ADDRESS || "";
  try {
    const response = await fetch(rpc, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_chainId", params: [] }), cache: "no-store" });
    const payload = await response.json();
    const chainId = typeof payload.result === "string" ? parseInt(payload.result, 16) : null;
    return NextResponse.json({ ok: response.ok && chainId === 61999 && /^0x[0-9a-fA-F]{40}$/.test(hub),
      service: "Noema Web", network: "GenLayer Studionet", chainId, hub, rpcReachable: response.ok,
      checkedAt: new Date().toISOString() }, { status: response.ok && chainId === 61999 ? 200 : 503 });
  } catch (error) {
    return NextResponse.json({ ok: false, service: "Noema Web", network: "GenLayer Studionet", hub,
      rpcReachable: false, error: error instanceof Error ? error.message : "RPC health check failed",
      checkedAt: new Date().toISOString() }, { status: 503 });
  }
}
