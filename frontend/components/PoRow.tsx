import { FlaggedPo } from "@/lib/types";
import { TierBadge } from "./TierBadge";

export function PoRow({
  po,
  selected,
  onSelect,
}: {
  po: FlaggedPo;
  selected: boolean;
  onSelect: (po: FlaggedPo) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(po)}
      className={`w-full rounded-lg border px-3 py-2.5 text-left transition ${
        selected
          ? "border-rose-500/70 bg-slate-800/80"
          : "border-transparent bg-slate-900/40 hover:bg-slate-800/50"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-100">{po.po_id}</span>
        <TierBadge number={po.tier_display.number} word={po.tier_display.word} />
      </div>
      <p className="mt-1 text-xs text-slate-400">{po.summary_line}</p>
    </button>
  );
}
