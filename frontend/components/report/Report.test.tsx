import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Report } from "./Report";
import type { TriageResponse } from "@/lib/types";

const result: TriageResponse = {
  halt: null,
  triage: {
    po_id: "PO-88405",
    halt: null,
    planner_question: "PO-88405?",
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
    exception_types: ["quantity_variance_short", "eta_slip"],
    queries: [],
  },
  recommendation: {
    po_id: "PO-88405",
    recommended_action: "amend",
    rationale: "V2 short-ship within amendment tolerance.",
    citations: ["variance_detection_sop.md §2.1"],
    confidence: "high",
    escalation_target_role: "Senior Merchandiser",
  },
  citations: [
    {
      code: "MERCH-SOP-014",
      section: "§2.1",
      title: "Compound variance rule",
      quote: "Where a PO carries two or more concurrent V1 variances…",
    },
  ],
};

describe("Report", () => {
  it("renders action headline, stats, chips, confidence, escalation and citation", () => {
    render(<Report result={result} />);
    expect(screen.getByText("Amend the purchase order")).toBeInTheDocument();
    expect(screen.getByText("5,000")).toBeInTheDocument();
    expect(screen.getByText("-12.0%")).toBeInTheDocument();
    expect(screen.getByText("+9d")).toBeInTheDocument();
    expect(screen.getByText("Short-ship")).toBeInTheDocument();
    expect(screen.getByText(/high/i)).toBeInTheDocument();
    expect(screen.getByText("Senior Merchandiser")).toBeInTheDocument();
    expect(screen.getByText(/MERCH-SOP-014 §2.1/)).toBeInTheDocument();
    expect(screen.getByText("Compound variance rule")).toBeInTheDocument();
    expect(screen.getByText(/recommended action/i)).toBeInTheDocument();
    expect(screen.getByText(/TIER 2 .* MATERIAL/)).toBeInTheDocument();
    expect(
      screen.getByText(/V2 short-ship within amendment tolerance/),
    ).toBeInTheDocument();
    expect(screen.getByText("4,400")).toBeInTheDocument();
    expect(screen.getByText(/Where a PO carries/)).toBeInTheDocument();
    expect(screen.getByText("ETA slip")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /open po in erp/i }),
    ).toBeDisabled();
    expect(screen.queryByText("0.82")).not.toBeInTheDocument();
  });
});
