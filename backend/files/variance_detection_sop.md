# Variance detection SOP

**Document ID:** MERCH-SOP-014
**Owner:** Intake Planning
**Review cycle:** Quarterly
**Last reviewed:** 2026-07-14

---

## 1. What counts as a variance

A variance is any difference between what a purchase order committed to and what the supplier has confirmed or delivered. Three variance classes are tracked independently, and a single PO may carry more than one at the same time.

### 1.1 Quantity variance

```
qty_variance_pct = (confirmed_qty - ordered_qty) / ordered_qty × 100
```

Measured on absolute value for tier assignment. Negative variance (under-supply) and positive variance (over-supply) share the same tier boundaries but route differently at V1 and above — see §3.

Where `confirmed_qty` is null, the PO is classified `AWAITING_CONFIRMATION` and **no variance tier is assigned**. Absence of confirmation is not a variance. It is a chase, and it is tracked separately on the supplier confirmation report.

### 1.2 Value variance

```
value_variance_pct = (confirmed_value - ordered_value) / ordered_value × 100
```

In practice, value variance that is not explained by quantity variance indicates a cost price movement, which is never amendable in place. Any value variance exceeding **2%** with no corresponding quantity variance is treated as a cost price exception and routed immediately to human review regardless of tier.

### 1.3 ETA variance

```
eta_variance_days = confirmed_eta - original_eta
```

Measured in calendar days, not working days. Positive values indicate a delay. Early delivery of more than 14 days is also flagged, as it creates warehouse capacity and cash-flow effects.

## 2. Severity tiers

Tier is assigned by taking the **highest** tier triggered across all three variance classes.

| Tier | Label | Quantity variance | ETA slip | Value at risk |
|---|---|---|---|---|
| **V0** | Nil | ≤ 2% | ≤ 3 days | — |
| **V1** | Low | 2.1% – 10% | 4 – 7 days | Under £25,000 |
| **V2** | Moderate | 10.1% – 25% | 8 – 21 days | £25,000 – £99,999 |
| **V3** | High | 25.1% – 50% | 22 – 45 days | £100,000 – £249,999 |
| **V4** | Critical | Over 50% | Over 45 days | £250,000 and above |

### 2.1 Compound variance rule

Where a PO carries **two or more concurrent V1 variances** across different classes, it is promoted to V2 and routed to human review. Two small problems on the same PO are not a small problem.

This promotion applies at V1 only. A PO carrying concurrent V2s is not promoted to V3 — it remains V2, because at V2 and above a human is already reviewing the whole PO in the round.

### 2.2 Channel override

Any variance of V1 or above on a PO with a **Wholesale allocation** is promoted one tier. Wholesale carries contractual delivery obligations that Retail does not, so the same shortfall has materially different consequences. A V1 quantity variance on a wholesale PO is handled as V2.

### 2.3 Season boundary override

Where a revised ETA falls outside the PO's season window, the PO is classified **V4 regardless of the size of the slip**. Stock arriving into the wrong season cannot be traded at full price and carries an immediate markdown provision.

## 3. Auto-action and human-review boundary

| Tier | Handling |
|---|---|
| **V0** | Auto-accepted. Written to the variance log. No notification. |
| **V1** | Auto-amended in place. Planner notified on the daily digest. No action required unless the planner objects within 48 hours. |
| **V2** | **Human review required.** Routed to the owning planner's exception queue. No system action taken until a decision is recorded. |
| **V3** | Human review required, plus mandatory notification to the sign-off authority for the value band. |
| **V4** | Human review required. **No auto-action of any kind is permitted**, including notifications to the supplier. Escalation is mandatory before any outbound communication. |

The auto-action boundary sits between V1 and V2. Nothing at V2 or above may be actioned, amended, split, cancelled or communicated to a supplier without a recorded human decision.

### 3.1 Positive variance handling

Over-delivery is not automatically benign. At V1 and above, positive quantity variance additionally requires a stock capacity check before acceptance, because unplanned intake displaces committed intake in the same receiving window. Over-delivery above 5% may not be auto-accepted even where the tier would otherwise permit it.

## 4. Data quality exclusions

The following conditions suppress tier assignment and route the PO to the data quality queue rather than the exception queue:

- `confirmed_qty` is null while status is not `AWAITING_CONFIRMATION`
- `eta` is null on a PO in `CONFIRMED` or later status
- `confirmed_qty` is zero on a PO not in `CANCELLED` status
- `value_gbp` is null or zero
- `parent_po_id` references a PO that does not exist or is itself a child

A PO in the data quality queue must not be given a recommendation. The underlying record is corrected first. Reasoning over a record known to be incomplete produces a confident answer to the wrong question.

## 5. Terminal statuses

POs in status `CANCELLED`, `CLOSED_SHORT` or `RECEIVED_COMPLETE` are excluded from variance detection. Variances discovered against a terminal PO are handled as a post-receipt claim under the supplier claims process, not as an amendment.

---

*Queries on tier assignment to Nadia Bergström, Intake Planning Lead — nadia.bergstrom@example-retail.co.uk, ext. 4417.*
