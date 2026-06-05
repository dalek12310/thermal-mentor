"""Tests for verifier mode dispatch + DoiCheckResult adapter."""
from __future__ import annotations

import sys
from pathlib import Path

# Make scripts/ importable (flattened release layout)
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_legacy_doi_status_verified():
    from doi_verify_multisource import DoiCheckResult
    from verifier import doi_result_to_v01_status
    r = DoiCheckResult("verified", "openalex", {"id": "W1"}, None)
    assert doi_result_to_v01_status(r) == "verified"


def test_legacy_doi_status_not_found():
    from doi_verify_multisource import DoiCheckResult
    from verifier import doi_result_to_v01_status
    r = DoiCheckResult("not_found", "crossref", None, None)
    assert doi_result_to_v01_status(r) == "not_found"


def test_legacy_doi_status_verifier_error_maps_to_external_unverified():
    """Backwards-compat: v0.1 publication renderer expects external_unverified
    string. verifier_error must map there, and Markdown layer显式标 网络问题。"""
    from doi_verify_multisource import DoiCheckResult
    from verifier import doi_result_to_v01_status
    r = DoiCheckResult("verifier_error", "all_sources_failed", None, {"errors": []})
    assert doi_result_to_v01_status(r) == "external_unverified"


def test_run_pipeline_dispatches_data_first_mode():
    """payload['mode'] == 'data_first' -> verify_mode_0 path."""
    import json
    from verifier import run_pipeline
    payload = {
        "mode": "data_first",
        "anomalies": [
            {
                "anomaly_id": "A1",
                "observation": "defect signal monotonic decrease",
                "data_evidence": [
                    {"source": "notes.txt", "quote_text": "...", "line_or_para": "7"}
                ],
            }
        ],
        "hypotheses": [],
        "experiments": [],
        "audit_log_id": "test-001",
    }
    result = run_pipeline(json.dumps(payload), run_sanity=False)
    assert "error" not in result
    # mode 0 不需要 publication schema 字段 (verdict / claims / prior_art_coverage)
    assert result["payload"]["anomalies"][0]["data_evidence"][0].get("verification_status") is not None


def test_run_pipeline_dispatches_publication_mode_unchanged():
    """payload['mode'] in publication set -> original verify_payload path."""
    import json
    from verifier import run_pipeline
    payload = {
        "mode": "novelty_review",
        "verdict": {"one_line": "...", "confidence": "medium"},
        "claims": [{"claim_id": "C1", "claim_text": "...", "supporting_refs": []}],
        "prior_art_coverage": {},
        "audit_log_id": "test-002",
    }
    result = run_pipeline(json.dumps(payload), run_sanity=False)
    assert "error" not in result
    assert result["payload"]["claims"][0]["claim_id"] == "C1"


def test_run_pipeline_accepts_utf8_bom_payload():
    """PowerShell 5 may write UTF-8 JSON with BOM; verifier should accept it."""
    import json
    from verifier import run_pipeline

    payload = {
        "mode": "data_first",
        "anomalies": [{"anomaly_id": "A1", "observation": "...", "data_evidence": []}],
        "hypotheses": [],
        "experiments": [],
        "audit_log_id": "test-bom",
    }
    result = run_pipeline("\ufeff" + json.dumps(payload), run_sanity=False)
    assert "error" not in result
    assert result["payload"]["audit_log_id"] == "test-bom"


def test_configure_stdout_utf8_calls_reconfigure_when_available(monkeypatch):
    """Windows consoles often default to GBK; CLI should request UTF-8 output."""
    from verifier import _configure_stdout_utf8

    class FakeStdout:
        def __init__(self):
            self.calls = []

        def reconfigure(self, **kwargs):
            self.calls.append(kwargs)

    fake = FakeStdout()
    monkeypatch.setattr("sys.stdout", fake)

    _configure_stdout_utf8()

    assert fake.calls == [{"encoding": "utf-8"}]


