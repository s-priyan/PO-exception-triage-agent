import { describe, expect, it } from "vitest";
import {
  actionHeadline,
  confidenceFill,
  EXCEPTION_LABELS,
  formatEtaDays,
  formatPct,
  formatQty,
} from "./format";

describe("format helpers", () => {
  it("maps action enum to a headline", () => {
    expect(actionHeadline("amend")).toBe("Amend the purchase order");
    expect(actionHeadline("escalate")).toBe("Escalate for review");
  });

  it("labels exception types", () => {
    expect(EXCEPTION_LABELS.quantity_variance_short).toBe("Short-ship");
    expect(EXCEPTION_LABELS.eta_slip).toBe("ETA slip");
  });

  it("maps confidence to a bar fill", () => {
    expect(confidenceFill("high")).toBe(100);
    expect(confidenceFill("medium")).toBe(66);
    expect(confidenceFill("low")).toBe(33);
  });

  it("formats variance, days and quantities", () => {
    expect(formatPct(-12)).toBe("-12.0%");
    expect(formatPct(null)).toBe("—");
    expect(formatEtaDays(9)).toBe("+9d");
    expect(formatEtaDays(null)).toBe("—");
    expect(formatQty(4800)).toBe("4,800");
    expect(formatQty(null)).toBe("—");
  });
});
