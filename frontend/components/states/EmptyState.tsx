export function EmptyState({ poId }: { poId: string | null }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-slate-500">
      <p className="text-lg font-medium text-slate-300">
        {poId ? `${poId} selected` : "Select a flagged PO"}
      </p>
      <p className="text-sm">Ask a question to run triage and see the recommendation.</p>
    </div>
  );
}
