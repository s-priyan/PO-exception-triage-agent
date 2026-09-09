import { ExceptionType } from "@/lib/types";
import { EXCEPTION_LABELS } from "@/lib/format";
import { Badge } from "../ui/Badge";

export function ExceptionTypeChips({ types }: { types: ExceptionType[] }) {
  if (types.length === 0) return null;
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Exception types
      </h3>
      <div className="flex flex-wrap gap-2">
        {types.map((type) => (
          <Badge key={type} className="bg-slate-800 text-slate-200">
            {EXCEPTION_LABELS[type]}
          </Badge>
        ))}
      </div>
    </div>
  );
}
