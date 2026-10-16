import { NextRequest, NextResponse } from "next/server";

const RPC = "https://studio.genlayer.com/api";
const HASH = /^0x[0-9a-fA-F]{64}$/;

export const dynamic = "force-dynamic";
export const maxDuration = 15;

/** Read-only, fixed-method projection for consensus validators checking a payout. */
export async function GET(request: NextRequest) {
  const hash = request.nextUrl.searchParams.get("hash") ?? "";
  if (!HASH.test(hash)) {
    return NextResponse.json({ error: "A 32-byte transaction hash is required." }, { status: 400 });
  }

  try {
    const upstream = await fetch(RPC, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_getTransactionByHash", params: [hash] }),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (!upstream.ok) {
      return NextResponse.json({ error: "StudioNet receipt lookup is temporarily unavailable." }, {
        status: 503, headers: { "cache-control": "no-store" },
      });
    }
    const payload = await upstream.json() as { error?: unknown; result?: Record<string, any> | null };
    const tx = payload?.result;
    if (payload?.error || !tx || String(tx.hash ?? tx.tx_id ?? "").toLowerCase() !== hash.toLowerCase()) {
      return NextResponse.json({ error: "Transaction receipt is not available." }, {
        status: 404, headers: { "cache-control": "no-store" },
      });
    }

    const projected = {
      hash: tx.hash ?? tx.tx_id ?? "",
      status: tx.status_name ?? tx.status ?? "",
      created_at: tx.created_at ?? "",
      from_address: tx.from_address ?? tx.sender ?? "",
      to_address: tx.to_address ?? tx.recipient ?? "",
      data: tx.data && typeof tx.data === "object" ? { calldata: tx.data.calldata ?? "" } : {},
      messages: Array.isArray(tx.messages) ? tx.messages.map((message: Record<string, unknown>) => ({
        recipient: message.recipient ?? "",
        value: message.value ?? "0",
        onAcceptance: message.onAcceptance,
      })) : [],
      triggered_by: tx.triggered_by ?? tx.triggered_by_hash ?? "",
      value: tx.value ?? "0",
      value_credited: tx.value_credited,
    };
    return NextResponse.json(projected, { headers: { "cache-control": "public, max-age=5, s-maxage=5" } });
  } catch {
    return NextResponse.json({ error: "StudioNet receipt lookup is temporarily unavailable." }, {
      status: 503, headers: { "cache-control": "no-store" },
    });
  }
}
