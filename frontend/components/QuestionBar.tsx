export function QuestionBar({
  value,
  onChange,
  onAsk,
  loading,
}: {
  value: string;
  onChange: (value: string) => void;
  onAsk: () => void;
  loading: boolean;
}) {
  const disabled = loading || value.trim().length === 0;
  return (
    <div className="flex items-center gap-3 border-b border-slate-800 p-4">
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !disabled) onAsk();
        }}
        placeholder="Ask about the selected PO…"
        aria-label="Question about the selected PO"
        className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-slate-500 focus:outline-none"
      />
      <button
        type="button"
        onClick={onAsk}
        disabled={disabled}
        className="rounded-md bg-blue-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading ? "Asking…" : "Ask"}
      </button>
    </div>
  );
}
