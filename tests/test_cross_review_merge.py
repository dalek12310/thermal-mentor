"""Tests for cross_review_merge: finding classification + DOI non-discriminatory attribution."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make scripts/ importable (flattened release layout)
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


SAMPLE_REVIEWS = {
    "opus": {
        "findings": [
            {"id": "F1", "text": "Step 0.5 不强制 ack 与 self-correcting 矛盾",
             "severity": "high"},
            {"id": "F2", "text": "DOI fallback 语义", "severity": "high"},
        ],
        "introduced_refs": [],
    },
    "codex": {
        "findings": [
            {"id": "C1", "text": "cross_review.py 误建模为脚本",
             "severity": "critical"},
            {"id": "C2", "text": "DOI fallback 语义",  # 与 Opus F2 同
             "severity": "high"},
        ],
        "introduced_refs": [{"value": "10.1038/codex_intro", "ref_type": "doi"}],
    },
    "ds": {
        "findings": [
            {"id": "D1", "text": "framing drift — idea-critique 缺失",
             "severity": "high"},
        ],
        "introduced_refs": [{"value": "10.1103/ds_intro", "ref_type": "doi"}],
    },
}


def test_classify_findings_consensus_majority_singleton():
    """Findings overlapping across reviewers -> consensus high/medium/low."""
    from cross_review_merge import classify_findings
    cls = classify_findings(SAMPLE_REVIEWS)

    high_count = sum(1 for f in cls if f["confidence"] == "high")
    medium_count = sum(1 for f in cls if f["confidence"] == "medium")
    low_count = sum(1 for f in cls if f["confidence"] == "low")

    # 2 reviewers agree on "DOI fallback 语义" -> medium
    assert medium_count >= 1
    # F1, C1, D1 each unique -> low
    assert low_count >= 3


def test_doi_attribution_symmetric():
    """All reviewers' introduced refs get source attribution, NOT only DS."""
    from cross_review_merge import attribute_refs
    attributions = attribute_refs(SAMPLE_REVIEWS)
    # Codex 引入的 DOI 应该有 attribution
    codex_doi = "10.1038/codex_intro"
    assert codex_doi in attributions
    assert attributions[codex_doi] == "codex"
    # DS 引入的 DOI 也有 attribution (但不再写'高风险')
    ds_doi = "10.1103/ds_intro"
    assert ds_doi in attributions
    assert attributions[ds_doi] == "ds"
    # 不应该有任何 ref 标 "high_risk" 或类似贬义词
    for ref, attrib in attributions.items():
        assert "high_risk" not in attrib.lower()
        assert "fabricat" not in attrib.lower()


def test_merge_with_doi_verification(monkeypatch):
    """All introduced refs go through verify_doi_multisource,
    failed verification -> removed, but finding 论点 retained."""
    from doi_verify_multisource import DoiCheckResult

    verify_calls = []
    def fake_verify(doi):
        verify_calls.append(doi)
        if "codex_intro" in doi:
            return DoiCheckResult("verified", "openalex", {"id": "W1"}, None)
        elif "ds_intro" in doi:
            return DoiCheckResult("not_found", "crossref", None, None)
        return DoiCheckResult("verifier_error", "all_sources_failed", None, {})
    monkeypatch.setattr("cross_review_merge.verify_doi_multisource", fake_verify)

    from cross_review_merge import merge_reviews
    merged = merge_reviews(SAMPLE_REVIEWS)

    # Codex's verified DOI is preserved
    surviving_refs = merged["surviving_refs"]
    assert any(r["value"] == "10.1038/codex_intro" for r in surviving_refs)
    # DS's not_found DOI is removed from surviving_refs
    assert not any(r["value"] == "10.1103/ds_intro" for r in surviving_refs)
    # BUT D1 finding (architectural claim) is still in findings list
    finding_texts = [f["text"] for f in merged["findings"]]
    assert any("idea-critique" in t for t in finding_texts)

    # deleted_refs records the removed DOI
    assert "10.1103/ds_intro" in [r["value"] for r in merged["deleted_refs"]]


def test_cli_writes_merged_json_and_md(tmp_path, monkeypatch):
    """CLI reads N reviewer JSONs, writes merged final.json + final.md."""
    import json
    import subprocess
    import sys

    # Prepare 2 reviewer JSON files
    r1 = tmp_path / "round1_opus.json"
    r1.write_text(json.dumps({
        "reviewer": "opus",
        "findings": [{"id": "F1", "text": "issue A", "severity": "high"}],
        "introduced_refs": [],
    }), encoding="utf-8")
    r2 = tmp_path / "round1_ds.json"
    r2.write_text(json.dumps({
        "reviewer": "ds",
        "findings": [{"id": "D1", "text": "issue B", "severity": "medium"}],
        "introduced_refs": [],
    }), encoding="utf-8")

    out_json = tmp_path / "final.json"

    # Locate the script
    from pathlib import Path
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "cross_review_merge.py"

    result = subprocess.run(
        [sys.executable, str(script_path), str(r1), str(r2), "--out", str(out_json)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, f"CLI failed: stderr={result.stderr}"
    assert out_json.exists()
    out_md = out_json.with_suffix(".md")
    assert out_md.exists()

    merged = json.loads(out_json.read_text(encoding="utf-8"))
    assert "findings" in merged
    assert len(merged["findings"]) == 2  # one from each reviewer (both singleton low)
    assert set(merged["reviewers_used"]) == {"opus", "ds"}
