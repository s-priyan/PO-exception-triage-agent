# PO Exception Triage Web UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a FastAPI wrapper over the existing LangGraph triage agent and a Next.js dashboard where a planner picks a flagged PO, asks a question, and sees the grounded recommendation exactly as in the wireframe.

**Architecture:** A thin FastAPI app (`backend/src/api.py`) reuses `prewarm()` + `build_triage_graph()` and exposes `GET /flagged-pos` (deterministic tiering only) and `POST /triage` (runs the graph, enriches citations). A single-page Next.js (App Router) client fetches the flagged list on load, prefills the clicked PO's question, and renders the report / edge-state / skeleton / error views.

**Tech Stack:** Python 3 · FastAPI · Uvicorn · Pydantic v2 · pytest + Starlette TestClient · Next.js (App Router) · TypeScript · Tailwind CSS · lucide-react · Vitest + React Testing Library · Playwright.

## Global Constraints

- **Backend Python style:** PEP 8, black-like, lines up to 100 chars. Explicit return types on all functions. Import namespaced classes before use.
- **Reuse, do not duplicate tiering:** `GET /flagged-pos` MUST call the existing `compute_variance_tier` tool; never re-implement tier maths in Python or TypeScript.
- **Flagged count is real:** the list length equals the number of entries in `synthetic_planner_queries.json` (13) — never hardcode the wireframe's "14".
- **Confidence is categorical:** render `high`/`medium`/`low`; never fabricate a numeric score.
- **Security — no secrets in the frontend:** the only frontend env var is `NEXT_PUBLIC_API_BASE_URL` (a public base URL). `OPENAI_API_KEY` stays in `backend/.env`. No SOP text or credentials are bundled into the client build.
- **PII by construction:** escalation is a role title only. The citation resolver MUST NOT return table rows (which contain names/emails/phones) as quotes.
- **Citation string format:** Agent 2 emits `"<filename>.md §<section>"` (e.g. `variance_detection_sop.md §2.1`). The document code (e.g. `MERCH-SOP-014`) lives inside the file as `**Document ID:** ...`.
- **Tier display mapping:** `V0→Clean, V1→Minor, V2→Material, V3→Major, V4→Critical`.
- **Commits:** conventional-commit style. If the working branch name encodes a ticket (e.g. `feature/AIP-0101_...`), prepend `[AIP-0101] ` to each commit subject (user rule); otherwise use the subject as written.
- **Commands are run from the stated directory** (`backend/` for Python, `frontend/` for Node).

## File Structure

**Backend (new, all in `backend/`):**
- `src/api.py` — FastAPI app factory + routes + CORS + lifespan prewarm.
- `src/api_schemas.py` — API-only Pydantic models (`FlaggedPo`, `FlaggedPosResponse`, `Citation`, `TriageRequest`, `TriageResponse`).
- `src/flagged.py` — deterministic flagged-PO list builder (reuses `get_purchase_order` + `compute_variance_tier`).
- `src/citations.py` — resolves `"file.md §n"` → `{code, section, title, quote}` from the SOP markdown.
- `src/service.py` — `run_triage(question, graph)` orchestration (invoke graph + enrich citations + surface halt).
- `tests/test_citations.py`, `tests/test_flagged.py`, `tests/test_api.py`.
- `requirements.txt` — add FastAPI/Uvicorn/httpx/pytest.

**Frontend (new, all in `frontend/`):**
- Config: `package.json`, `tsconfig.json`, `next.config.mjs`, `tailwind.config.ts`, `postcss.config.js`, `vitest.config.ts`, `vitest.setup.ts`, `playwright.config.ts`, `.env.local.example`, `.gitignore`.
- `app/layout.tsx`, `app/globals.css`, `app/page.tsx`.
- `lib/config.ts`, `lib/types.ts`, `lib/format.ts`, `lib/format.test.ts`, `lib/api.ts`, `lib/api.test.ts`.
- `components/ui/` — `Badge.tsx`, `Skeleton.tsx` (minimal Tailwind primitives).
- `components/TierBadge.tsx` (+ `TierBadge.test.tsx`).
- `components/FlaggedPoList.tsx`, `components/PoRow.tsx` (+ `FlaggedPoList.test.tsx`).
- `components/QuestionBar.tsx`, `components/states/EmptyState.tsx`, `components/states/ReportSkeleton.tsx`, `components/states/ErrorState.tsx`.
- `components/report/` — `RecommendedActionHeader.tsx`, `StatsRow.tsx`, `ExceptionTypeChips.tsx`, `ConfidenceCard.tsx`, `EscalationCard.tsx`, `ActionButtons.tsx`, `PolicyCitations.tsx`, `Report.tsx`.
- `components/EdgeStatePanel.tsx`, `components/ReportPanel.tsx` (+ `ReportPanel.test.tsx`).
- `e2e/happy-path.spec.ts`.
- `README.md` — run both servers.

> **Note on shadcn/ui:** the spec named shadcn/ui. To keep this plan reproducible (no interactive generator), we use Tailwind with a couple of tiny local primitives in the same visual style. This satisfies the spec's intent; swap to generated shadcn components later if desired.

---

## Task 1: Backend deps + FastAPI app factory + health route

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/src/api.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Produces: `create_app(graph=None, prewarm_startup=True) -> FastAPI`. When `graph` is provided it is stored on `app.state.graph` and startup prewarm is skipped. Exposes `GET /health` → `{"status": "ok"}`.

- [ ] **Step 1: Add dependencies**

Append to `backend/requirements.txt`:

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
httpx>=0.27.0
pytest>=8.0.0
```

Install (from `backend/`):

```bash
pip install -r requirements.txt
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_api.py`:

```python
"""API surface tests. Uses an injected fake graph so no model is loaded."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import create_app


def _client() -> TestClient:
    return TestClient(create_app(graph=object(), prewarm_startup=False))


def test_health_ok() -> None:
    response = _client().get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Run test to verify it fails**

Run (from `backend/`): `python -m pytest tests/test_api.py::test_health_ok -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.api'`.

- [ ] **Step 4: Write minimal implementation**

Create `backend/src/api.py`:

```python
"""FastAPI wrapper over the two-stage triage graph.

Exposes a deterministic flagged-PO list and a live triage endpoint. The heavy
graph/model stack is imported lazily (only on startup or per triage call) so the
app and its lighter routes stay importable and testable without loading Harrier.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def _frontend_origins() -> list[str]:
    """Return the allowed CORS origins from env, defaulting to the Next dev host."""
    raw = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(graph: Optional[Any] = None, prewarm_startup: bool = True) -> FastAPI:
    """Build the FastAPI app.

    :param graph: Optional pre-built/compiled graph (or fake) for tests; when set,
        startup prewarm is skipped and this graph is used for /triage.
    :param prewarm_startup: When True and no graph is injected, prewarm the model
        and build the real graph on startup.
    :returns: The configured FastAPI application.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.graph is None and prewarm_startup:
            # Imported here so importing this module stays light for tests.
            from .graph import build_triage_graph
            from .retrieval import prewarm

            prewarm()
            app.state.graph = build_triage_graph()
        yield

    app = FastAPI(title="PO Exception Triage API", lifespan=lifespan)
    app.state.graph = graph

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_frontend_origins(),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_api.py::test_health_ok -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/src/api.py backend/tests/test_api.py
git commit -m "feat(api): add FastAPI app factory with health route"
```

---

## Task 2: Citation resolver

**Files:**
- Create: `backend/src/api_schemas.py`
- Create: `backend/src/citations.py`
- Test: `backend/tests/test_citations.py`

**Interfaces:**
- Produces: `Citation` model `{code: str, section: str, title: str | None, quote: str | None}`; `resolve_citation(citation: str) -> Citation`. `section` is the display token (e.g. `"§2.1"`) or `""`. `quote` is the first prose paragraph of the section (never a markdown table/code block), capped at 500 chars, else `None`.

- [ ] **Step 1: Create the API schemas file (needed by this and later tasks)**

Create `backend/src/api_schemas.py`:

```python
"""Pydantic models for the HTTP API layer (separate from the agent schemas)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from .schemas import Recommendation, TriageOutput


class TierDisplay(BaseModel):
    """Human-facing tier label derived from the V0-V4 code."""

    number: int
    word: str


