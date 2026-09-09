import { Citation } from "@/lib/types";

export function PolicyCitations({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Policy citations
      </h3>
      <div className="flex flex-col gap-2">
        {citations.map((citation, index) => (
          <div
            key={`${citation.code}-${citation.section}-${index}`}
            className="rounded-lg border border-slate-800 bg-slate-900/40 p-4"
          >
            <p className="text-sm font-semibold text-slate-200">
              {`${citation.code} ${citation.section}`.trim()}
              {citation.title ? (
                <>
                  {" — "}
                  <span>{citation.title}</span>
                </>
              ) : null}
            </p>
            {citation.quote && (
              <p className="mt-1 text-xs italic leading-relaxed text-slate-400">
                “{citation.quote}”
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
