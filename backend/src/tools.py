"""Triage tools for Agent 1: data access plus authoritative variance tiering.

compute_variance_tier encodes MERCH-SOP-014 (Variance detection SOP). The agent
never reasons about policy; it calls this tool and copies the result verbatim.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from langchain_core.tools import tool

from .schemas import TierResult, ValidationResult

FILES_DIR = Path(__file__).resolve().parents[1] / "files"
PURCHASE_ORDERS_PATH = FILES_DIR / "purchase_orders.json"
FORECASTS_PATH = FILES_DIR / "forecasts.json"

# Statuses at or beyond supplier confirmation, used by the data-quality checks.
CONFIRMED_OR_LATER = {
    "CONFIRMED",
    "IN_TRANSIT",
    "PART_RECEIVED",
    "RECEIVED_COMPLETE",
    "SPLIT_PARENT",
    "CLOSED_SHORT",
}

_purchase_orders_file: Optional[dict] = None
_forecasts_file: Optional[dict] = None


def _load_purchase_orders() -> dict:
    """Load and cache the purchase orders file."""
    global _purchase_orders_file
    if _purchase_orders_file is None:
        _purchase_orders_file = json.loads(
            PURCHASE_ORDERS_PATH.read_text(encoding="utf-8")
        )
    return _purchase_orders_file


def _load_forecasts() -> dict:
    """Load and cache the forecasts file."""
    global _forecasts_file
    if _forecasts_file is None:
        _forecasts_file = json.loads(FORECASTS_PATH.read_text(encoding="utf-8"))
    return _forecasts_file


def _po_index() -> Dict[str, dict]:
    """Return an index of PO records keyed by po_id."""
    return {rec["po_id"]: rec for rec in _load_purchase_orders()["purchase_orders"]}


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO date string, returning None for empty input."""
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d")


def _qty_variance_pct(record: dict) -> Optional[float]:
    """Signed quantity variance percentage (MERCH-SOP-014 section 1.1)."""
    ordered = record.get("ordered_qty")
    confirmed = record.get("confirmed_qty")
    if not ordered or confirmed is None:
        return None
    # Early return keeps the null-confirmation case out of the arithmetic.
    return round((confirmed - ordered) / ordered * 100, 4)


def _eta_variance_days(record: dict) -> Optional[int]:
    """Signed ETA variance in calendar days (MERCH-SOP-014 section 1.3)."""
    original = _parse_date(record.get("original_eta"))
    revised = _parse_date(record.get("eta"))
    if original is None or revised is None:
        return None
    return (revised - original).days


def _value_at_risk_gbp(record: dict) -> Optional[float]:
    """Value at risk in GBP: absolute unit gap valued at unit cost."""
    ordered = record.get("ordered_qty")
    confirmed = record.get("confirmed_qty")
    unit_cost = record.get("unit_cost_gbp")
    if ordered is None or confirmed is None or unit_cost is None:
        return None
    return round(abs(ordered - confirmed) * unit_cost, 2)


def _qty_tier(pct: Optional[float]) -> int:
    """Quantity variance tier index from the absolute percentage."""
    if pct is None:
        return 0
    magnitude = abs(pct)
    if magnitude <= 2:
        return 0
    if magnitude <= 10:
        return 1
    if magnitude <= 25:
        return 2
    if magnitude <= 50:
        return 3
    return 4


def _eta_tier(days: Optional[int]) -> int:
    """ETA slip tier index from the positive day count."""
    if days is None or days <= 3:
        return 0
    if days <= 7:
        return 1
    if days <= 21:
        return 2
    if days <= 45:
        return 3
    return 4


def _value_tier(value_at_risk: Optional[float]) -> int:
    """Value-at-risk tier index from the GBP band."""
    if not value_at_risk or value_at_risk <= 0:
        return 0
    if value_at_risk < 25000:
        return 1
    if value_at_risk < 100000:
        return 2
    if value_at_risk < 250000:
        return 3
    return 4


def _eta_outside_season(record: dict) -> bool:
    """True when the revised ETA falls outside the season window."""
    revised = _parse_date(record.get("eta"))
    if revised is None:
        return False
    window = _load_purchase_orders()["meta"]["season_window"]
    start = _parse_date(window["start"])
    end = _parse_date(window["end"])
    return revised < start or revised > end


