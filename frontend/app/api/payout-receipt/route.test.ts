import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET } from "./route";

const hash = `0x${"a".repeat(64)}`;
function request(value = hash) {
  return new NextRequest(`https://neoma-hub.vercel.app/api/payout-receipt?hash=${encodeURIComponent(value)}`);
}

afterEach(() => vi.unstubAllGlobals());

describe("read-only payout receipt projection", () => {
  it("fetches only the exact transaction hash using the fixed read method and returns minimal fields", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ result: {
      hash, status: 7, created_at: "2026-10-16T11:09:20.089709+00:00", from_address: "0x111", to_address: "0x222",
      data: { calldata: "withdraw" }, messages: [{ recipient: "0x333", value: 42, onAcceptance: false }],
      triggered_by: "0x444", value: 42, value_credited: true, secret_large_field: "never forward",
    } }), { status: 200, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET(request());

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      hash, status: 7, created_at: "2026-10-16T11:09:20.089709+00:00", from_address: "0x111", to_address: "0x222",
      data: { calldata: "withdraw" }, messages: [{ recipient: "0x333", value: 42, onAcceptance: false }],
      triggered_by: "0x444", value: 42, value_credited: true,
    });
    expect(fetchMock).toHaveBeenCalledWith("https://studio.genlayer.com/api", expect.objectContaining({
      method: "POST", cache: "no-store", body: JSON.stringify({
        jsonrpc: "2.0", id: 1, method: "eth_getTransactionByHash", params: [hash],
      }),
    }));
  });

  it("rejects malformed identifiers before making an upstream call", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    expect((await GET(request("latest"))).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("does not turn absent or failed upstream receipts into proof", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ result: null }), { status: 200 }))
      .mockResolvedValueOnce(new Response("", { status: 503 })));
    expect((await GET(request())).status).toBe(404);
    expect((await GET(request())).status).toBe(503);
  });
});
