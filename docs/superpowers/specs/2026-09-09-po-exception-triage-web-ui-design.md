# PO Exception Triage — Web UI — Design

- **Date:** 2026-09-09
- **Status:** Approved (design); pending spec review
- **Topic:** React/Next.js front end + FastAPI wrapper for the existing LangGraph triage agent

## 1. Context & problem

The backend (`backend/`) is a two-stage LangGraph agent (Agent 1 = facts/triage, Agent 2
= grounded recommendation) that is currently **CLI-only** (`main.py`). A merchandising
planner needs a web UI to:

1. See the **flagged POs** drawn from `backend/files/synthetic_planner_queries.json`.
2. Click a PO — which shows **no report yet**, only an empty state.
3. Ask a question — which runs the live agent and renders the recommendation exactly as
   in the wireframe (`frontend/front-end-ui.png`).

The wireframe is **illustrative**: its numbers, its "14" count, its PO ids
(PO-88391, etc.), and its numeric `0.82` confidence do not literally match the data or
the schema. The UI is built against the **real** backend contract, not the mock numbers.

## 2. Goals / non-goals

**Goals**

- Full-stack: a thin FastAPI wrapper over the existing graph + a Next.js dashboard.
- Faithful to the backend schemas (`TriageOutput`, `Recommendation`) and to the SOPs.
- Handle the deliberate edge-case POs (data-quality, terminal, unresolved) honestly.

**Non-goals (YAGNI)**

- Auth, real ERP integration ("Open PO in ERP" is a stub), response streaming,
  pagination, persistence, multi-question history.

## 3. Decisions

| # | Decision |
|---|----------|
| Integration | Full-stack. New `backend/api.py` (FastAPI) reuses `prewarm()` + `build_triage_graph()`; Next.js calls it. |
| Flagged list | Lightweight `GET /flagged-pos`, **deterministic tiering only** (no LLM/RAG), reusing `compute_variance_tier`. |
| Response UX | Single `POST /triage` returns everything at once; UI shows a report-shaped **skeleton** while waiting. |
| Confidence | **Categorical** (high/medium/low) → labeled bar. No fabricated numeric score. |
| Halts | **Dedicated edge-state panel** for `data_quality` / `terminal_status` / `unresolved_po`. |
| Citations | Backend **resolves** each `"DOC.md §n"` reference to `{code, section, title, quote}` from the SOP markdown. |
| FE structure | Single-page dashboard (one route, client-managed state). |
| Prefill | Clicking a PO selects it, shows the empty state, and prefills the question input with that PO's synthetic query (editable). |
| Stack | Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui + lucide icons; dark theme. |

## 4. Architecture

```
frontend/  (Next.js App Router, TS, Tailwind + shadcn/ui)
   └── HTTP →  backend/api.py  (FastAPI)
                    ├── prewarm()             # once, on startup (lifespan)
                    ├── build_triage_graph()  # reused per /triage call
                    └── files/*.json + SOP *.md   (unchanged source of truth)
```

- `prewarm()` runs once via FastAPI lifespan so the Harrier model + Chroma index load a
  single time; the compiled graph is built once and reused.
- CORS restricted to the Next dev origin (configurable).
- `OPENAI_API_KEY` stays in `backend/.env` only. The frontend holds **no** secrets.

## 5. Backend API contract

### 5.1 `GET /flagged-pos`

Deterministic, no LLM/RAG. Reads `synthetic_planner_queries.json`, joins
`purchase_orders.json` by `po_id`, runs `compute_variance_tier` on each record.

Response: `{ "count": <int>, "items": FlaggedPo[] }` where

```jsonc
FlaggedPo = {
  "po_id": "PO-88405",
  "supplier": "Anadolu Tekstil",
  "category": "Womenswear",
  "tier": "V2",
  "tier_display": { "number": 2, "word": "Material" },
  "qty_variance_pct": -12.0,      // null when not computable
  "eta_variance_days": 9,          // null when not computable
  "summary_line": "Short-ship -12% · ETA +9d",
  "query": "PO-88405 has come in short ... what should I do about it?"
}
```

- `count` = real length of the queries file (13), not the wireframe's "14".
- `summary_line` is derived (see §6). All 13 queried PO ids exist in
  `purchase_orders.json`, so every row joins; a missing join (if the data changes later)
  degrades gracefully to a reference-only row with `tier = null`.
- Data-quality POs (e.g. PO-88416, missing ETA) still compute a deterministic tier here;
  their data-quality failure only surfaces as a **halt** in `/triage` (§9), keeping the
  list logic simple.

### 5.2 `POST /triage`

Request: `{ "question": string }` (non-empty; 422 otherwise).

Runs `graph.invoke({ messages:[HumanMessage(question)], final_output:None,
agent2_messages:[], recommendation:None })`.

Response:

```jsonc
{
  "triage":         TriageOutput,      // verbatim from Agent 1
  "recommendation": Recommendation,    // verbatim from Agent 2
  "citations": [                        // enriched from recommendation.citations
    { "code": "MERCH-SOP-014", "section": "§3.2",
      "title": "Variance tiering", "quote": "A receipt variance of ..." }
  ],
  "halt": "data_quality" | "terminal_status" | "unresolved_po" | null
}
```

- `halt` mirrors `triage.halt` for convenient UI branching.
- Citation enrichment: parse the referenced SOP markdown, locate the section by its
  number, and extract the section heading (title) + the clause text (quote). If a
  reference cannot be resolved, return it with `title/quote = null` so the UI can fall
  back to a reference-only card.