def _apply_overrides(
    base_tier: int, class_tiers: List[int], record: dict
) -> Tuple[int, List[str]]:
    """Apply the SOP overrides to the base tier (MERCH-SOP-014 section 2)."""
    overrides: List[str] = []
    final_tier = base_tier

    # Section 2.1: two or more concurrent V1 variances promote to V2 (V1 only).
    if final_tier == 1 and sum(1 for tier in class_tiers if tier == 1) >= 2:
        final_tier = 2
        overrides.append("compound_variance_v1_promoted_to_v2")

    # Section 2.2: a wholesale allocation at V1 or above promotes one tier.
    if final_tier >= 1 and (record.get("wholesale_alloc") or 0) > 0:
        final_tier = min(final_tier + 1, 4)
        overrides.append("wholesale_channel_promoted_one_tier")

    # Section 2.3: a revised ETA outside the season window is V4 regardless.
    if _eta_outside_season(record):
        if final_tier != 4:
            overrides.append("season_boundary_promoted_to_v4")
        final_tier = 4

    return final_tier, overrides


def _validate(record: dict) -> ValidationResult:
    """Run the SOP data-quality exclusions (MERCH-SOP-014 section 4)."""
    failures: List[str] = []
    status = record.get("status")
    confirmed = record.get("confirmed_qty")
    eta = record.get("eta")
    value = record.get("value_gbp")
    parent = record.get("parent_po_id")

    if confirmed is None and status != "AWAITING_CONFIRMATION":
        failures.append("confirmed_qty is null while status is not AWAITING_CONFIRMATION")
    if eta is None and status in CONFIRMED_OR_LATER:
        failures.append("eta is null on a PO in CONFIRMED or later status")
    if confirmed == 0 and status != "CANCELLED":
        failures.append("confirmed_qty is zero on a PO not in CANCELLED status")
    if value is None or value == 0:
        failures.append("value_gbp is null or zero")
    if parent is not None:
        parent_record = _po_index().get(parent)
        if parent_record is None:
            failures.append("parent_po_id references a PO that does not exist")
        elif parent_record.get("parent_po_id") is not None:
            failures.append("parent_po_id references a PO that is itself a child")

    return ValidationResult(passed=not failures, failures=failures)


@tool
def get_purchase_order(po_id: str) -> dict:
    """Return the purchase order record for po_id, or an error object if not found."""
    for record in _load_purchase_orders()["purchase_orders"]:
        if record["po_id"] == po_id:
            return record
    return {"error": f"purchase order not found: {po_id}"}


@tool
def get_forecast(po_id: str) -> dict:
    """Return the forecast record for the PO's SKU, matched by po_id, or an error object."""
    for record in _load_forecasts()["forecasts"]:
        if record["po_id"] == po_id:
            return record
    return {"error": f"forecast not found: {po_id}"}


@tool
def compute_variance_tier(po_record: dict) -> dict:
    """Return the authoritative variance assessment for a PO record.

    Encodes MERCH-SOP-014. Output keys: tier (V0-V4), qty_variance_pct,
    eta_variance_days, value_at_risk_gbp, overrides_applied and validation. This
    tool is the single source of truth for the tier, percentages and day counts;
    never recompute them by hand.
    """
    qty_pct = _qty_variance_pct(po_record)
    eta_days = _eta_variance_days(po_record)
    value_at_risk = _value_at_risk_gbp(po_record)

    class_tiers = [_qty_tier(qty_pct), _eta_tier(eta_days), _value_tier(value_at_risk)]
    final_tier, overrides = _apply_overrides(max(class_tiers), class_tiers, po_record)

    result = TierResult(
        tier=f"V{final_tier}",
        qty_variance_pct=qty_pct,
        eta_variance_days=eta_days,
        value_at_risk_gbp=value_at_risk,
        overrides_applied=overrides,
        validation=_validate(po_record),
    )
    return result.model_dump()


TRIAGE_TOOLS = [get_purchase_order, get_forecast, compute_variance_tier]
