import { TriageResponse } from "@/lib/types";
import { actionHeadline } from "@/lib/format";
import { RecommendedActionHeader } from "./RecommendedActionHeader";
import { StatsRow } from "./StatsRow";
import { PolicyCitations } from "./PolicyCitations";
import { ConfidenceCard } from "./ConfidenceCard";
import { EscalationCard } from "./EscalationCard";
import { ExceptionTypeChips } from "./ExceptionTypeChips";
import { ActionButtons } from "./ActionButtons";

export function Report({ result }: { result: TriageResponse }) {
  const { triage, recommendation, citations } = result;
  const poPrefix = triage.po_id ? `${triage.po_id}: ` : "";
  const summary = `${poPrefix}${actionHeadline(
    recommendation.recommended_action,
  )} — ${recommendation.rationale}`;

  return (
    <div className="grid grid-cols-[1fr_18rem] gap-6 p-6">
      <div className="flex flex-col gap-5">
        <RecommendedActionHeader recommendation={recommendation} tier={triage.tier} />
        <StatsRow record={triage.po_record} tier={triage.tier} />
        <PolicyCitations citations={citations} />
      </div>
      <div className="flex flex-col gap-4">
        <ConfidenceCard confidence={recommendation.confidence} citations={citations} />
        <EscalationCard role={recommendation.escalation_target_role} />
        <ExceptionTypeChips types={triage.exception_types} />
        <ActionButtons summary={summary} />
      </div>
    </div>
  );
}
