"""Tests for paper_pdf_handoff manifest + resume instruction template."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

# Make scripts/ importable (flattened release layout)
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_write_manifest_creates_csv(tmp_path):
    from paper_pdf_handoff import write_manifest
    rows = [
        {"doi": "10.1038/example1", "citekey": "Ex2025Example1",
         "why_needed": "verify H1a mechanism", "expected_section": "methods+results",
         "resume_token": "audit-001"},
        {"doi": "10.1002/example2", "citekey": "Ex2025Example2",
         "why_needed": "discriminating experiment baseline", "expected_section": "discussion",
         "resume_token": "audit-001"},
    ]
    out_path = tmp_path / "pdf_handoff_audit-001.csv"
    write_manifest(out_path, rows)
    assert out_path.exists()
    with out_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        loaded = list(reader)
    assert len(loaded) == 2
    assert loaded[0]["doi"] == "10.1038/example1"


def test_write_manifest_rejects_more_than_5_doi(tmp_path):
    """Spec 4.8.3: <=5 DOI per manifest to prevent batch misuse."""
    import pytest
    from paper_pdf_handoff import write_manifest
    rows = [{"doi": f"10.1/x{i}", "citekey": f"x{i}", "why_needed": "x",
             "expected_section": "x", "resume_token": "t"} for i in range(6)]
    with pytest.raises(ValueError, match="max 5"):
        write_manifest(tmp_path / "too_many.csv", rows)


def test_render_resume_instruction_includes_manifest_path():
    from paper_pdf_handoff import render_resume_instruction
    md = render_resume_instruction(
        manifest_path=Path("/abs/path/pdf_handoff_audit-001.csv"),
        audit_log_id="audit-001",
        doi_list=["10.1038/a", "10.1002/b"],
    )
    assert "/abs/path/pdf_handoff_audit-001.csv" in md or "\\abs\\path\\pdf_handoff_audit-001.csv" in md
    assert "audit-001" in md
    assert "10.1038/a" in md
    assert "10.1002/b" in md
    assert "/paper-pdf-acquisition" in md