class FlaggedPo(BaseModel):
    """One row in the flagged-PO list (deterministic; no LLM)."""

    po_id: str
    supplier: str
    category: str
    tier: Optional[str]
    tier_display: TierDisplay
    qty_variance_pct: Optional[float]
    eta_variance_days: Optional[int]
    summary_line: str
    query: str


class FlaggedPosResponse(BaseModel):
    """Envelope for the flagged-PO list."""

    count: int
    items: List[FlaggedPo]


class Citation(BaseModel):
    """A resolved SOP citation: code + section + title + quoted clause."""

    code: str
    section: str
    title: Optional[str] = None
    quote: Optional[str] = None


class TriageRequest(BaseModel):
    """Planner question payload."""

    question: str


class TriageResponse(BaseModel):
    """Full triage result returned to the UI."""

    triage: TriageOutput
    recommendation: Recommendation
    citations: List[Citation]
    halt: Optional[str] = None
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_citations.py`:

```python
"""Citation resolver tests against the real SOP corpus."""

from __future__ import annotations

from src.citations import resolve_citation


def test_resolves_subsection_title_and_prose_quote() -> None:
    result = resolve_citation("variance_detection_sop.md §2.1")
    assert result.code == "MERCH-SOP-014"
    assert result.section == "§2.1"
    assert result.title == "Compound variance rule"
    assert result.quote is not None
    assert result.quote.startswith("Where a PO carries")


def test_skips_leading_table_and_returns_following_prose() -> None:
    result = resolve_citation("variance_detection_sop.md §3")
    assert result.title == "Auto-action and human-review boundary"
    assert result.quote is not None
    assert result.quote.startswith("The auto-action boundary sits between V1 and V2")


def test_table_only_section_has_no_quote_no_pii() -> None:
    result = resolve_citation("merch_escalation_matrix.md §3")
    assert result.code == "MERCH-POL-009"
    assert result.title == "Contacts by category"
    assert result.quote is None  # never leak the names/emails in the tables


def test_unknown_section_returns_reference_only() -> None:
    result = resolve_citation("variance_detection_sop.md §99")
    assert result.code == "MERCH-SOP-014"
    assert result.section == "§99"
    assert result.title is None
    assert result.quote is None


def test_missing_file_degrades_gracefully() -> None:
    result = resolve_citation("nonexistent.md §1")
    assert result.code == "nonexistent"
    assert result.title is None
    assert result.quote is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_citations.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.citations'`.

- [ ] **Step 4: Write minimal implementation**

Create `backend/src/citations.py`:

```python
"""Resolve Agent 2 citation strings to code + section + title + quoted clause.

A citation is "<filename>.md §<section>" (section like "3" or "2.1"). The document
code (e.g. MERCH-SOP-014) is declared inside the file. Quotes are prose only:
markdown tables and code fences are skipped so PII in the escalation matrix tables
can never reach an output.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from .api_schemas import Citation

FILES_DIR = Path(__file__).resolve().parents[1] / "files"
_QUOTE_CAP = 500

_CITATION_RE = re.compile(r"^\s*(?P<file>[\w\-.]+\.md)\s*(?:§\s*(?P<sec>[\d.]+))?")
_DOC_ID_RE = re.compile(r"\*\*Document ID:\*\*\s*(?P<code>[A-Za-z0-9\-]+)")
_HEADING_RE = re.compile(r"^#{1,6}\s+(?P<num>\d+(?:\.\d+)*)\.?\s+(?P<title>.+?)\s*$")
_ANY_HEADING_RE = re.compile(r"^#{1,6}\s+")


def _cap(text: str) -> str:
    """Cap a quote to a readable length."""
    if len(text) <= _QUOTE_CAP:
        return text
    return text[: _QUOTE_CAP - 1].rstrip() + "\u2026"


def _first_prose_quote(lines: List[str], start: int) -> Optional[str]:
    """Return the first prose paragraph after ``start`` until the next heading.

    Table rows (``|``) and code fences (```` ``` ````) are skipped so structured
    blocks — including the PII tables in the escalation matrix — are never quoted.
    """
    body: List[str] = []
    for line in lines[start:]:
        if _ANY_HEADING_RE.match(line):
            break
        body.append(line)

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", "\n".join(body)) if p.strip()]
    for paragraph in paragraphs:
        first = paragraph.splitlines()[0].strip()
        if first.startswith("|") or first.startswith("```"):
            continue
        return _cap(" ".join(paragraph.split()))
    return None


def resolve_citation(citation: str) -> Citation:
    """Resolve one citation string into a structured, display-ready Citation."""
    match = _CITATION_RE.match(citation or "")
    if not match:
        return Citation(code=(citation or "").strip(), section="")

    filename = match.group("file")
    section = match.group("sec") or ""
    section_display = f"\u00a7{section}" if section else ""
    path = FILES_DIR / filename

    if not path.exists():
        return Citation(code=Path(filename).stem, section=section_display)

    text = path.read_text(encoding="utf-8")
    doc_id = _DOC_ID_RE.search(text)
    code = doc_id.group("code") if doc_id else path.stem

    if not section:
        return Citation(code=code, section="")

    lines = text.splitlines()
    for index, line in enumerate(lines):
        heading = _HEADING_RE.match(line)
        if heading and heading.group("num") == section:
            return Citation(
                code=code,
                section=section_display,
                title=heading.group("title").strip(),
                quote=_first_prose_quote(lines, index + 1),
            )

    return Citation(code=code, section=section_display)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_citations.py -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/src/api_schemas.py backend/src/citations.py backend/tests/test_citations.py
git commit -m "feat(api): resolve SOP citations to code/title/quote, PII-safe"
```

---

## Task 3: Flagged-PO list service + endpoint

**Files:**
- Create: `backend/src/flagged.py`
- Modify: `backend/src/api.py` (add the route)
- Test: `backend/tests/test_flagged.py`

**Interfaces:**
- Consumes: `get_purchase_order`, `compute_variance_tier`, `FILES_DIR` from `src.tools`; `FlaggedPo`, `TierDisplay` from `src.api_schemas`.
- Produces: `build_flagged_pos() -> list[FlaggedPo]`; route `GET /flagged-pos -> FlaggedPosResponse`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_flagged.py`:

```python
"""Deterministic flagged-PO list tests (no LLM)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import create_app
from src.flagged import build_flagged_pos


def test_list_length_matches_queries_file() -> None:
    items = build_flagged_pos()
    assert len(items) == 13


def test_po_88405_fields() -> None:
    item = next(i for i in build_flagged_pos() if i.po_id == "PO-88405")
    assert item.supplier == "Anadolu Tekstil"
    assert item.tier == "V2"
    assert item.tier_display.number == 2
    assert item.tier_display.word == "Material"
    assert item.qty_variance_pct == -12.0
    assert item.eta_variance_days == 9
    assert item.summary_line == "Short-ship -12% \u00b7 ETA +9d"


def test_endpoint_returns_envelope() -> None:
    client = TestClient(create_app(graph=object(), prewarm_startup=False))
    response = client.get("/flagged-pos")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 13
    assert len(body["items"]) == 13
    assert body["items"][0]["po_id"].startswith("PO-")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_flagged.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.flagged'`.

- [ ] **Step 3: Write the flagged-list builder**

Create `backend/src/flagged.py`:

```python
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
```

- [ ] **Step 4: Add the route to `backend/src/api.py`**

Add the import near the top of `src/api.py` (with the other imports):

```python
from .api_schemas import FlaggedPosResponse
from .flagged import build_flagged_pos
```

Add this route inside `create_app`, immediately after the `health` route:

```python
    @app.get("/flagged-pos", response_model=FlaggedPosResponse)
    def flagged_pos() -> FlaggedPosResponse:
        """Return the deterministically tiered flagged-PO list (no LLM)."""
        items = build_flagged_pos()
        return FlaggedPosResponse(count=len(items), items=items)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_flagged.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/src/flagged.py backend/src/api.py backend/tests/test_flagged.py
git commit -m "feat(api): add deterministic GET /flagged-pos endpoint"
```

---

## Task 4: Triage service + endpoint (mocked graph)

**Files:**
- Create: `backend/src/service.py`
- Modify: `backend/src/api.py` (add the route)
- Test: `backend/tests/test_api.py` (extend)

**Interfaces:**
- Consumes: `app.state.graph` (an object with `.invoke(state: dict) -> dict` returning keys `final_output: TriageOutput` and `recommendation: Recommendation`); `resolve_citation`; `TriageResponse`.
- Produces: `run_triage(question: str, graph) -> TriageResponse`; route `POST /triage` (422 on empty question, 503 when the graph is not ready).

