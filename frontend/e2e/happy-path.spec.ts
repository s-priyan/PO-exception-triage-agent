import { expect, test } from "@playwright/test";

const flagged = {
  count: 1,
  items: [
    {
      po_id: "PO-88405",
      supplier: "Anadolu Tekstil",
      category: "Womenswear",
      tier: "V2",
      tier_display: { number: 2, word: "Material" },
      qty_variance_pct: -12,
      eta_variance_days: 9,
      summary_line: "Short-ship -12% · ETA +9d",
      query: "PO-88405 came in short and the ETA slipped, what's going on?",
    },
  ],
};

const triage = {
  halt: null,
  triage: {
    po_id: "PO-88405",
    halt: null,
    planner_question: flagged.items[0].query,
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

test("planner selects a PO, asks, and sees the recommendation", async ({ page }) => {
  await page.route("**/flagged-pos", (route) =>
    route.fulfill({ json: flagged }),
  );
  await page.route("**/triage", (route) => route.fulfill({ json: triage }));

  await page.goto("/");
  await page.getByText("PO-88405").click();
  await expect(page.getByText(/ask a question/i)).toBeVisible();

  await page.getByRole("button", { name: /ask/i }).click();
  await expect(page.getByText("Amend the purchase order")).toBeVisible();
  await expect(page.getByText("Compound variance rule")).toBeVisible();
});
