# PO exception triage system

A two-stage LangGraph agent for merchandising PO exception triage. A planner asks
about a problem purchase order in natural language; the system gathers the facts,
grounds itself in the merch SOPs, and returns a structured recommendation with
citations.

- **Agent 1 — triage.** Resolves the PO, calls the data tools, classifies the
  exception types, and synthesises retrieval queries. It never reasons about policy.
- **Agent 2 — recommendation.** Takes Agent 1's output, retrieves SOP passages via
  RAG, and recommends exactly one action with inline citations, a confidence level,
  and a PII-safe escalation role.

## Layout

```
ASOS/
├── files/                 # mock data + SOP corpus
│   ├── purchase_orders.json
│   ├── forecasts.json
│   └── *.md               # 5 SOP documents (indexed by RAG)
├── src/
│   ├── prompts.py         # AGENT_1_SYSTEM_PROMPT, AGENT_2_SYSTEM_PROMPT
│   ├── schemas.py         # TriageOutput, TierResult, Recommendation
│   ├── tools.py           # Agent 1 tools + SOP tier logic
│   ├── embeddings.py      # Harrier embedding model (prewarmed singleton)
│   ├── retrieval.py       # recursive chunking + Chroma + search_sops tool
│   ├── llm.py             # StructuredToolLLM wrapper (tool-bind + structured output)
│   └── graph.py           # compiled two-stage LangGraph
├── main.py                # CLI entry point
├── pyproject.toml         # project metadata + dependencies
├── requirements.txt       # dependency mirror for pip installs
└── .env.example
```

## Graph

```
START -> agent1 -> (tools1 -> agent1)* -> agent2 -> (tools2 -> agent2)* -> END
```

- **agent1 / tools1** — Agent 1 loop over `get_purchase_order`, `get_forecast`,
  `compute_variance_tier`; emits `TriageOutput`.
- **agent2 / tools2** — Agent 2 loop over `search_sops`; emits `Recommendation`.

Each agent node binds its tools for the gather loop and, once no further tool call
is needed, produces its Pydantic structured output.

## Retrieval (RAG)

- **Embeddings:** `microsoft/harrier-oss-v1-0.6b` (instruction-aware, 1024-dim),
  loaded once as a prewarmed singleton and reused for every call.
- **Chunking:** markdown header split (to keep section numbers for citations) then
  LangChain `RecursiveCharacterTextSplitter`.
- **Vector store:** persistent ChromaDB (cosine), built on first run.
- **Tool:** `search_sops(query)` returns passages tagged with `document.md §n` for
  citation and a relevance score for the low-confidence guardrail.

## Setup

Dependencies are declared in `pyproject.toml` and mirrored in `requirements.txt`.

```bash
# Option A — uv (reads pyproject.toml)
uv sync

# Option B — pip + venv
python -m venv .venv
.venv\Scripts\activate         # Windows PowerShell
pip install -r requirements.txt

# then add your OPENAI_API_KEY
copy .env.example .env
```

The first run downloads the Harrier model (~1.2 GB) and builds the Chroma index;
subsequent runs reuse the cached weights and the persisted index.

## Run

```bash
python main.py "PO-88405 came in short and the ETA has slipped, what's going on?"
# or, with uv: uv run main.py "..."
```

Omitting the argument runs a built-in example. The command prints Agent 1's triage
object followed by Agent 2's recommendation.
