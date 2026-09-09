import { afterEach, describe, expect, it, vi } from "vitest";
import { getFlaggedPos, postTriage } from "./api";

afterEach(() => vi.restoreAllMocks());

describe("api client", () => {
  it("fetches flagged POs from the correct URL and forwards the signal", async () => {
    const payload = { count: 0, items: [] };
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => payload });
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    await expect(getFlaggedPos(controller.signal)).resolves.toEqual(payload);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/flagged-pos$/);
    expect(init.signal).toBe(controller.signal);
  });

  it("posts a triage question with JSON body and headers", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ halt: null }) });
    vi.stubGlobal("fetch", fetchMock);

    await postTriage("PO-88405?");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/triage$/);
    expect(init.method).toBe("POST");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body)).toEqual({ question: "PO-88405?" });
  });

  it("throws with the status when flagged POs request is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(getFlaggedPos()).rejects.toThrow(/500/);
  });

  it("throws with the status when triage request is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 502 }));
    await expect(postTriage("PO-88405?")).rejects.toThrow(/502/);
  });
});
