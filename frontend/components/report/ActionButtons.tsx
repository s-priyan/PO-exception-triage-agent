"use client";

export function ActionButtons({ summary }: { summary: string }) {
  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={() => navigator.clipboard?.writeText(summary)}
        className="rounded-md border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
      >
        Copy summary
      </button>
      <button
        type="button"
        disabled
        title="ERP integration not available in this demo"
        className="rounded-md border border-slate-800 px-4 py-2 text-sm text-slate-500"
      >
        Open PO in ERP
      </button>
    </div>
  );
}
