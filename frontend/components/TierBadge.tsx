import { Badge } from "./ui/Badge";

const TIER_CLASSES: Record<number, string> = {
  0: "bg-slate-700 text-slate-200",
  1: "bg-slate-600 text-slate-100",
  2: "bg-rose-600/90 text-white",
  3: "bg-rose-700 text-white",
  4: "bg-red-800 text-white",
};

export function TierBadge({
  number,
  word,
  withWord = false,
}: {
  number: number;
  word: string;
  withWord?: boolean;
}) {
  const label = withWord ? `TIER ${number} · ${word.toUpperCase()}` : `TIER ${number}`;
  return <Badge className={TIER_CLASSES[number] ?? TIER_CLASSES[0]}>{label}</Badge>;
}
