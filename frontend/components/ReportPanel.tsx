import { TriageResponse } from "@/lib/types";
import { Report } from "./report/Report";
import { EdgeStatePanel } from "./EdgeStatePanel";
import { EmptyState } from "./states/EmptyState";
import { ReportSkeleton } from "./states/ReportSkeleton";
import { ErrorState } from "./states/ErrorState";

export type ReportPhase = "empty" | "loading" | "done" | "error";

export function ReportPanel({
  phase,
  result,
  error,
  selectedPoId,
  onRetry,
}: {
  phase: ReportPhase;
  result?: TriageResponse;
  error?: string;
  selectedPoId: string | null;
  onRetry: () => void;
}) {
  if (phase === "loading") return <ReportSkeleton />;
  if (phase === "error") {
    return <ErrorState message={error ?? "Something went wrong."} onRetry={onRetry} />;
  }
  if (phase === "done" && result) {
    return result.halt ? <EdgeStatePanel result={result} /> : <Report result={result} />;
  }
  return <EmptyState poId={selectedPoId} />;
}
