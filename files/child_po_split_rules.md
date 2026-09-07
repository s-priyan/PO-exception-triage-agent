# Child PO split rules

**Document ID:** MERCH-POL-006
**Owner:** Merchandising Operations
**Applies to:** Partial receipts and split-delivery confirmations, all channels

---

## 1. What a child PO is for

A child PO carries the undelivered balance of a parent PO on its own delivery date, so that the parent can be receipted and closed against what actually arrived.

Without a split, the outstanding balance continues to sit against the parent's original ETA. Stock cover, intake phasing and open-to-buy all read from that date, so every downstream number is wrong for as long as the balance is misdated. Splitting is a data hygiene action as much as a commercial one.

Splitting does **not** commit the supplier to anything new. It records a revised expectation. Where the balance is genuinely at risk, the correct action is cancellation, not a split that keeps a dead balance alive on the books.

## 2. When to split

| Condition | Action |
|---|---|
| Shortfall ≥ 25% of ordered qty **and** balance ETA more than 14 days after parent ETA | **Split — mandatory** |
| Shortfall 10% – 24.9% **and** balance ETA more than 21 days after parent ETA | Split — planner discretion |
| Shortfall 10% – 24.9% **and** balance ETA within 21 days | Do not split. Hold parent open. |
| Shortfall under 10% | Do not split. Raise backorder per MERCH-POL-007. |
| Balance ETA unknown or unconfirmed by supplier | **Do not split.** Chase confirmation first. |
| Balance falls outside the parent's season window | Do not split. Cancel the balance. |

A mandatory split must be raised within **48 hours** of goods receipt. The 48-hour clock starts at receipt, not at the point the discrepancy is noticed.

## 3. Sizing rules

A child PO must be viable in its own right:

- **Minimum size:** 200 units **or** £5,000 value, whichever is lower
- **Maximum children per parent:** 3
- A balance below the minimum size is not split. It is closed short and, if demand supports it, backordered.
- A parent already carrying 3 children may not be split again. A fourth balance is an escalation, not an amendment — the supplier relationship is the problem at that point, not the PO.

Child POs inherit from the parent: supplier, cost price, season code, style and SKU.

Child POs do **not** inherit: ETA, channel allocation, or sign-off. Each must be restated explicitly on the child. Inheriting a channel allocation silently is the most common cause of wholesale over-commitment.

## 4. Naming and linkage

Children are suffixed sequentially against the parent:

```
PO-88412        parent
PO-88412-C1     first child
PO-88412-C2     second child
```

The `parent_po_id` field on every child must reference the parent. A child may not itself be a parent — chained splits are not permitted. Where a child's balance is itself short-delivered, the child is closed short and the residual backordered.

The parent remains **open** until every child has reached a terminal status. Closing a parent with live children orphans the balance and removes it from stock cover.

## 5. Retail and wholesale split logic

Where the parent carries allocation across both channels, the received quantity is apportioned before the child is sized.

**Rule 5.1 — Wholesale inside 30 days.** Where the wholesale contracted delivery date falls within 30 days of receipt, the wholesale allocation is satisfied **in full** from received stock. Retail absorbs the entire shortfall. This is not a commercial judgement; it follows from the contractual position set out in MERCH-POL-004 §6.

**Rule 5.2 — Wholesale outside 30 days.** Where the contracted delivery is more than 30 days out, the shortfall is pro-rated across channels in proportion to original allocation, and the partner is notified where their reduction exceeds 10%.

**Rule 5.3 — Channel of the child.** The child PO carries only the channels that were shorted. Where Retail absorbed the whole shortfall under 5.1, the child is Retail-only.

**Rule 5.4 — No cross-channel recovery.** A child PO raised against a Retail shortfall may not be reallocated to Wholesale on arrival without a channel amendment and Category Merchandising Manager sign-off.

### Worked apportionment

Parent: 4,000 units, 3,400 Retail / 600 Wholesale. Received 2,600. Wholesale contracted delivery in 19 days.

Rule 5.1 applies. Wholesale takes 600 in full. Retail receives 2,000 against 3,400. Shortfall of 1,400 is 35% of the parent — mandatory split. Child is 1,400 units, Retail-only.

## 6. Demand test before splitting

A split commits warehouse capacity and open-to-buy to a balance arriving late in the season. Before raising a discretionary split, check the forecast position for the SKU:

- **Demand index at or above 100** and weeks cover below target — split, the balance is worth recovering
- **Demand index below 85** — do not split. Cancel the balance and redeploy the open-to-buy.
- **Demand index 85–99** — planner judgement; document the reasoning on the amendment

This test does not apply to mandatory splits under §2, which are raised for data accuracy regardless of the demand position. It also does not apply to wholesale balances, which are contractually owed irrespective of the retail demand signal.

## 7. What a split does not fix

Splitting resolves the dating of the balance. It does not resolve:

- The gap in the trading plan created by short intake
- Any markdown provision arising from late arrival
- Size-curve damage where the shortfall is concentrated in volume sizes

These are separate actions and must be raised alongside the split, not treated as absorbed by it.

---

*For supplier-side split confirmations, the intake coordination contact for Anadolu Tekstil is Emre Yıldız (mob. +90 532 447 0912). All other supplier contacts are held in the escalation matrix.*