def test_citation_validity_excludes_verifier_error():
    """citation_validity_rate must NOT count verifier_error refs (network problem,
    not citation fabrication)."""
    from verifier import _compute_validity
    payload = {
        "mode": "novelty_review",
        "claims": [
            {
                "claim_id": "C1",
                "claim_text": "...",
                "supporting_refs": [
                    {"value": "10.1/a", "verification_status": "verified"},
                    {"value": "10.2/b", "verification_status": "external_unverified",
                     "verifier_error_metadata": {"errors": []}},
                    {"value": "10.3/c", "verification_status": "not_found"},
                ],
            }
        ],
    }
    rate = _compute_validity(payload)
    # 旧逻辑: ok=2 (verified + external_unverified) / total=3 = 0.667
    # 新逻辑: ok=1 (verified) / total=2 (verifier_error 不入分母) = 0.5
    assert rate == 0.5


def test_render_markdown_mode_0_includes_summon_footer():
    """Mode 0 Markdown must include always-available 召唤 footer."""
    from verifier import render_markdown_mode_0
    payload = {
        "mode": "data_first",
        "anomalies": [{"anomaly_id": "A1", "observation": "...", "data_evidence": []}],
        "hypotheses": [],
        "experiments": [],
        "audit_log_id": "test-summon",
    }
    md = render_markdown_mode_0(payload)
    assert "叫 codex 审" in md
    assert "叫 opus 审" in md
    assert "叫 ds 审" in md
    assert "test-summon" in md


def test_render_markdown_mode_0_no_codename_in_user_facing():
    """No internal codename (mode_0 / L1 / L3 / hypothesis_id) in user-facing output."""
    from verifier import render_markdown_mode_0
    payload = {
        "mode": "data_first",
        "anomalies": [{"anomaly_id": "A1", "observation": "obs", "data_evidence": []}],
        "hypotheses": [{"hypothesis_id": "H1a", "anomaly_id": "A1", "mechanism_text": "mech"}],
        "experiments": [],
        "audit_log_id": "test-nocode",
    }
    md = render_markdown_mode_0(payload)
    # Internal codenames should NOT appear as section headers or in prose
    # (They CAN appear as inline IDs like **A1** **H1a** for cross-ref)
    assert "mode_0" not in md
    assert "anomaly_brief" not in md
    assert "L1 retrieve" not in md
    assert "L3 search" not in md


def test_verify_payload_propagates_verifier_error_metadata(monkeypatch):
    """Publication mode verify_payload now sets verifier_error_metadata on refs
    when DOI verification hits verifier_error."""
    from doi_verify_multisource import DoiCheckResult
    from verifier import verify_payload

    def fake_verify(doi):
        return DoiCheckResult("verifier_error", "all_sources_failed", None,
                              {"errors": [{"src": "openalex", "error": "ConnectError"}]})
    monkeypatch.setattr("verifier.verify_doi_multisource", fake_verify)

    payload = {
        "mode": "novelty_review",
        "claims": [{
            "claim_id": "C1",
            "claim_text": "...",
            "supporting_refs": [
                {"ref_type": "doi", "value": "10.1038/example"},
            ],
        }],
    }
    result = verify_payload(payload, run_sanity=False)
    ref = result["claims"][0]["supporting_refs"][0]
    assert ref["verification_status"] == "external_unverified"  # legacy schema compat
    assert "verifier_error_metadata" in ref
    assert "errors" in ref["verifier_error_metadata"]
    assert ref.get("verified_via") == "all_sources_failed"


def test_verify_payload_propagates_verified_status(monkeypatch):
    """Verified DOI: verification_status='verified', verified_via=source, no error metadata."""
    from doi_verify_multisource import DoiCheckResult
    from verifier import verify_payload

    def fake_verify(doi):
        return DoiCheckResult("verified", "openalex", {"id": "W1"}, None)
    monkeypatch.setattr("verifier.verify_doi_multisource", fake_verify)

    payload = {
        "mode": "novelty_review",
        "claims": [{
            "claim_id": "C1", "claim_text": "...",
            "supporting_refs": [{"ref_type": "doi", "value": "10.1038/v"}],
        }],
    }
    result = verify_payload(payload, run_sanity=False)
    ref = result["claims"][0]["supporting_refs"][0]
    assert ref["verification_status"] == "verified"
    assert ref["verified_via"] == "openalex"
    assert "verifier_error_metadata" not in ref


