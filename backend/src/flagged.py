"""Build the flagged-PO list for the UI.

Reads synthetic_planner_queries.json, joins each PO from purchase_orders.json, and
runs the authoritative compute_variance_tier tool (no LLM/RAG) to produce a tier
badge and a one-line symptom summary per PO.
"""

from __future__ import annotations

import json
from typing import List, Optional

from .api_schemas import FlaggedPo, TierDisplay
from .tools import FILES_DIR, compute_variance_tier, get_purchase_order

QUERIES_PATH = FILES_DIR / "synthetic_planner_queries.json"

_TIER_WORDS = {0: "Clean", 1: "Minor", 2: "Material", 3: "Major", 4: "Critical"}


def _tier_display(tier: str) -> TierDisplay:
    """Map a 'Vn' tier code to a {number, word} display object."""
    try:
        number = int(tier.lstrip("V"))
    except (ValueError, AttributeError):
        number = 0
    return TierDisplay(number=number, word=_TIER_WORDS.get(number, "Clean"))


def _summary_line(
    qty_pct: Optional[float], eta_days: Optional[int], overrides: List[str]
) -> str:
    """Compose the '<symptom> · <symptom>' summary shown under each PO."""
    parts: List[str] = []
    if qty_pct is not None:
        rounded = round(qty_pct)
        if rounded < 0:
            parts.append(f"Short-ship {rounded}%")
        elif rounded > 0:
            parts.append(f"Over-delivery +{rounded}%")
    if eta_days is not None and eta_days > 0:
        parts.append(f"ETA +{eta_days}d")
    if "season_boundary_promoted_to_v4" in (overrides or []):
        parts.append("season slip")
    return " \u00b7 ".join(parts) if parts else "Within tolerance"


def _load_queries() -> List[dict]:
    """Load the synthetic planner queries."""
    return json.loads(QUERIES_PATH.read_text(encoding="utf-8"))["queries"]


def build_flagged_pos() -> List[FlaggedPo]:
    """Return one FlaggedPo per query, joined to its PO and deterministically tiered."""
    items: List[FlaggedPo] = []
    for entry in _load_queries():
        po_id = entry["po_id"]
        record = get_purchase_order.invoke({"po_id": po_id})
        if "error" in record:
            items.append(
                FlaggedPo(
                    po_id=po_id,
                    supplier="Unknown",
                    category="Unknown",
                    tier=None,
                    tier_display=TierDisplay(number=0, word="Clean"),
                    qty_variance_pct=None,
                    eta_variance_days=None,
                    summary_line="Record not found",
                    query=entry["query"],
                )
            )
            continue

        tier = compute_variance_tier.invoke({"po_record": record})
        items.append(
            FlaggedPo(
                po_id=po_id,
                supplier=record.get("supplier", "Unknown"),
                category=record.get("category", "Unknown"),
                tier=tier["tier"],
                tier_display=_tier_display(tier["tier"]),
                qty_variance_pct=tier["qty_variance_pct"],
                eta_variance_days=tier["eta_variance_days"],
                summary_line=_summary_line(
                    tier["qty_variance_pct"],
                    tier["eta_variance_days"],
                    tier["overrides_applied"],
                ),
                query=entry["query"],
            )
        )
    return items
