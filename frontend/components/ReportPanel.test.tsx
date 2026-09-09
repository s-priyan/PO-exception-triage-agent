import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReportPanel } from "./ReportPanel";
import type { TriageResponse } from "@/lib/types";

function haltResult(): TriageResponse {
  return {
    halt: "data_quality",
    triage: {
      po_id: "PO-88416",
      halt: "data_quality",
      planner_question: "PO-88416?",
      po_record: { ordered_qty: 3200, confirmed_qty: 3050 },
      forecast: null,
      tier: {
        tier: "V2",
        qty_variance_pct: -4.7,
        eta_variance_days: null,
        value_at_risk_gbp: 3300,
        overrides_applied: [],
        validation: { passed: false, failures: ["eta is null on a CONFIRMED PO"] },
      },
      exception_types: [],
      queries: [],
    },
    recommendation: {
      po_id: "PO-88416",
      recommended_action: "escalate",
      rationale: "Record fails data-quality checks; cannot recommend.",
      citations: [],
      confidence: "low",
      escalation_target_role: "Intake Planning Lead",
    },
    citations: [],
  };
}

describe("ReportPanel", () => {
  it("shows the empty state", () => {
    render(
      <ReportPanel phase="empty" selectedPoId="PO-88405" onRetry={() => {}} />,
    );
    expect(screen.getByText(/ask a question/i)).toBeInTheDocument();
  });

  it("renders the edge-state panel on halt", () => {
    render(
      <ReportPanel
        phase="done"
        result={haltResult()}
        selectedPoId="PO-88416"
        onRetry={() => {}}
      />,
    );
    expect(screen.getByText(/can't auto-recommend/i)).toBeInTheDocument();
    expect(screen.getByText("Data-quality failure")).toBeInTheDocument();
    expect(screen.getByText("Intake Planning Lead")).toBeInTheDocument();
  });
});