def test_render_markdown_flags_verifier_error_refs():
    """Markdown render shows ⚠️ for refs with verifier_error_metadata."""
    from verifier import render_markdown
    payload = {
        "mode": "novelty_review",
        "verdict": {"one_line": "test", "confidence": "medium"},
        "claims": [{
            "claim_id": "C1", "claim_text": "test claim",
            "supporting_refs": [
                {"ref_type": "doi", "value": "10.1/err",
                 "verification_status": "external_unverified",
                 "verifier_error_metadata": {"errors": [{"src": "openalex"},
                                                         {"src": "crossref"}]}},
                {"ref_type": "doi", "value": "10.1/ok",
                 "verification_status": "external_unverified"},
            ],
        }],
        "prior_art_coverage": {},
        "audit_log_id": "test-f2-render",
    }
    md = render_markdown(payload)
    # verifier_error ref should have warning marker
    assert "⚠️" in md or "校验器报错" in md
    assert "10.1/err" in md
    # genuine external_unverified ref stays normal
    assert "10.1/ok" in md


def test_verify_mode_0_accepts_string_supporting_refs(monkeypatch):
    """Regression (blind audit): LLMs emit bare-string refs; must not crash."""
    import json
    from doi_verify_multisource import DoiCheckResult
    import verifier
    monkeypatch.setattr(
        "verifier.verify_doi_multisource",
        lambda doi: DoiCheckResult("verified", "openalex", {"id": "W1"}, None),
    )
    payload = {
        "mode": "data_first",
        "anomalies": [{"anomaly_id": "A1", "observation": "o", "data_evidence": []}],
        "hypotheses": [{
            "hypothesis_id": "H1", "anomaly_id": "A1", "mechanism_text": "m",
            "supporting_refs": ["10.1038/nature12373"],  # bare string, not dict
        }],
        "experiments": [], "audit_log_id": "t",
    }
    result = verifier.run_pipeline(json.dumps(payload))
    assert "error" not in result
    ref = result["payload"]["hypotheses"][0]["supporting_refs"][0]
    assert ref["ref_type"] == "doi"
    assert ref["verification_status"] == "verified"


def test_verify_mode_0_source_with_line_suffix(tmp_path):
    """Regression (blind audit #1): data_evidence source 'file.ext:7' must resolve
    by stripping the trailing :line, not be marked not_found."""
    import json
    import verifier
    f = tmp_path / "notes.txt"
    f.write_text("data", encoding="utf-8")
    payload = {
        "mode": "data_first",
        "anomalies": [{"anomaly_id": "A1", "observation": "o", "data_evidence": [
            {"source": f"{f}:7", "quote_text": "q", "line_or_para": "7"}]}],
        "hypotheses": [], "experiments": [], "audit_log_id": "t",
    }
    result = verifier.run_pipeline(json.dumps(payload))
    ev = result["payload"]["anomalies"][0]["data_evidence"][0]
    assert ev["verification_status"] == "verified"


def test_no_false_content_warning_when_similarity_not_checked(monkeypatch):
    """Regression (blind audit #4): the stub sanity-check (no embedding model) must
    NOT raise the '内容与摘要重叠度低' alarm — that means 'checked & low', not 'not checked'."""
    from doi_verify_multisource import DoiCheckResult
    import verifier
    monkeypatch.setattr(
        "verifier.verify_doi_multisource",
        lambda doi: DoiCheckResult("verified", "openalex", {"id": "W1"}, None),
    )
    monkeypatch.setattr("verifier.fetch_openalex_abstract", lambda doi: "some abstract text")
    payload = {
        "mode": "novelty_review",
        "verdict": {"one_line": "x", "confidence": "low"},
        "claims": [{"claim_id": "C1", "claim_text": "t",
                    "supporting_refs": [{"ref_type": "doi", "value": "10.1/a"}]}],
        "prior_art_coverage": {}, "audit_log_id": "t",
    }
    result = verifier.verify_payload(payload, run_sanity=True)
    claim = result["claims"][0]
    assert not claim.get("claim_content_warning"), "must not warn when similarity not computed"
    assert claim["supporting_refs"][0]["content_sanity"]["checked"] is False
