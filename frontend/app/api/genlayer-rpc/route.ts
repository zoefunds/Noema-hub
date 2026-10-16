import { NextRequest, NextResponse } from "next/server";

const UPSTREAM = "https://studio.genlayer.com/api";
const MAX_BODY_BYTES = 1_000_000;
const ALLOWED_METHODS = new Set([
  "eth_chainId",
  "eth_estimateGas",
  "eth_gasPrice",
  "eth_getBalance",
  "eth_getCode",
  "eth_getTransactionByHash",
  "eth_getTransactionCount",
  "eth_getTransactionReceipt",
  "gen_call",
  "gen_getContractCode",
  "gen_getContractSchema",
]);

export const dynamic = "force-dynamic";
export const maxDuration = 30;

export async function POST(request: NextRequest) {
  const origin = request.headers.get("origin");
  if (origin && origin !== new URL(request.url).origin) {
    return NextResponse.json({ error: "Cross-origin RPC requests are not accepted." }, { status: 403 });
  }

  const declaredLength = Number(request.headers.get("content-length") ?? 0);
  if (declaredLength > MAX_BODY_BYTES) {
    return NextResponse.json({ error: "RPC request exceeds the size limit." }, { status: 413 });
  }

  let body: unknown;
  try {
    const raw = await request.text();
    if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) {
      return NextResponse.json({ error: "RPC request exceeds the size limit." }, { status: 413 });
    }
    body = JSON.parse(raw);
  } catch {
    return NextResponse.json({ error: "RPC request must be valid JSON." }, { status: 400 });
  }

  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return NextResponse.json({ error: "Only a single JSON-RPC request is accepted." }, { status: 400 });
  }
  const rpc = body as { jsonrpc?: unknown; id?: unknown; method?: unknown; params?: unknown };
  if (rpc.jsonrpc !== "2.0" || typeof rpc.method !== "string" || !ALLOWED_METHODS.has(rpc.method)
      || !(typeof rpc.id === "string" || typeof rpc.id === "number" || rpc.id === null)
      || !(rpc.params === undefined || Array.isArray(rpc.params) || (rpc.params !== null && typeof rpc.params === "object"))) {
    return NextResponse.json({ error: "Unsupported or malformed JSON-RPC request." }, { status: 400 });
  }

  try {
    const upstream = await fetch(UPSTREAM, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(rpc),
      cache: "no-store",
      signal: AbortSignal.timeout(25_000),
    });
    const responseBody = await upstream.text();
    return new Response(responseBody, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/json",
        "cache-control": "no-store",
      },
    });
  } catch {
    return NextResponse.json({
      jsonrpc: "2.0",
      id: rpc.id,
      error: { code: -32000, message: "StudioNet RPC is temporarily unavailable." },
    }, { status: 502, headers: { "cache-control": "no-store" } });
  }
}
