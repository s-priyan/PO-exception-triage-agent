export type TierWord = "Clean" | "Minor" | "Material" | "Major" | "Critical";

export interface TierDisplay {
  number: number;
  word: TierWord;
}

export interface FlaggedPo {
  po_id: string;
  supplier: string;
  category: string;
  tier: string | null;
  tier_display: TierDisplay;
  qty_variance_pct: number | null;
  eta_variance_days: number | null;
  summary_line: string;
  query: string;
}

export interface FlaggedPosResponse {
  count: number;
  items: FlaggedPo[];
}

export type ExceptionType =
  | "quantity_variance_short"
  | "quantity_variance_over"
  | "eta_slip"
  | "partial_delivery"
  | "season_boundary_risk"
  | "wholesale_constraint"
  | "parent_child_context";

export type RecommendedAction =
  | "amend"
  | "split_child_po"
  | "firm_planned_order"
  | "raise_backorder"
  | "escalate";

export type Confidence = "high" | "medium" | "low";
export type HaltReason = "unresolved_po" | "data_quality" | "terminal_status";

export interface TierResult {
  tier: string;
  qty_variance_pct: number | null;
  eta_variance_days: number | null;
  value_at_risk_gbp: number | null;
  overrides_applied: string[];
  validation: { passed: boolean; failures: string[] };
}

export interface TriageOutput {
  po_id: string | null;
  halt: HaltReason | null;
  planner_question: string;
  po_record: Record<string, unknown> | null;
  forecast: Record<string, unknown> | null;
  tier: TierResult | null;
  exception_types: ExceptionType[];
  queries: string[];
}

export interface Recommendation {
  po_id: string | null;
  recommended_action: RecommendedAction;
  rationale: string;
  citations: string[];
  confidence: Confidence;
  escalation_target_role: string | null;
}

export interface Citation {
  code: string;
  section: string;
  title: string | null;
  quote: string | null;
}

export interface TriageResponse {
  triage: TriageOutput;
  recommendation: Recommendation;
  citations: Citation[];
  halt: HaltReason | null;
}
