export function EscalationCard({ role }: { role: string | null }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        If you need to escalate
      </h3>
      <p className="mt-1 text-sm font-semibold text-slate-100">
        {role ?? "No escalation required"}
      </p>
      {role && (
        <p className="mt-1 text-xs text-slate-400">
          Role only — no personal contact data.
        </p>
      )}
    </div>
  );
}