- [ ] **Step 1: Write the failing test (extend `tests/test_api.py`)**

Append to `backend/tests/test_api.py`:

```python
from langchain_core.messages import HumanMessage

from src.schemas import Recommendation, TriageOutput


class _FakeGraph:
    """Stand-in graph that returns fixed structured outputs without an LLM."""

    def __init__(self, triage: TriageOutput, recommendation: Recommendation) -> None:
        self._triage = triage
        self._recommendation = recommendation
        self.last_state: dict = {}

    def invoke(self, state: dict) -> dict:
        self.last_state = state
        return {"final_output": self._triage, "recommendation": self._recommendation}


def _fake_success_graph() -> _FakeGraph:
    triage = TriageOutput(
        po_id="PO-88405",
        halt=None,
        planner_question="PO-88405 came in short and the ETA slipped, what's going on?",
        po_record={"po_id": "PO-88405", "ordered_qty": 5000, "confirmed_qty": 4400},
        forecast=None,
        tier={
            "tier": "V2",
            "qty_variance_pct": -12.0,
            "eta_variance_days": 9,
            "value_at_risk_gbp": 22800.0,
            "overrides_applied": [],
            "validation": {"passed": True, "failures": []},
        },
        exception_types=["quantity_variance_short", "eta_slip"],
        queries=["quantity variance amendment"],
    )
    recommendation = Recommendation(
        po_id="PO-88405",
        recommended_action="amend",
        rationale="V2 short-ship within amendment tolerance.",
        citations=["variance_detection_sop.md \u00a72.1"],
        confidence="high",
        escalation_target_role=None,
    )
    return _FakeGraph(triage, recommendation)


def test_triage_returns_enriched_citations() -> None:
    client = TestClient(
        create_app(graph=_fake_success_graph(), prewarm_startup=False)
    )
    response = client.post("/triage", json={"question": "PO-88405?"})
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"]["recommended_action"] == "amend"
    assert body["halt"] is None
    assert body["citations"][0]["code"] == "MERCH-SOP-014"
    assert body["citations"][0]["title"] == "Compound variance rule"


def test_triage_rejects_empty_question() -> None:
    client = TestClient(
        create_app(graph=_fake_success_graph(), prewarm_startup=False)
    )
    response = client.post("/triage", json={"question": "   "})
    assert response.status_code == 422


def test_triage_passes_question_into_graph() -> None:
    graph = _fake_success_graph()
    client = TestClient(create_app(graph=graph, prewarm_startup=False))
    client.post("/triage", json={"question": "hello PO-88405"})
    sent = graph.last_state["messages"][0]
    assert isinstance(sent, HumanMessage)
    assert sent.content == "hello PO-88405"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_api.py -v`
Expected: FAIL — 404 on `/triage` (route not defined) / import error for `src.service` once referenced.

- [ ] **Step 3: Write the service**

Create `backend/src/service.py`:

```python
"""Orchestrate one triage pass: invoke the graph and enrich the result for the UI."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from .api_schemas import TriageResponse
from .citations import resolve_citation


def run_triage(question: str, graph: Any) -> TriageResponse:
    """Run the compiled graph for one question and assemble the API response.

    :param question: The planner's verbatim question.
    :param graph: A compiled graph exposing ``invoke(state) -> dict``.
    :returns: The triage output, recommendation, resolved citations and halt.
    :raises RuntimeError: If the graph does not produce both structured outputs.
    """
    result = graph.invoke(
        {
            "messages": [HumanMessage(content=question)],
            "final_output": None,
            "agent2_messages": [],
            "recommendation": None,
        }
    )

    triage = result.get("final_output")
    recommendation = result.get("recommendation")
    if triage is None or recommendation is None:
        raise RuntimeError("Triage did not complete: missing structured output.")

    citations = [resolve_citation(reference) for reference in recommendation.citations]
    return TriageResponse(
        triage=triage,
        recommendation=recommendation,
        citations=citations,
        halt=triage.halt,
    )
```

- [ ] **Step 4: Add the route to `backend/src/api.py`**

Add imports near the top of `src/api.py`:

```python
from fastapi import HTTPException
from .api_schemas import TriageRequest, TriageResponse
from .service import run_triage
```

Add this route inside `create_app`, after the `flagged_pos` route:

```python
    @app.post("/triage", response_model=TriageResponse)
    def triage(request: TriageRequest) -> TriageResponse:
        """Run the live agent for one planner question."""
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=422, detail="question must not be empty")
        if app.state.graph is None:
            raise HTTPException(status_code=503, detail="triage graph is not ready")
        return run_triage(question, app.state.graph)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/ -v`
Expected: PASS (all backend tests).

- [ ] **Step 6: Commit**

```bash
git add backend/src/service.py backend/src/api.py backend/tests/test_api.py
git commit -m "feat(api): add POST /triage running the live graph with enriched citations"
```

---

## Task 5: Frontend scaffold + config + types + primitives

**Files:** create all config files, `app/*`, `lib/config.ts`, `lib/types.ts`, `components/ui/Badge.tsx`, `components/ui/Skeleton.tsx`, `components/TierBadge.tsx`, `components/TierBadge.test.tsx`.

**Interfaces:**
- Produces: `API_BASE_URL`; all shared TS types; `<TierBadge number word />`; `<Badge/>`, `<Skeleton/>`.

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "po-triage-ui",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "e2e": "playwright test"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.454.0"
  },
  "devDependencies": {
    "@playwright/test": "^1.48.0",
    "@testing-library/jest-dom": "^6.5.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "jsdom": "^25.0.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.6.0",
    "vitest": "^2.1.0"
  }
}
```

Install (from `frontend/`): `npm install`

- [ ] **Step 2: Create config files**

`frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "baseUrl": ".",
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

`frontend/next.config.mjs`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {};
export default nextConfig;
```

`frontend/postcss.config.js`:

```javascript
module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

`frontend/tailwind.config.ts`:

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
export default config;
```

`frontend/.env.local.example`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`frontend/.gitignore`:

```
node_modules
.next
.env.local
playwright-report
test-results
```

- [ ] **Step 3: Create the app shell**

`frontend/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  background-color: #0b0e14;
  color: #e6e9ef;
}
```

`frontend/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PO Exception Triage",
  description: "Merchandising PO exception triage",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

`frontend/app/page.tsx` (placeholder, wired in Task 12):

```tsx
export default function Page() {
  return <main className="p-6">PO Exception Triage</main>;
}
```

- [ ] **Step 4: Create config + types**

`frontend/lib/config.ts`:

```typescript
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
```

`frontend/lib/types.ts`:

```typescript
export type TierWord = "Clean" | "Minor" | "Material" | "Major" | "Critical";

export interface TierDisplay {
  number: number;
  word: TierWord;
}

export interface FlaggedPo {
  po_id: string;
  supplier: string;
  category: string;
  tier: string | null;
  tier_display: TierDisplay;
  qty_variance_pct: number | null;
  eta_variance_days: number | null;
  summary_line: string;
  query: string;
}

export interface FlaggedPosResponse {
  count: number;
  items: FlaggedPo[];
}

export type ExceptionType =
  | "quantity_variance_short"
  | "quantity_variance_over"
  | "eta_slip"
  | "partial_delivery"
  | "season_boundary_risk"
  | "wholesale_constraint"
  | "parent_child_context";

export type RecommendedAction =
  | "amend"
  | "split_child_po"
  | "firm_planned_order"
  | "raise_backorder"
  | "escalate";

export type Confidence = "high" | "medium" | "low";
export type HaltReason = "unresolved_po" | "data_quality" | "terminal_status";

export interface TierResult {
  tier: string;
  qty_variance_pct: number | null;
  eta_variance_days: number | null;
  value_at_risk_gbp: number | null;
  overrides_applied: string[];
  validation: { passed: boolean; failures: string[] };
}

export interface TriageOutput {
  po_id: string | null;
  halt: HaltReason | null;
  planner_question: string;
  po_record: Record<string, unknown> | null;
  forecast: Record<string, unknown> | null;
  tier: TierResult | null;
  exception_types: ExceptionType[];
  queries: string[];
}

export interface Recommendation {
  po_id: string | null;
  recommended_action: RecommendedAction;
  rationale: string;
  citations: string[];
  confidence: Confidence;
  escalation_target_role: string | null;
}

export interface Citation {
  code: string;
  section: string;
  title: string | null;
  quote: string | null;
}

export interface TriageResponse {
  triage: TriageOutput;
  recommendation: Recommendation;
  citations: Citation[];
  halt: HaltReason | null;
}
```

