# Purchase order amendment policy

**Document ID:** MERCH-POL-004
**Owner:** Merchandising Operations
**Applies to:** All intake POs, Retail and Wholesale channels
**Current version:** 3.0

---

## 1. Purpose and scope

This policy governs what may be changed on a purchase order after it has been issued to a supplier, and what must instead be cancelled and re-raised as a new PO.

A purchase order is a commercial commitment. Amending one has cost, contractual and audit consequences, so amendments are permitted only within defined tolerances and with the sign-off appropriate to the value at risk.

This policy covers in-place amendment and cancel-and-re-raise. It does not cover sub-division into child POs (see MERCH-POL-006, *Child PO split rules*) or backorder handling (see MERCH-POL-007, *Backorder reconciliation*).

## 2. Amendable and non-amendable fields

| Field | Before dispatch | After dispatch (in transit) | After goods receipt |
|---|---|---|---|
| Ordered quantity | Amendable within tolerance | **Locked** | Locked |
| ETA / delivery date | Amendable | Amendable | N/A |
| Delivery destination | Amendable | Amendable | Locked |
| Cost price | **Never amendable** — cancel and re-raise | Locked | Locked |
| Supplier | **Never amendable** — cancel and re-raise | Locked | Locked |
| Channel allocation (Retail / Wholesale) | Amendable, subject to §6 | Locked | Locked |
| Season code | **Never amendable** — cancel and re-raise | Locked | Locked |

Once a supplier ASN has been issued, quantity is locked. The only remaining levers are the delivery date and the destination. A quantity discrepancy discovered after dispatch is a receipting matter, not an amendment.

## 3. Amendment triggers

An amendment may be initiated by:

- A supplier-confirmed quantity that differs from the ordered quantity
- A supplier-confirmed ETA that differs from the ordered ETA
- A planner-initiated change following a forecast revision
- A channel reallocation request from Wholesale

All amendments must be raised within **48 hours** of the triggering event and must carry a reason code.

## 4. Amendment thresholds

Quantity variance is calculated as:

```
qty_variance_pct = (confirmed_qty - ordered_qty) / ordered_qty × 100
```

**In-place amendment is permitted where absolute quantity variance is 15% or less.** Within this band the agreed cost price and any volume break remain valid, and no supplier re-confirmation is required.

Where absolute quantity variance exceeds 15%, the volume break underpinning the agreed cost price is no longer assured. The cost price must be re-agreed with the supplier before any amendment is applied. Because cost price is a non-amendable field (§2), this is effected by cancel-and-re-raise.

Positive variance (over-delivery) is treated symmetrically for the cost-price test, but any over-delivery above **5%** additionally requires explicit planner acceptance before receipt, regardless of cost-price impact.

ETA variance is measured in calendar days against the original confirmed ETA:

| ETA slip | Treatment |
|---|---|
| 0–3 days | No amendment required; log only |
| 4–14 days | In-place amendment, planner authority |
| 15–30 days | In-place amendment, Senior Merchandiser sign-off |
| Over 30 days | Cancel and re-raise, or split — see MERCH-POL-006 |

## 5. Sign-off authority by value band

Authority is determined by the **PO value at risk** — for a quantity reduction, the value of the units removed; for a full cancellation, the total PO value.

| Value at risk (GBP) | Sign-off required |
|---|---|
| Under £25,000 | Merch Planner (self-authorised) |
| £25,000 – £99,999 | Senior Merchandiser |
| £100,000 – £249,999 | Category Merchandising Manager |
| £250,000 and above | Merchandising Director |

Sign-off is required *before* the amendment is transmitted to the supplier, not retrospectively. Contact routing for each authority level is held in MERCH-POL-009, *Escalation matrix*.

## 6. Wholesale-specific constraints

Wholesale allocations are contractually committed and are not freely amendable.

- A wholesale allocation **cannot be reduced within 30 days** of the contracted delivery date without invoking the cancellation clause in the relevant partner agreement.
- Outside the 30-day window, wholesale allocations may be reduced by up to 10% without partner notification. Above 10%, the partner must be notified in writing before the amendment is applied.
- Where a shortfall affects a PO carrying both Retail and Wholesale allocation, and the wholesale contracted delivery falls within 30 days, the wholesale allocation is satisfied in full from received stock and the Retail allocation absorbs the entire shortfall.
- Reallocating units from Wholesale to Retail, or the reverse, is a channel amendment and requires Category Merchandising Manager sign-off irrespective of value.

## 7. Cancel-and-re-raise triggers — quick reference

Cancel the parent PO and raise a replacement where any of the following apply:

- Cost price has changed for any reason
- Supplier has changed
- Season code has changed, or the revised ETA falls outside the season window
- **Absolute quantity variance exceeds 10%**
- ETA slip exceeds 30 days and sub-division is not viable
- The PO was raised against a since-cancelled option or style

Where a PO is cancelled and re-raised, the replacement must reference the cancelled PO in its notes field, and the original must be closed with reason code `CXL-REPLACED` within 5 working days.

## 8. Audit requirements

Every amendment must record: the reason code, the value at risk, the authority who signed off, the policy clause relied upon, and the timestamp. Amendments applied without a recorded sign-off are reversed at month-end review.

---

## Revision history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2023-04-11 | Initial issue |
| 2.0 | 2024-09-02 | Added wholesale constraints (§6); introduced value bands |
| 2.3 | 2025-06-30 | ETA slip tiers revised following supplier performance review |
| 3.0 | 2026-01-19 | In-place amendment ceiling for quantity variance raised from 10% to 15% following the FY25 supplier tolerance review. Value bands uplifted. |
