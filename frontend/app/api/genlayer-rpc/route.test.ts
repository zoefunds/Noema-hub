import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "./route";

const origin = "https://neoma-hub.vercel.app";
function request(body: string, headers: Record<string, string> = {}) {
  return new NextRequest(`${origin}/api/genlayer-rpc`, {
    method: "POST",
    headers: { origin, "content-type": "application/json", ...headers },
    body,
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("StudioNet RPC proxy", () => {
  it("forwards bounded allowlisted reads to the fixed RPC and preserves its response", async () => {
    const rpc = { jsonrpc: "2.0", id: 7, method: "gen_call", params: [{ type: "read" }] };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ jsonrpc: "2.0", id: 7, result: "0x01" }), {
      status: 200, headers: { "content-type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(request(JSON.stringify(rpc)));

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ jsonrpc: "2.0", id: 7, result: "0x01" });
    expect(fetchMock).toHaveBeenCalledWith("https://studio.genlayer.com/api", expect.objectContaining({ method: "POST" }));
  });

  it("rejects cross-origin requests and transaction-sending methods without contacting upstream", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const foreign = await POST(request(JSON.stringify({ jsonrpc: "2.0", id: 1, method: "gen_call", params: [] }), { origin: "https://attacker.example" }));
    const write = await POST(request(JSON.stringify({ jsonrpc: "2.0", id: 2, method: "eth_sendRawTransaction", params: ["0xdead"] })));

    expect(foreign.status).toBe(403);
    expect(write.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects oversized and malformed request bodies", async () => {
    const tooLarge = await POST(request("x".repeat(1_000_001)));
    const malformed = await POST(request("{"));
    expect(tooLarge.status).toBe(413);
    expect(malformed.status).toBe(400);
  });
});