- [ ] **Step 5: Create UI primitives + TierBadge**

`frontend/components/ui/Badge.tsx`:

```tsx
import { ReactNode } from "react";

export function Badge({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${className}`}
    >
      {children}
    </span>
  );
}
```

`frontend/components/ui/Skeleton.tsx`:

```tsx
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-slate-800/70 ${className}`} />;
}
```

`frontend/components/TierBadge.tsx`:

```tsx
import { Badge } from "./ui/Badge";

const TIER_CLASSES: Record<number, string> = {
  0: "bg-slate-700 text-slate-200",
  1: "bg-slate-600 text-slate-100",
  2: "bg-rose-600/90 text-white",
  3: "bg-rose-700 text-white",
  4: "bg-red-800 text-white",
};

export function TierBadge({
  number,
  word,
  withWord = false,
}: {
  number: number;
  word: string;
  withWord?: boolean;
}) {
  const label = withWord ? `TIER ${number} · ${word.toUpperCase()}` : `TIER ${number}`;
  return <Badge className={TIER_CLASSES[number] ?? TIER_CLASSES[0]}>{label}</Badge>;
}
```

- [ ] **Step 6: Create vitest config + setup**

`frontend/vitest.config.ts`:

```typescript
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL(".", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    exclude: ["e2e/**", "node_modules/**"],
  },
});
```

> The `@` alias here must mirror the `paths` mapping in `tsconfig.json` so component/lib imports resolve under Vitest as well as Next.js.

`frontend/vitest.setup.ts`:

```typescript
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 7: Write the TierBadge test**

`frontend/components/TierBadge.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TierBadge } from "./TierBadge";

describe("TierBadge", () => {
  it("renders number only by default", () => {
    render(<TierBadge number={2} word="Material" />);
    expect(screen.getByText("TIER 2")).toBeInTheDocument();
  });

  it("renders number and word when withWord is set", () => {
    render(<TierBadge number={2} word="Material" withWord />);
    expect(screen.getByText("TIER 2 · MATERIAL")).toBeInTheDocument();
  });
});
```

- [ ] **Step 8: Run typecheck + test**

Run (from `frontend/`): `npm run typecheck && npm run test`
Expected: typecheck clean; TierBadge tests PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend
git commit -m "feat(ui): scaffold Next.js app with types, config and TierBadge"
```

---

## Task 6: Format helpers

**Files:** create `frontend/lib/format.ts`, `frontend/lib/format.test.ts`.

**Interfaces:**
- Produces: `actionHeadline(a: RecommendedAction): string`, `EXCEPTION_LABELS: Record<ExceptionType, string>`, `confidenceFill(c: Confidence): number`, `formatPct(v: number|null): string`, `formatEtaDays(v: number|null): string`, `formatQty(v: number|null|undefined): string`.

- [ ] **Step 1: Write the failing test**

`frontend/lib/format.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import {
  actionHeadline,
  confidenceFill,
  EXCEPTION_LABELS,
  formatEtaDays,
  formatPct,
  formatQty,
} from "./format";

describe("format helpers", () => {
  it("maps action enum to a headline", () => {
    expect(actionHeadline("amend")).toBe("Amend the purchase order");
    expect(actionHeadline("escalate")).toBe("Escalate for review");
  });

  it("labels exception types", () => {
    expect(EXCEPTION_LABELS.quantity_variance_short).toBe("Short-ship");
    expect(EXCEPTION_LABELS.eta_slip).toBe("ETA slip");
  });

  it("maps confidence to a bar fill", () => {
    expect(confidenceFill("high")).toBe(100);
    expect(confidenceFill("medium")).toBe(66);
    expect(confidenceFill("low")).toBe(33);
  });

  it("formats variance, days and quantities", () => {
    expect(formatPct(-12)).toBe("-12.0%");
    expect(formatPct(null)).toBe("—");
    expect(formatEtaDays(9)).toBe("+9d");
    expect(formatEtaDays(null)).toBe("—");
    expect(formatQty(4800)).toBe("4,800");
    expect(formatQty(null)).toBe("—");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- format`
Expected: FAIL — cannot find `./format`.

- [ ] **Step 3: Write the implementation**

`frontend/lib/format.ts`:

```typescript
import { Confidence, ExceptionType, RecommendedAction } from "./types";

const ACTION_HEADLINES: Record<RecommendedAction, string> = {
  amend: "Amend the purchase order",
  split_child_po: "Split into a child PO",
  firm_planned_order: "Firm the planned order",
  raise_backorder: "Raise a back-order for the shortfall",
  escalate: "Escalate for review",
};

export function actionHeadline(action: RecommendedAction): string {
  return ACTION_HEADLINES[action];
}

export const EXCEPTION_LABELS: Record<ExceptionType, string> = {
  quantity_variance_short: "Short-ship",
  quantity_variance_over: "Over-delivery",
  eta_slip: "ETA slip",
  partial_delivery: "Part received",
  season_boundary_risk: "Season boundary",
  wholesale_constraint: "Wholesale",
  parent_child_context: "Parent/child",
};

export function confidenceFill(confidence: Confidence): number {
  if (confidence === "high") return 100;
  if (confidence === "medium") return 66;
  return 33;
}

export function formatPct(value: number | null): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function formatEtaDays(value: number | null): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value}d`;
}

