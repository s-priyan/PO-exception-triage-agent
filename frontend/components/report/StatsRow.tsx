import { TierResult } from "@/lib/types";
import { formatEtaDays, formatPct, formatQty } from "@/lib/format";

function Stat({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-slate-500">{label}</span>
      <span className={`text-lg font-semibold ${danger ? "text-rose-400" : "text-slate-100"}`}>
        {value}
      </span>
    </div>
  );
}

export function StatsRow({
  record,
  tier,
}: {
  record: Record<string, unknown> | null;
  tier: TierResult | null;
}) {
  const ordered = (record?.ordered_qty as number | undefined) ?? null;
  const confirmed = (record?.confirmed_qty as number | undefined) ?? null;
  return (
    <div className="flex gap-10 rounded-lg border border-slate-800 bg-slate-900/40 px-5 py-4">
      <Stat label="Ordered" value={formatQty(ordered)} />
      <Stat label="Confirmed" value={formatQty(confirmed)} />
      <Stat label="Variance" value={formatPct(tier?.qty_variance_pct ?? null)} danger />
      <Stat label="ETA" value={formatEtaDays(tier?.eta_variance_days ?? null)} />
    </div>
  );
}
