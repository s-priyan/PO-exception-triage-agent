## How I interpreted the problem and my assumptions

A merchandising planner asks a free-text question about a problem purchase order
(e.g. *"PO-88405 came in short and the ETA has slipped, what's going on?"*). The
system has to turn that into a **defensible, auditable action** not a chat reply.

I read this as two responsibilities that must never blur:

1. **Establish the facts,**  which PO, what varied, how severe deterministically.
2. **Decide what to do**, grounded strictly in the company SOPs, with citations.

The hard part isn't producing a recommendation; it's *trust*. A planner must be able
to act on the output, so every number has to be reproducible and every policy claim
has to trace back to a clause. That pushed the whole design toward determinism and
grounding over LLM cleverness.

**Assumptions:**

- Severity/tiering is **policy, not judgement**, so it belongs in code, not the model.
`compute_variance_tier` is the single source of truth (it encodes MERCH-SOP-014); the
LLM never does the arithmetic and never overrides it.
- Agent 1 must not "help" by reasoning about policy doing so would let it leak an answer it isn't grounded to. It only gathers facts and classifies.
- Data is mock fixture JSON (20 POs) deliberately covering the edge cases the SOPs
describe: terminal statuses, data-quality failures, season-boundary slips,
over-delivery, wholesale allocations, and parent/child splits. Tools read these
files; there are no live systems.
- The 5-document SOP corpus is the **only** source of policy truth. If it is silent or
self-contradictory, the correct output is *escalate*, not a guess.
- PII in the escalation matrix (names, emails, phones) must **never** reach the output, only role titles.
- One PO per question, and exactly one recommended action is required.

## Architecture and key design decisions

A two-stage LangGraph pipeline, each stage a gather-loop that finalizes into a typed object:

```
START -> agent1 -> (tools1 -> agent1)* -> agent2 -> (tools2 -> agent2)* -> END
```

- **Agent 1 — triage (facts).** Resolves the PO, calls three tools
(`get_purchase_order`, `get_forecast`, `compute_variance_tier`), multi-labels the
exception types, and drafts retrieval queries. Emits a typed `TriageOutput`. Has **no
access to policy**.
- **Agent 2 — recommendation (judgement).** Consumes Agent 1's object, retrieves SOP
passages via `search_sops` (RAG), and emits a typed `Recommendation`: one action,
rationale, citations, confidence, and a PII-safe escalation role. The **only** stage
permitted to read policy.

**Key decisions and rationale:**

- **Strict fact / judgement separation.** The single biggest guardrail. Agent 1
physically cannot see the SOP corpus, so it cannot invent policy; Agent 2 must ground
every claim in a retrieved clause. This makes the reasoning auditable and stops the
model answering from parametric memory.
- **Deterministic tiering in Python, not the LLM.** All variance maths and tier
overrides (compound variance, wholesale channel, season-boundary) live in `tools.py` and are authoritative. This removes arithmetic, the thing LLMs are least reliable at from the model entirely and makes severity reproducible.
- **Verbatim hand-off.** Agent 1 copies `po_record`, `forecast`, and `tier` into its
output unmodified . Agent 2 decides relevance, so summarising or dropping a field upstream
would be reasoning-without-data downstream.
- **Citation-grounded RAG with anti-hallucination guardrails.** Markdown is
header-split (to keep section numbers for `document.md §n` citations) then recursively
chunked, embedded with instruction-aware Harrier vectors, and stored in persistent
Chroma (cosine). `search_sops` returns citations plus relevance scores. The prompt
enforces: no citation → invalid; retrieval silent → *escalate* / low confidence;
clauses conflict → *escalate* / confidence ≤ medium.
- **Typed contracts (Pydantic).** `TriageOutput`, `TierResult`, and `Recommendation`
use `Literal` enums for actions, exception types, and confidence, giving a strict
schema between stages and a machine-consumable final result.
- **One reusable LLM wrapper.** `StructuredToolLLM` runs the same "loop over tools until done, then coerce to schema" pattern for both agents, differing only by tool set and output schema,  no duplication.
- **Explicit halts.** Agent 1 halts on `unresolved_po`, `data_quality`, or
`terminal_status`; Agent 2 turns a halt into a low-confidence *escalate* rather than
forcing a recommendation on a record that cannot be reasoned over.
- **PII safe by construction.** Both prompts forbid names, emails, and phone numbers;
escalation is expressed as a role title only, matching the escalation matrix's
handling notice.
- **Performance.** The embedding model and Chroma index are prewarmed once as
singletons, and the index persists across runs.