export function formatQty(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString("en-GB");
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test -- format`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/format.ts frontend/lib/format.test.ts
git commit -m "feat(ui): add format helpers for tiers, actions and variance"
```

---

## Task 7: Typed API client

**Files:** create `frontend/lib/api.ts`, `frontend/lib/api.test.ts`.

**Interfaces:**
- Consumes: `API_BASE_URL`, `FlaggedPosResponse`, `TriageResponse`.
- Produces: `getFlaggedPos(signal?): Promise<FlaggedPosResponse>`; `postTriage(question, signal?): Promise<TriageResponse>`.

- [ ] **Step 1: Write the failing test**

`frontend/lib/api.test.ts`:

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import { getFlaggedPos, postTriage } from "./api";

afterEach(() => vi.restoreAllMocks());

describe("api client", () => {
  it("fetches flagged POs", async () => {
    const payload = { count: 0, items: [] };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => payload }),
    );
    await expect(getFlaggedPos()).resolves.toEqual(payload);
  });

  it("posts a triage question", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ halt: null }) });
    vi.stubGlobal("fetch", fetchMock);
    await postTriage("PO-88405?");
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ question: "PO-88405?" });
  });

  it("throws on a non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(getFlaggedPos()).rejects.toThrow(/500/);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- api`
Expected: FAIL — cannot find `./api`.

- [ ] **Step 3: Write the implementation**

`frontend/lib/api.ts`:

```typescript
import { API_BASE_URL } from "./config";
import { FlaggedPosResponse, TriageResponse } from "./types";

export async function getFlaggedPos(
  signal?: AbortSignal,
): Promise<FlaggedPosResponse> {
  const response = await fetch(`${API_BASE_URL}/flagged-pos`, { signal });
  if (!response.ok) {
    throw new Error(`Failed to load flagged POs (${response.status})`);
  }
  return response.json();
}

export async function postTriage(
  question: string,
  signal?: AbortSignal,
): Promise<TriageResponse> {
  const response = await fetch(`${API_BASE_URL}/triage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  if (!response.ok) {
    throw new Error(`Triage failed (${response.status})`);
  }
  return response.json();
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test -- api`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/api.test.ts
git commit -m "feat(ui): add typed API client for flagged POs and triage"
```

---

## Task 8: Left panel — flagged-PO list

**Files:** create `frontend/components/PoRow.tsx`, `frontend/components/FlaggedPoList.tsx`, `frontend/components/FlaggedPoList.test.tsx`.

**Interfaces:**
- Consumes: `FlaggedPo`, `TierBadge`.
- Produces: `<FlaggedPoList items selectedPoId onSelect />` with an internal filter by `po_id` or `supplier`; `<PoRow po selected onSelect />`.

- [ ] **Step 1: Write the failing test**

`frontend/components/FlaggedPoList.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FlaggedPoList } from "./FlaggedPoList";
import type { FlaggedPo } from "@/lib/types";

const items: FlaggedPo[] = [
  {
    po_id: "PO-88405",
    supplier: "Anadolu Tekstil",
    category: "Womenswear",
    tier: "V2",
    tier_display: { number: 2, word: "Material" },
    qty_variance_pct: -12,
    eta_variance_days: 9,
    summary_line: "Short-ship -12% · ETA +9d",
    query: "PO-88405 came in short",
  },
  {
    po_id: "PO-88408",
    supplier: "Coastal Apparel Ltd",
    category: "Accessories",
    tier: "V3",
    tier_display: { number: 3, word: "Major" },
    qty_variance_pct: -22,
    eta_variance_days: null,
    summary_line: "Short-ship -22%",
    query: "PO-88408 wholesale short",
  },
];

describe("FlaggedPoList", () => {
  it("renders every PO with its summary", () => {
    render(<FlaggedPoList items={items} selectedPoId={null} onSelect={() => {}} />);
    expect(screen.getByText("PO-88405")).toBeInTheDocument();
    expect(screen.getByText("Short-ship -12% · ETA +9d")).toBeInTheDocument();
    expect(screen.getByText("PO-88408")).toBeInTheDocument();
  });

  it("filters by PO id or supplier", async () => {
    render(<FlaggedPoList items={items} selectedPoId={null} onSelect={() => {}} />);
    await userEvent.type(screen.getByPlaceholderText(/filter/i), "coastal");
    expect(screen.queryByText("PO-88405")).not.toBeInTheDocument();
    expect(screen.getByText("PO-88408")).toBeInTheDocument();
  });

  it("calls onSelect when a row is clicked", async () => {
    const onSelect = vi.fn();
    render(<FlaggedPoList items={items} selectedPoId={null} onSelect={onSelect} />);
    await userEvent.click(screen.getByText("PO-88405"));
    expect(onSelect).toHaveBeenCalledWith(items[0]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- FlaggedPoList`
Expected: FAIL — cannot find `./FlaggedPoList`.

- [ ] **Step 3: Write `PoRow`**

`frontend/components/PoRow.tsx`:

```tsx
import { FlaggedPo } from "@/lib/types";
import { TierBadge } from "./TierBadge";

export function PoRow({
  po,
  selected,
  onSelect,
}: {
  po: FlaggedPo;
  selected: boolean;
  onSelect: (po: FlaggedPo) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(po)}
      className={`w-full rounded-lg border px-3 py-2.5 text-left transition ${
        selected
          ? "border-rose-500/70 bg-slate-800/80"
          : "border-transparent bg-slate-900/40 hover:bg-slate-800/50"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-100">{po.po_id}</span>
        <TierBadge number={po.tier_display.number} word={po.tier_display.word} />
      </div>
      <p className="mt-1 text-xs text-slate-400">{po.summary_line}</p>
    </button>
  );
}
```

- [ ] **Step 4: Write `FlaggedPoList`**

`frontend/components/FlaggedPoList.tsx`:

```tsx
"use client";

import { useMemo, useState } from "react";
import { FlaggedPo } from "@/lib/types";
import { PoRow } from "./PoRow";

export function FlaggedPoList({
  items,
  selectedPoId,
  onSelect,
}: {
  items: FlaggedPo[];
  selectedPoId: string | null;
  onSelect: (po: FlaggedPo) => void;
}) {
  const [filter, setFilter] = useState("");

  const filtered = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return items;
    return items.filter(
      (po) =>
        po.po_id.toLowerCase().includes(needle) ||
        po.supplier.toLowerCase().includes(needle),
    );
  }, [items, filter]);

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col gap-3 border-r border-slate-800 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Flagged POs</h2>
        <span className="text-xs text-slate-400">{items.length}</span>
      </div>
      <input
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
        placeholder="Filter by PO or supplier"
        className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-slate-500 focus:outline-none"
      />
      <div className="flex flex-col gap-1.5 overflow-y-auto">
        {filtered.map((po) => (
          <PoRow
            key={po.po_id}
            po={po}
            selected={po.po_id === selectedPoId}
            onSelect={onSelect}
          />
        ))}
      </div>
    </aside>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm run test -- FlaggedPoList`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/components/PoRow.tsx frontend/components/FlaggedPoList.tsx frontend/components/FlaggedPoList.test.tsx
git commit -m "feat(ui): add flagged-PO list with filter and selection"
```

---

## Task 9: Question bar + empty/skeleton/error states

**Files:** create `frontend/components/QuestionBar.tsx`, `frontend/components/states/EmptyState.tsx`, `frontend/components/states/ReportSkeleton.tsx`, `frontend/components/states/ErrorState.tsx`, `frontend/components/QuestionBar.test.tsx`.

**Interfaces:**
- Produces: `<QuestionBar value onChange onAsk loading />` (Ask disabled when empty/loading, Enter submits); `<EmptyState/>`, `<ReportSkeleton/>`, `<ErrorState message onRetry/>`.

- [ ] **Step 1: Write the failing test**

`frontend/components/QuestionBar.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QuestionBar } from "./QuestionBar";

describe("QuestionBar", () => {
  it("disables Ask when empty", () => {
    render(
      <QuestionBar value="   " onChange={() => {}} onAsk={() => {}} loading={false} />,
    );
    expect(screen.getByRole("button", { name: /ask/i })).toBeDisabled();
  });

  it("calls onAsk when clicked with text", async () => {
    const onAsk = vi.fn();
    render(
      <QuestionBar value="PO-88405?" onChange={() => {}} onAsk={onAsk} loading={false} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(onAsk).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- QuestionBar`
Expected: FAIL — cannot find `./QuestionBar`.

- [ ] **Step 3: Write `QuestionBar`**

`frontend/components/QuestionBar.tsx`:

```tsx
export function QuestionBar({
  value,
  onChange,
  onAsk,
  loading,
}: {
  value: string;
  onChange: (value: string) => void;
  onAsk: () => void;
  loading: boolean;
}) {
  const disabled = loading || value.trim().length === 0;
  return (
    <div className="flex items-center gap-3 border-b border-slate-800 p-4">
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !disabled) onAsk();
        }}
        placeholder="Ask about the selected PO…"
        className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-slate-500 focus:outline-none"
      />
      <button
        type="button"
        onClick={onAsk}
        disabled={disabled}
        className="rounded-md bg-blue-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading ? "Asking…" : "Ask"}
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Write the state components**

`frontend/components/states/EmptyState.tsx`:

```tsx
export function EmptyState({ poId }: { poId: string | null }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-slate-500">
      <p className="text-lg font-medium text-slate-300">
        {poId ? `${poId} selected` : "Select a flagged PO"}
      </p>
      <p className="text-sm">Ask a question to run triage and see the recommendation.</p>
    </div>
  );
}
```

`frontend/components/states/ReportSkeleton.tsx`:

```tsx
import { Skeleton } from "../ui/Skeleton";

export function ReportSkeleton() {
  return (
    <div className="grid grid-cols-[1fr_18rem] gap-6 p-6">
      <div className="flex flex-col gap-4">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-10 w-3/4" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
      <div className="flex flex-col gap-4">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    </div>
  );
}
```

`frontend/components/states/ErrorState.tsx`:

```tsx
export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
      <p className="text-sm text-rose-400">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="rounded-md border border-slate-700 px-4 py-1.5 text-sm text-slate-200 hover:bg-slate-800"
      >
        Retry
      </button>
    </div>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm run test -- QuestionBar`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/QuestionBar.tsx frontend/components/states frontend/components/QuestionBar.test.tsx
git commit -m "feat(ui): add question bar and empty/skeleton/error states"
```

---

## Task 10: Report view

**Files:** create `frontend/components/report/RecommendedActionHeader.tsx`, `StatsRow.tsx`, `ExceptionTypeChips.tsx`, `ConfidenceCard.tsx`, `EscalationCard.tsx`, `ActionButtons.tsx`, `PolicyCitations.tsx`, `Report.tsx`, and `frontend/components/report/Report.test.tsx`.

**Interfaces:**
- Consumes: `TriageResponse`, format helpers, `TierBadge`.
- Produces: `<Report result />` rendering the full recommendation layout.

- [ ] **Step 1: Write the failing test**

