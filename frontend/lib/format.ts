import { Confidence, ExceptionType, RecommendedAction } from "./types";

const ACTION_HEADLINES: Record<RecommendedAction, string> = {
  amend: "Amend the purchase order",
  split_child_po: "Split into a child PO",
  firm_planned_order: "Firm the planned order",
  raise_backorder: "Raise a back-order for the shortfall",
  escalate: "Escalate for review",
};

export function actionHeadline(action: RecommendedAction): string {
  return ACTION_HEADLINES[action];
}

export const EXCEPTION_LABELS: Record<ExceptionType, string> = {
  quantity_variance_short: "Short-ship",
  quantity_variance_over: "Over-delivery",
  eta_slip: "ETA slip",
  partial_delivery: "Part received",
  season_boundary_risk: "Season boundary",
  wholesale_constraint: "Wholesale",
  parent_child_context: "Parent/child",
};

export function confidenceFill(confidence: Confidence): number {
  if (confidence === "high") return 100;
  if (confidence === "medium") return 66;
  return 33;
}

export function formatPct(value: number | null): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function formatEtaDays(value: number | null): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value}d`;
}

export function formatQty(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString("en-GB");
}
