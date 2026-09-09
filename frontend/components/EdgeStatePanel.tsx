import { TriageResponse } from "@/lib/types";
import { formatEtaDays, formatPct, formatQty } from "@/lib/format";
import { EscalationCard } from "./report/EscalationCard";

const HALT_LABELS: Record<string, string> = {
  data_quality: "Data-quality failure",
  terminal_status: "Terminal status",
  unresolved_po: "PO could not be resolved",
};

export function EdgeStatePanel({ result }: { result: TriageResponse }) {
  const { triage, recommendation } = result;
  const failures = triage.tier?.validation.failures ?? [];
  const haltKey = result.halt ?? "unresolved_po";

  return (
    <div className="grid grid-cols-[1fr_18rem] gap-6 p-6">
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-amber-500">
            Can't auto-recommend
          </span>
          <h1 className="text-2xl font-bold text-slate-50">{HALT_LABELS[haltKey]}</h1>
          <p className="text-sm leading-relaxed text-slate-300">
            {recommendation.rationale}
          </p>
        </div>

        {failures.length > 0 && (
          <ul className="list-inside list-disc rounded-lg border border-amber-900/50 bg-amber-950/20 p-4 text-sm text-amber-200">
            {failures.map((failure) => (
              <li key={failure}>{failure}</li>
            ))}
          </ul>
        )}

        <div className="flex gap-10 rounded-lg border border-slate-800 bg-slate-900/40 px-5 py-4">
          <Fact label="Ordered" value={formatQty((triage.po_record?.ordered_qty as number | undefined) ?? null)} />
          <Fact
            label="Confirmed"
            value={formatQty((triage.po_record?.confirmed_qty as number | undefined) ?? null)}
          />
          <Fact label="Variance" value={formatPct(triage.tier?.qty_variance_pct ?? null)} />
          <Fact label="ETA" value={formatEtaDays(triage.tier?.eta_variance_days ?? null)} />
        </div>
      </div>
      <div className="flex flex-col gap-4">
        <EscalationCard role={recommendation.escalation_target_role} />
      </div>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-slate-500">{label}</span>
      <span className="text-lg font-semibold text-slate-100">{value}</span>
    </div>
  );
}
