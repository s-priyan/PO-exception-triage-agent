import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "./page";
import * as api from "@/lib/api";
import type { FlaggedPo, TriageResponse } from "@/lib/types";

const po: FlaggedPo = {
  po_id: "PO-88405",
  supplier: "Anadolu Tekstil",
  category: "Womenswear",
  tier: "V2",
  tier_display: { number: 2, word: "Material" },
  qty_variance_pct: -12,
  eta_variance_days: 9,
  summary_line: "Short-ship -12% · ETA +9d",
  query: "PO-88405 came in short and the ETA slipped, what's going on?",
};

const triage: TriageResponse = {
  halt: null,
  triage: {
    po_id: "PO-88405",
    halt: null,
    planner_question: po.query,
    po_record: { ordered_qty: 5000, confirmed_qty: 4400 },
    forecast: null,
    tier: {
      tier: "V2",
      qty_variance_pct: -12,
      eta_variance_days: 9,
      value_at_risk_gbp: 22800,
      overrides_applied: [],
      validation: { passed: true, failures: [] },
    },
    exception_types: ["quantity_variance_short"],
    queries: [],
  },
  recommendation: {
    po_id: "PO-88405",
    recommended_action: "amend",
    rationale: "V2 short-ship within amendment tolerance.",
    citations: [],
    confidence: "high",
    escalation_target_role: null,
  },
  citations: [],
};

beforeEach(() => {
  vi.spyOn(api, "getFlaggedPos").mockResolvedValue({ count: 1, items: [po] });
  vi.spyOn(api, "postTriage").mockResolvedValue(triage);
});

describe("Page", () => {
  it("loads POs, prefills on select, and renders the report after Ask", async () => {
    render(<Page />);
    await waitFor(() => expect(screen.getByText("PO-88405")).toBeInTheDocument());

    await userEvent.click(screen.getByText("PO-88405"));
    expect(screen.getByDisplayValue(po.query)).toBeInTheDocument();
    expect(screen.getByText(/ask a question/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /ask/i }));
    await waitFor(() =>
      expect(screen.getByText("Amend the purchase order")).toBeInTheDocument(),
    );
  });
});
