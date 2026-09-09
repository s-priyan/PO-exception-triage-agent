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
