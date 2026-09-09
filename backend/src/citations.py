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
