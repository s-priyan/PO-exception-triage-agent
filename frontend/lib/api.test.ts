import { afterEach, describe, expect, it, vi } from "vitest";
import { getFlaggedPos, postTriage } from "./api";

afterEach(() => vi.restoreAllMocks());

describe("api client", () => {
  it("fetches flagged POs", async () => {
    const payload = { count: 0, items: [] };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => payload }),
    );
    await expect(getFlaggedPos()).resolves.toEqual(payload);
  });

  it("posts a triage question", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ halt: null }) });
    vi.stubGlobal("fetch", fetchMock);
    await postTriage("PO-88405?");
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ question: "PO-88405?" });
  });

  it("throws on a non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(getFlaggedPos()).rejects.toThrow(/500/);
  });
});
