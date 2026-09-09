# Backorder reconciliation

**Document ID:** MERCH-POL-007
**Owner:** Merchandising Operations / Customer Operations (joint)
**Applies to:** Retail channel. Wholesale shortfalls follow the partner agreement, not this policy.

---

## 1. When a backorder is raised

A backorder records demand that has been accepted but cannot be fulfilled from current stock. It is the correct action where a shortfall is too small to justify a child PO but too material to write off.

| Condition | Action |
|---|---|
| Shortfall under 10% of ordered qty | **Raise backorder** |
| Shortfall 10%+ but balance below child PO minimum size (200 units / £5,000) | **Raise backorder** |
| Shortfall 10%+ and balance above minimum size | Split — see MERCH-POL-006 |
| Balance ETA unconfirmed | **Do not raise.** A backorder with no date cannot be communicated to a customer. |
| SKU has been discontinued or the option cancelled | Do not raise. Close short. |

A backorder may only be raised against a **confirmed** supplier commitment. Raising one against an expected-but-unconfirmed balance transfers supplier risk onto the customer, which is not ours to transfer.

## 2. Maximum permissible delay

Measured from the date the customer's order was placed to the confirmed availability date.

| Channel | Maximum permissible delay |
|---|---|
| Retail — standard lines | 21 calendar days |
| Retail — pre-order and drop lines | 35 calendar days |
| Wholesale | 10 calendar days (contractual; see partner agreement) |

Beyond the maximum, the backorder is **auto-cancelled** and the customer refunded in full. The planner is notified but no planner decision is required — this is a hard limit, not a tolerance.

### 2.1 Season boundary constraint

A backorder may **not** cross a season boundary, regardless of the day count. An AW26 backorder cannot fulfil into SS27 even where the delay is within 21 days, because the stock will arrive against a season that is already in markdown.

Where a confirmed availability date falls outside the season window, the backorder is cancelled at the point of detection and the balance is either cancelled with the supplier or repurposed as clearance intake. Repurposing requires Senior Merchandiser sign-off.

## 3. Customer communication thresholds

Communication is triggered by the delay length, and is issued by Customer Operations rather than by Merchandising. Merchandising's obligation is to provide a confirmed date; the messaging itself is not a merchandising action.

| Delay from original promise | Communication |
|---|---|
| 1 – 3 days | None. Absorbed within standard delivery windows. |
| 4 – 10 days | Proactive notification with revised date. |
| 11 – 21 days | Notification with revised date **and** a no-penalty cancellation option. |
| Over 21 days | Auto-cancellation and full refund. Apology issued. |

Where a revised date is itself missed, the customer is offered cancellation immediately regardless of the day count. A second slip is not communicated as a further delay.

**A backorder must never be communicated to a customer before the supplier balance is confirmed.** Where confirmation is pending, the order remains unallocated and no promise date is issued.

## 4. Allocation priority

Where received stock is insufficient to clear all open backorders on a SKU, allocation runs in this order:

1. Backorders already communicated to the customer with a firm date
2. Backorders by order date, oldest first
3. New demand (front-of-site availability)

New demand does not take priority over an existing backorder, even where doing so would trade at a better margin. Publishing availability while backorders are outstanding on the same SKU is a specific breach of this policy.

## 5. Partial fulfilment

A backorder may be partially fulfilled **once**. The residual either clears on the next receipt or is cancelled — it may not be split a second time.

Where partial fulfilment would leave a residual below 20 units, the backorder is fulfilled in full from safety stock if available, or cancelled entirely. Splitting a customer's order into a third shipment costs more in fulfilment and contact-centre volume than the units are worth.

## 6. Reconciliation and closure

A backorder reaches terminal status when one of the following occurs:

- **Fulfilled** — received quantity has cleared the committed demand
- **Expired** — maximum permissible delay reached, auto-cancelled
- **Cancelled by customer** — under the §3 cancellation option
- **Cancelled by planner** — supplier balance cancelled or season boundary reached

Every backorder must be reconciled against its source PO at closure. An unreconciled backorder holds phantom demand in the forecast and will inflate the next replenishment calculation for the same SKU.

Open backorders are reviewed weekly. Any backorder open for more than 14 days without a confirmed date is escalated, irrespective of its size or value.

## 7. Interaction with child POs

Where a parent PO has been split, backorders attach to the **child** carrying the balance, not to the parent. Attaching to the parent breaks the fulfilment link, because the parent is receipted and closed against what already arrived.

Where a child PO is subsequently cancelled, every backorder attached to it is cancelled in the same action. Backorders are never silently reassigned to another PO.
