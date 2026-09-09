import { Citation, Confidence } from "@/lib/types";
import { confidenceFill } from "@/lib/format";

export function ConfidenceCard({
  confidence,
  citations,
}: {
  confidence: Confidence;
  citations: Citation[];
}) {
  const note =
    citations.length > 0
      ? `${citations.length} cited clause${citations.length > 1 ? "s" : ""} matched.`
      : "No policy clause was cited.";
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Confidence
      </h3>
      <p className="mt-1 text-xl font-bold capitalize text-slate-100">{confidence}</p>
      <div className="mt-2 h-1.5 w-full rounded-full bg-slate-800">
        <div
          className="h-1.5 rounded-full bg-blue-500"
          style={{ width: `${confidenceFill(confidence)}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-slate-400">{note}</p>
    </div>
  );
}