`frontend/components/report/Report.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Report } from "./Report";
import type { TriageResponse } from "@/lib/types";

const result: TriageResponse = {
  halt: null,
  triage: {
    po_id: "PO-88405",
    halt: null,
    planner_question: "PO-88405?",
    po_record: { ordered_qty: 5000, confirmed_qty: 4400 },
    forecast: null,
    tier: {
      tier: "V2",
      qty_variance_pct: -12,
      eta_variance_days: 9,
      value_at_risk_gbp: 22800,
      overrides_applied: [],
      validation: { passed: true, failures: [] },
    },
    exception_types: ["quantity_variance_short", "eta_slip"],
    queries: [],
  },
  recommendation: {
    po_id: "PO-88405",
    recommended_action: "amend",
    rationale: "V2 short-ship within amendment tolerance.",
    citations: ["variance_detection_sop.md §2.1"],
    confidence: "high",
    escalation_target_role: "Senior Merchandiser",
  },
  citations: [
    {
      code: "MERCH-SOP-014",
      section: "§2.1",
      title: "Compound variance rule",
      quote: "Where a PO carries two or more concurrent V1 variances…",
    },
  ],
};

describe("Report", () => {
  it("renders action headline, stats, chips, confidence, escalation and citation", () => {
    render(<Report result={result} />);
    expect(screen.getByText("Amend the purchase order")).toBeInTheDocument();
    expect(screen.getByText("5,000")).toBeInTheDocument();
    expect(screen.getByText("-12.0%")).toBeInTheDocument();
    expect(screen.getByText("+9d")).toBeInTheDocument();
    expect(screen.getByText("Short-ship")).toBeInTheDocument();
    expect(screen.getByText(/high/i)).toBeInTheDocument();
    expect(screen.getByText("Senior Merchandiser")).toBeInTheDocument();
    expect(screen.getByText(/MERCH-SOP-014 §2.1/)).toBeInTheDocument();
    expect(screen.getByText("Compound variance rule")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- Report`
Expected: FAIL — cannot find `./Report`.

- [ ] **Step 3: Write the report subcomponents**

`frontend/components/report/RecommendedActionHeader.tsx`:

```tsx
import { Recommendation, TierResult } from "@/lib/types";
import { actionHeadline } from "@/lib/format";
import { TierBadge } from "../TierBadge";

const TIER_WORDS = ["Clean", "Minor", "Material", "Major", "Critical"];

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
```

`frontend/components/report/StatsRow.tsx`:

```tsx
import { TierResult } from "@/lib/types";
import { formatEtaDays, formatPct, formatQty } from "@/lib/format";

function Stat({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-slate-500">{label}</span>
      <span className={`text-lg font-semibold ${danger ? "text-rose-400" : "text-slate-100"}`}>
        {value}
      </span>
    </div>
  );
}

export function StatsRow({
  record,
  tier,
}: {
  record: Record<string, unknown> | null;
  tier: TierResult | null;
}) {
  const ordered = (record?.ordered_qty as number | undefined) ?? null;
  const confirmed = (record?.confirmed_qty as number | undefined) ?? null;
  return (
    <div className="flex gap-10 rounded-lg border border-slate-800 bg-slate-900/40 px-5 py-4">
      <Stat label="Ordered" value={formatQty(ordered)} />
      <Stat label="Confirmed" value={formatQty(confirmed)} />
      <Stat label="Variance" value={formatPct(tier?.qty_variance_pct ?? null)} danger />
      <Stat label="ETA" value={formatEtaDays(tier?.eta_variance_days ?? null)} />
    </div>
  );
}
```

`frontend/components/report/ExceptionTypeChips.tsx`:

```tsx
import { ExceptionType } from "@/lib/types";
import { EXCEPTION_LABELS } from "@/lib/format";
import { Badge } from "../ui/Badge";

export function ExceptionTypeChips({ types }: { types: ExceptionType[] }) {
  if (types.length === 0) return null;
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Exception types
      </h3>
      <div className="flex flex-wrap gap-2">
        {types.map((type) => (
          <Badge key={type} className="bg-slate-800 text-slate-200">
            {EXCEPTION_LABELS[type]}
          </Badge>
        ))}
      </div>
    </div>
  );
}
```

`frontend/components/report/ConfidenceCard.tsx`:

```tsx
import { Citation, Confidence } from "@/lib/types";
import { confidenceFill } from "@/lib/format";

export function ConfidenceCard({
  confidence,
  citations,
}: {
  confidence: Confidence;
  citations: Citation[];
}) {
  const note =
    citations.length > 0
      ? `${citations.length} cited clause${citations.length > 1 ? "s" : ""} matched.`
      : "No policy clause was cited.";
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Confidence
      </h3>
      <p className="mt-1 text-xl font-bold capitalize text-slate-100">{confidence}</p>
      <div className="mt-2 h-1.5 w-full rounded-full bg-slate-800">
        <div
          className="h-1.5 rounded-full bg-blue-500"
          style={{ width: `${confidenceFill(confidence)}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-slate-400">{note}</p>
    </div>
  );
}
```

`frontend/components/report/EscalationCard.tsx`:

```tsx
export function EscalationCard({ role }: { role: string | null }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        If you need to escalate
      </h3>
      <p className="mt-1 text-sm font-semibold text-slate-100">
        {role ?? "No escalation required"}
      </p>
      {role && (
        <p className="mt-1 text-xs text-slate-400">
          Role only — no personal contact data.
        </p>
      )}
    </div>
  );
}
```

`frontend/components/report/ActionButtons.tsx`:

```tsx
"use client";

export function ActionButtons({ summary }: { summary: string }) {
  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={() => navigator.clipboard?.writeText(summary)}
        className="rounded-md border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
      >
        Copy summary
      </button>
      <button
        type="button"
        disabled
        title="ERP integration not available in this demo"
        className="rounded-md border border-slate-800 px-4 py-2 text-sm text-slate-500"
      >
        Open PO in ERP
      </button>
    </div>
  );
}
```

`frontend/components/report/PolicyCitations.tsx`:

```tsx
import { Citation } from "@/lib/types";

