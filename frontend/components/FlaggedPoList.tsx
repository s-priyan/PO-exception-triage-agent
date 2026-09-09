"use client";

import { useMemo, useState } from "react";
import { FlaggedPo } from "@/lib/types";
import { PoRow } from "./PoRow";

export function FlaggedPoList({
  items,
  selectedPoId,
  onSelect,
}: {
  items: FlaggedPo[];
  selectedPoId: string | null;
  onSelect: (po: FlaggedPo) => void;
}) {
  const [filter, setFilter] = useState("");

  const filtered = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return items;
    return items.filter(
      (po) =>
        po.po_id.toLowerCase().includes(needle) ||
        po.supplier.toLowerCase().includes(needle),
    );
  }, [items, filter]);

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col gap-3 border-r border-slate-800 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Flagged POs</h2>
        <span className="text-xs text-slate-400">{items.length}</span>
      </div>
      <input
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
        placeholder="Filter by PO or supplier"
        className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-slate-500 focus:outline-none"
      />
      <div className="flex flex-col gap-1.5 overflow-y-auto">
        {filtered.map((po) => (
          <PoRow
            key={po.po_id}
            po={po}
            selected={po.po_id === selectedPoId}
            onSelect={onSelect}
          />
        ))}
      </div>
    </aside>
  );
}