## 6. Derivations & mappings (schema → UI)

- **Tier display:** `V0→Clean, V1→Minor, V2→Material, V3→Major, V4→Critical`; badge
  renders `TIER n · WORD`.
- **`summary_line`:** join the parts that apply, `·`-separated:
  - qty short: `"Short-ship {pct}%"`; qty over: `"Over-delivery +{pct}%"` (pct rounded).
  - eta slip: `"ETA +{days}d"` (only when days > 0).
  - season boundary override present: `"season slip"`.
  - If none apply: `"Within tolerance"`.
- **Recommended-action headline** (enum → short title; `rationale` shown beneath):
  `amend`→"Amend the purchase order", `split_child_po`→"Split into a child PO",
  `firm_planned_order`→"Firm the planned order", `raise_backorder`→"Raise a back-order
  for the shortfall", `escalate`→"Escalate for review".
- **Stats row:** Ordered = `po_record.ordered_qty`; Confirmed = `po_record.confirmed_qty`;
  Variance = `tier.qty_variance_pct`; ETA = `tier.eta_variance_days` (`±Nd`). Value at
  risk (`tier.value_at_risk_gbp`) shown as a secondary stat when present.
- **Exception-type chips:** `quantity_variance_short`→"Short-ship",
  `quantity_variance_over`→"Over-delivery", `eta_slip`→"ETA slip",
  `partial_delivery`→"Part received", `season_boundary_risk`→"Season boundary",
  `wholesale_constraint`→"Wholesale", `parent_child_context`→"Parent/child".
- **Confidence:** high/medium/low → full / two-thirds / one-third bar + label; grounding
  note derived from confidence + citation count (e.g. "N cited clauses matched
  directly.").

## 7. Data flow

1. Load → `GET /flagged-pos` → render left panel (tier badges + summary lines + count).
2. Click a PO → select it; main panel shows the **empty "Ask a question to run triage"**
   state; question input is prefilled with that PO's synthetic `query` (editable).
3. Ask → `POST /triage { question }` → report-shaped **skeleton** while awaiting.
4. Response → render the **full report**, or the **edge-state panel** when `halt` is set.

## 8. Frontend structure

- `app/page.tsx` — dashboard shell + client state (`flaggedPos`, `selectedPoId`,
  `question`, `result`, `status: idle|loading|done|error`).
- `components/FlaggedPoList` → `FilterInput` (filter by PO id or supplier) + `PoRow`
  (`TierBadge` + summary line).
- `components/QuestionBar` — input + Ask button (disabled when empty/loading).
- `components/ReportPanel` — renders one of `EmptyState | ReportSkeleton | Report |
  EdgeStatePanel | ErrorState`.
  - `Report`: `RecommendedActionHeader` (label + `TierBadge` + headline + rationale) ·
    `StatsRow` · `PolicyCitations` (`CitationCard[]`) · right column: `ConfidenceCard`,
    `EscalationCard` (role only), `ExceptionTypeChips`, `ActionButtons`
    (Copy summary = clipboard text; Open PO in ERP = stub/no-op).
- `lib/api.ts` — typed client (`getFlaggedPos`, `postTriage`).
- `lib/types.ts` — TS types mirroring the backend schemas + enriched response.
- `lib/format.ts` — tier, action, exception-type, variance, confidence mappings.
- `lib/config.ts` — `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).

## 9. Edge-state panel (halt)

For `data_quality` / `terminal_status` / `unresolved_po`: a "Can't auto-recommend" view
showing the halt reason + `tier.validation.failures` (when present), the facts we do have
(stats), any exception-type chips, and Agent 2's `escalate` action + escalation role at
Low confidence. Exercised by PO-88413 (missing parent) and PO-88416 (missing ETA).

## 10. Error handling

- Network / 500 / model-not-ready → `ErrorState` with a retry button.
- Empty question → Ask disabled.
- `/triage` first call may be slow (model warm-up handled by startup `prewarm()`); the
  skeleton covers ordinary latency.
- CORS misconfig surfaces as a clear error message, not a silent failure.

## 11. Config & security

- Frontend env: only `NEXT_PUBLIC_API_BASE_URL` — a public base URL, not a secret.
- No API keys, tokens, or SOP text are bundled into the frontend build.
- Escalation output is **role-only** by construction (backend guarantee); the UI never
  renders names, emails, or phone numbers.

## 12. Testing

- **Backend (`pytest`):** `/flagged-pos` (fast, deterministic, covers short/over/eta/
  season/data-quality rows) + citation resolver (reference → title + quote, incl.
  unresolved fallback). `/triage` tested with a **mocked graph** (no live LLM) for the
  happy path and a halt path.
- **Frontend (Vitest + RTL):** list + `TierBadge` mapping, report vs edge-state vs
  skeleton vs error rendering, prefill-on-click, and format helpers — all against a
  mocked API client. One Playwright happy-path (load → click PO → Ask → report).

## 13. Risks / open items

- **Latency:** two LLM stages + RAG per question; mitigated by skeleton + startup
  prewarm. Streaming is deliberately deferred.
- **Headline fidelity:** the wireframe's rich action sentence is illustrative; we render
  an enum-derived title + the model's `rationale`. Accepted.
- **Citation section parsing** depends on SOP markdown heading/section conventions; the
  resolver must fall back gracefully to reference-only when a section can't be located.