export function PolicyCitations({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Policy citations
      </h3>
      <div className="flex flex-col gap-2">
        {citations.map((citation, index) => (
          <div
            key={`${citation.code}-${citation.section}-${index}`}
            className="rounded-lg border border-slate-800 bg-slate-900/40 p-4"
          >
            <p className="text-sm font-semibold text-slate-200">
              {`${citation.code} ${citation.section}`.trim()}
              {citation.title ? ` — ${citation.title}` : ""}
            </p>
            {citation.quote && (
              <p className="mt-1 text-xs italic leading-relaxed text-slate-400">
                “{citation.quote}”
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Write the `Report` container**

`frontend/components/report/Report.tsx`:

```tsx
import { TriageResponse } from "@/lib/types";
import { actionHeadline } from "@/lib/format";
import { RecommendedActionHeader } from "./RecommendedActionHeader";
import { StatsRow } from "./StatsRow";
import { PolicyCitations } from "./PolicyCitations";
import { ConfidenceCard } from "./ConfidenceCard";
import { EscalationCard } from "./EscalationCard";
import { ExceptionTypeChips } from "./ExceptionTypeChips";
import { ActionButtons } from "./ActionButtons";

export function Report({ result }: { result: TriageResponse }) {
  const { triage, recommendation, citations } = result;
  const summary = `${triage.po_id}: ${actionHeadline(
    recommendation.recommended_action,
  )} — ${recommendation.rationale}`;

  return (
    <div className="grid grid-cols-[1fr_18rem] gap-6 p-6">
      <div className="flex flex-col gap-5">
        <RecommendedActionHeader recommendation={recommendation} tier={triage.tier} />
        <StatsRow record={triage.po_record} tier={triage.tier} />
        <PolicyCitations citations={citations} />
      </div>
      <div className="flex flex-col gap-4">
        <ConfidenceCard confidence={recommendation.confidence} citations={citations} />
        <EscalationCard role={recommendation.escalation_target_role} />
        <ExceptionTypeChips types={triage.exception_types} />
        <ActionButtons summary={summary} />
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm run test -- Report`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/report
git commit -m "feat(ui): add grounded recommendation report view"
```

---

## Task 11: Edge-state panel + ReportPanel switch

**Files:** create `frontend/components/EdgeStatePanel.tsx`, `frontend/components/ReportPanel.tsx`, `frontend/components/ReportPanel.test.tsx`.

**Interfaces:**
- Consumes: `TriageResponse`, `Report`, `EmptyState`, `ReportSkeleton`, `ErrorState`.
- Produces: `<EdgeStatePanel result />`; `<ReportPanel phase result error selectedPoId onRetry />` where `phase: "empty" | "loading" | "done" | "error"`. When `phase === "done"` and `result.halt` is set, render `EdgeStatePanel`; otherwise `Report`.

- [ ] **Step 1: Write the failing test**

`frontend/components/ReportPanel.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReportPanel } from "./ReportPanel";
import type { TriageResponse } from "@/lib/types";

function haltResult(): TriageResponse {
  return {
    halt: "data_quality",
    triage: {
      po_id: "PO-88416",
      halt: "data_quality",
      planner_question: "PO-88416?",
      po_record: { ordered_qty: 3200, confirmed_qty: 3050 },
      forecast: null,
      tier: {
        tier: "V2",
        qty_variance_pct: -4.7,
        eta_variance_days: null,
        value_at_risk_gbp: 3300,
        overrides_applied: [],
        validation: { passed: false, failures: ["eta is null on a CONFIRMED PO"] },
      },
      exception_types: [],
      queries: [],
    },
    recommendation: {
      po_id: "PO-88416",
      recommended_action: "escalate",
      rationale: "Record fails data-quality checks; cannot recommend.",
      citations: [],
      confidence: "low",
      escalation_target_role: "Intake Planning Lead",
    },
    citations: [],
  };
}

describe("ReportPanel", () => {
  it("shows the empty state", () => {
    render(
      <ReportPanel phase="empty" selectedPoId="PO-88405" onRetry={() => {}} />,
    );
    expect(screen.getByText(/ask a question/i)).toBeInTheDocument();
  });

  it("renders the edge-state panel on halt", () => {
    render(
      <ReportPanel
        phase="done"
        result={haltResult()}
        selectedPoId="PO-88416"
        onRetry={() => {}}
      />,
    );
    expect(screen.getByText(/can't auto-recommend/i)).toBeInTheDocument();
    expect(screen.getByText(/data.quality/i)).toBeInTheDocument();
    expect(screen.getByText("Intake Planning Lead")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- ReportPanel`
Expected: FAIL — cannot find `./ReportPanel`.

- [ ] **Step 3: Write `EdgeStatePanel`**

`frontend/components/EdgeStatePanel.tsx`:

```tsx
import { TriageResponse } from "@/lib/types";
import { formatEtaDays, formatPct, formatQty } from "@/lib/format";
import { EscalationCard } from "./report/EscalationCard";

const HALT_LABELS: Record<string, string> = {
  data_quality: "Data-quality failure",
  terminal_status: "Terminal status",
  unresolved_po: "PO could not be resolved",
};

export function EdgeStatePanel({ result }: { result: TriageResponse }) {
  const { triage, recommendation } = result;
  const failures = triage.tier?.validation.failures ?? [];
  const haltKey = result.halt ?? "unresolved_po";

  return (
    <div className="grid grid-cols-[1fr_18rem] gap-6 p-6">
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-amber-500">
            Can't auto-recommend
          </span>
          <h1 className="text-2xl font-bold text-slate-50">{HALT_LABELS[haltKey]}</h1>
          <p className="text-sm leading-relaxed text-slate-300">
            {recommendation.rationale}
          </p>
        </div>

        {failures.length > 0 && (
          <ul className="list-inside list-disc rounded-lg border border-amber-900/50 bg-amber-950/20 p-4 text-sm text-amber-200">
            {failures.map((failure) => (
              <li key={failure}>{failure}</li>
            ))}
          </ul>
        )}

        <div className="flex gap-10 rounded-lg border border-slate-800 bg-slate-900/40 px-5 py-4">
          <Fact label="Ordered" value={formatQty(triage.po_record?.ordered_qty as number)} />
          <Fact
            label="Confirmed"
            value={formatQty(triage.po_record?.confirmed_qty as number)}
          />
          <Fact label="Variance" value={formatPct(triage.tier?.qty_variance_pct ?? null)} />
          <Fact label="ETA" value={formatEtaDays(triage.tier?.eta_variance_days ?? null)} />
        </div>
      </div>
      <div className="flex flex-col gap-4">
        <EscalationCard role={recommendation.escalation_target_role} />
      </div>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-slate-500">{label}</span>
      <span className="text-lg font-semibold text-slate-100">{value}</span>
    </div>
  );
}
```

- [ ] **Step 4: Write `ReportPanel`**

`frontend/components/ReportPanel.tsx`:

```tsx
import { TriageResponse } from "@/lib/types";
import { Report } from "./report/Report";
import { EdgeStatePanel } from "./EdgeStatePanel";
import { EmptyState } from "./states/EmptyState";
import { ReportSkeleton } from "./states/ReportSkeleton";
import { ErrorState } from "./states/ErrorState";

export type ReportPhase = "empty" | "loading" | "done" | "error";

export function ReportPanel({
  phase,
  result,
  error,
  selectedPoId,
  onRetry,
}: {
  phase: ReportPhase;
  result?: TriageResponse;
  error?: string;
  selectedPoId: string | null;
  onRetry: () => void;
}) {
  if (phase === "loading") return <ReportSkeleton />;
  if (phase === "error") {
    return <ErrorState message={error ?? "Something went wrong."} onRetry={onRetry} />;
  }
  if (phase === "done" && result) {
    return result.halt ? <EdgeStatePanel result={result} /> : <Report result={result} />;
  }
  return <EmptyState poId={selectedPoId} />;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm run test -- ReportPanel`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/EdgeStatePanel.tsx frontend/components/ReportPanel.tsx frontend/components/ReportPanel.test.tsx
git commit -m "feat(ui): add edge-state panel and report panel state switch"
```

---

## Task 12: Page wiring

**Files:** modify `frontend/app/page.tsx`; create `frontend/app/page.test.tsx`.

**Interfaces:**
- Consumes: `getFlaggedPos`, `postTriage`, `FlaggedPoList`, `QuestionBar`, `ReportPanel`.
- Produces: the wired dashboard: fetch flagged POs on mount; clicking a PO selects it, sets phase `empty`, and prefills the question; Ask runs `postTriage`, showing `loading` then `done`/`error`.

- [ ] **Step 1: Write the failing test**

`frontend/app/page.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "./page";
import * as api from "@/lib/api";
import type { FlaggedPo, TriageResponse } from "@/lib/types";

const po: FlaggedPo = {
  po_id: "PO-88405",
  supplier: "Anadolu Tekstil",
  category: "Womenswear",
  tier: "V2",
  tier_display: { number: 2, word: "Material" },
  qty_variance_pct: -12,
  eta_variance_days: 9,
  summary_line: "Short-ship -12% · ETA +9d",
  query: "PO-88405 came in short and the ETA slipped, what's going on?",
};

const triage: TriageResponse = {
  halt: null,
  triage: {
    po_id: "PO-88405",
    halt: null,
    planner_question: po.query,
    po_record: { ordered_qty: 5000, confirmed_qty: 4400 },
    forecast: null,
    tier: {
      tier: "V2",
      qty_variance_pct: -12,
      eta_variance_days: 9,
      value_at_risk_gbp: 22800,
      overrides_applied: [],
      validation: { passed: true, failures: [] },
    },
    exception_types: ["quantity_variance_short"],
    queries: [],
  },
  recommendation: {
    po_id: "PO-88405",
    recommended_action: "amend",
    rationale: "V2 short-ship within amendment tolerance.",
    citations: [],
    confidence: "high",
    escalation_target_role: null,
  },
  citations: [],
};

beforeEach(() => {
  vi.spyOn(api, "getFlaggedPos").mockResolvedValue({ count: 1, items: [po] });
  vi.spyOn(api, "postTriage").mockResolvedValue(triage);
});

describe("Page", () => {
  it("loads POs, prefills on select, and renders the report after Ask", async () => {
    render(<Page />);
    await waitFor(() => expect(screen.getByText("PO-88405")).toBeInTheDocument());

    await userEvent.click(screen.getByText("PO-88405"));
    expect(screen.getByDisplayValue(po.query)).toBeInTheDocument();
    expect(screen.getByText(/ask a question/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /ask/i }));
    await waitFor(() =>
      expect(screen.getByText("Amend the purchase order")).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- page`
Expected: FAIL — current placeholder page renders neither the list nor the report.

- [ ] **Step 3: Write the wired page**

Replace `frontend/app/page.tsx` with:

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import { getFlaggedPos, postTriage } from "@/lib/api";
import { FlaggedPo, TriageResponse } from "@/lib/types";
import { FlaggedPoList } from "@/components/FlaggedPoList";
import { QuestionBar } from "@/components/QuestionBar";
import { ReportPanel, ReportPhase } from "@/components/ReportPanel";

export default function Page() {
  const [items, setItems] = useState<FlaggedPo[]>([]);
  const [selected, setSelected] = useState<FlaggedPo | null>(null);
  const [question, setQuestion] = useState("");
  const [phase, setPhase] = useState<ReportPhase>("empty");
  const [result, setResult] = useState<TriageResponse | undefined>(undefined);
  const [error, setError] = useState<string | undefined>(undefined);

  useEffect(() => {
    getFlaggedPos()
      .then((response) => setItems(response.items))
      .catch((err: Error) => setError(err.message));
  }, []);

  const onSelect = useCallback((po: FlaggedPo) => {
    setSelected(po);
    setQuestion(po.query);
    setResult(undefined);
    setError(undefined);
    setPhase("empty");
  }, []);

  const onAsk = useCallback(async () => {
    setPhase("loading");
    setError(undefined);
    try {
      const response = await postTriage(question);
      setResult(response);
      setPhase("done");
    } catch (err) {
      setError((err as Error).message);
      setPhase("error");
    }
  }, [question]);

  return (
    <main className="flex h-screen">
      <FlaggedPoList
        items={items}
        selectedPoId={selected?.po_id ?? null}
        onSelect={onSelect}
      />
      <section className="flex min-w-0 flex-1 flex-col">
        <QuestionBar
          value={question}
          onChange={setQuestion}
          onAsk={onAsk}
          loading={phase === "loading"}
        />
        <div className="min-h-0 flex-1 overflow-y-auto">
          <ReportPanel
            phase={phase}
            result={result}
            error={error}
            selectedPoId={selected?.po_id ?? null}
            onRetry={onAsk}
          />
        </div>
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test -- page`
Expected: PASS.

- [ ] **Step 5: Run the full frontend suite + typecheck**

Run: `npm run typecheck && npm run test`
Expected: all PASS, typecheck clean.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/page.tsx frontend/app/page.test.tsx
git commit -m "feat(ui): wire dashboard — load POs, prefill on select, run triage"
```

---

## Task 13: End-to-end happy path + README

**Files:** create `frontend/playwright.config.ts`, `frontend/e2e/happy-path.spec.ts`, `frontend/README.md`.

**Interfaces:**
- Consumes: the running Next app; network is intercepted so no backend/model is required.

- [ ] **Step 1: Create the Playwright config**

`frontend/playwright.config.ts`:

```typescript
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: "http://localhost:3000" },
  webServer: {
    command: "npm run build && npm run start",
    url: "http://localhost:3000",
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
  },
});
```

- [ ] **Step 2: Write the e2e spec (network intercepted)**

`frontend/e2e/happy-path.spec.ts`:

```typescript
import { expect, test } from "@playwright/test";

const flagged = {
  count: 1,
  items: [
    {
      po_id: "PO-88405",
      supplier: "Anadolu Tekstil",
      category: "Womenswear",
      tier: "V2",
      tier_display: { number: 2, word: "Material" },
      qty_variance_pct: -12,
      eta_variance_days: 9,
      summary_line: "Short-ship -12% · ETA +9d",
      query: "PO-88405 came in short and the ETA slipped, what's going on?",
    },
  ],
};

const triage = {
  halt: null,
  triage: {
    po_id: "PO-88405",
    halt: null,
    planner_question: flagged.items[0].query,
    po_record: { ordered_qty: 5000, confirmed_qty: 4400 },
    forecast: null,
    tier: {
      tier: "V2",
      qty_variance_pct: -12,
      eta_variance_days: 9,
      value_at_risk_gbp: 22800,
      overrides_applied: [],
      validation: { passed: true, failures: [] },
    },
    exception_types: ["quantity_variance_short", "eta_slip"],
    queries: [],
  },
  recommendation: {
    po_id: "PO-88405",
    recommended_action: "amend",
    rationale: "V2 short-ship within amendment tolerance.",
    citations: ["variance_detection_sop.md §2.1"],
    confidence: "high",
    escalation_target_role: "Senior Merchandiser",
  },
  citations: [
    {
      code: "MERCH-SOP-014",
      section: "§2.1",
      title: "Compound variance rule",
      quote: "Where a PO carries two or more concurrent V1 variances…",
    },
  ],
};

test("planner selects a PO, asks, and sees the recommendation", async ({ page }) => {
  await page.route("**/flagged-pos", (route) =>
    route.fulfill({ json: flagged }),
  );
  await page.route("**/triage", (route) => route.fulfill({ json: triage }));

  await page.goto("/");
  await page.getByText("PO-88405").click();
  await expect(page.getByText(/ask a question/i)).toBeVisible();

  await page.getByRole("button", { name: /ask/i }).click();
  await expect(page.getByText("Amend the purchase order")).toBeVisible();
  await expect(page.getByText("Compound variance rule")).toBeVisible();
});
```

- [ ] **Step 3: Install browsers and run the e2e**

Run (from `frontend/`):

```bash
npx playwright install --with-deps chromium
npm run e2e
```

Expected: 1 test PASS.

- [ ] **Step 4: Write the README**

`frontend/README.md`:

```markdown
# PO Exception Triage — UI

Next.js dashboard for the PO exception triage agent.

## Run

1. **Backend** (from `../backend`):
   ```bash
   pip install -r requirements.txt
   copy .env.example .env   # add OPENAI_API_KEY
   uvicorn src.api:app --reload --port 8000
   ```
2. **Frontend** (from here):
   ```bash
   npm install
   copy .env.local.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   npm run dev
   ```
3. Open http://localhost:3000

## Test

```bash
npm run test        # unit/component (Vitest)
npm run e2e         # end-to-end (Playwright, network mocked)
npm run typecheck
```

The first `/triage` call downloads the embedding model and builds the SOP index on the
backend; subsequent calls reuse the cache.
```

- [ ] **Step 5: Commit**

```bash
git add frontend/playwright.config.ts frontend/e2e frontend/README.md
git commit -m "test(ui): add Playwright happy-path e2e and run docs"
```

---

## Manual verification (after all tasks)

- [ ] Start backend: `cd backend && uvicorn src.api:app --port 8000`. Confirm `GET http://localhost:8000/flagged-pos` returns 13 items.
- [ ] Start frontend: `cd frontend && npm run dev`. Open http://localhost:3000.
- [ ] Click **PO-88405** → main panel shows the empty state; the question is prefilled.
- [ ] Click **Ask** → skeleton, then the grounded report with tier badge, stats, citations (with quoted clauses), categorical confidence, and role-only escalation.
- [ ] Click **PO-88416** (missing ETA) → Ask → the **edge-state** panel (data-quality failure + escalate).

---

## Self-Review (completed)

**1. Spec coverage:**
- Full-stack FastAPI + Next.js → Tasks 1–13. ✓
- Deterministic `GET /flagged-pos` reusing `compute_variance_tier` → Task 3. ✓
- Single `POST /triage` + skeleton → Tasks 4, 9, 11. ✓
- Categorical confidence → Task 10 (`ConfidenceCard`). ✓
- Dedicated halt/edge-state panel → Task 11. ✓
- Backend-resolved citations `{code, section, title, quote}` → Task 2. ✓
- Prefill on select; count = 13; role-only escalation; no frontend secrets → Tasks 12, 8, 10, 5. ✓
- Tier/action/exception/confidence mappings → Task 6. ✓
- Testing (backend pytest incl. mocked graph; frontend Vitest + Playwright) → Tasks 1–13. ✓

**2. Placeholder scan:** No TBD/TODO; every code step contains complete code. ✓

**3. Type consistency:** `FlaggedPo`, `TriageResponse`, `Citation`, `ReportPhase`, and helper signatures are used identically across backend (`api_schemas.py`) and frontend (`lib/types.ts`). The graph contract (`invoke(state) -> {final_output, recommendation}`) matches `main.py` and the `_FakeGraph` used in tests. ✓

**Deviation from spec:** shadcn/ui replaced by Tailwind + minimal local primitives for reproducibility (noted in File Structure). Same visual intent; can be swapped later.
