import { Recommendation, TierResult, TierWord } from "@/lib/types";
import { actionHeadline } from "@/lib/format";
import { TierBadge } from "../TierBadge";

const TIER_WORDS: TierWord[] = ["Clean", "Minor", "Material", "Major", "Critical"];

export function RecommendedActionHeader({
  recommendation,
  tier,
}: {
  recommendation: Recommendation;
  tier: TierResult | null;
}) {
  const number = tier ? Number(tier.tier.replace("V", "")) : 0;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Recommended action
        </span>
        {tier && (
          <TierBadge number={number} word={TIER_WORDS[number] ?? "Clean"} withWord />
        )}
      </div>
      <h1 className="text-2xl font-bold text-slate-50">
        {actionHeadline(recommendation.recommended_action)}
      </h1>
      <p className="text-sm leading-relaxed text-slate-300">{recommendation.rationale}</p>
    </div>
  );
}
