"""Tests for DOI multi-source verification."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make scripts/ importable (flattened release layout)
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_normalize_doi_strips_url_prefix():
    from doi_verify_multisource import normalize_doi
    assert normalize_doi("https://doi.org/10.1038/s41586-2025-EXAMPLE") == "10.1038/s41586-2025-example"
    assert normalize_doi("http://dx.doi.org/10.1038/s41586-2025-EXAMPLE") == "10.1038/s41586-2025-example"
    assert normalize_doi("doi:10.1038/s41586-2025-EXAMPLE") == "10.1038/s41586-2025-example"


def test_normalize_doi_lowercases():
    from doi_verify_multisource import normalize_doi
    assert normalize_doi("10.1038/S41586-2025-EXAMPLE") == "10.1038/s41586-2025-example"


def test_normalize_doi_strips_whitespace():
    from doi_verify_multisource import normalize_doi
    assert normalize_doi("  10.1038/s41586-2025-EXAMPLE  ") == "10.1038/s41586-2025-example"


def test_doi_check_result_has_required_fields():
    from doi_verify_multisource import DoiCheckResult
    r = DoiCheckResult(status="verified", source="openalex", metadata={"id": "..."}, error_detail=None)
    assert r.status == "verified"
    assert r.source == "openalex"
    assert r.metadata == {"id": "..."}
    assert r.error_detail is None


def test_doi_check_result_status_must_be_valid():
    from doi_verify_multisource import DoiCheckResult
    with pytest.raises((TypeError, ValueError)):
        DoiCheckResult(status="invalid_status", source=None, metadata=None, error_detail=None)


def test_openalex_lookup_found(mock_openalex_client):
    from doi_verify_multisource import openalex_lookup
    result = openalex_lookup("10.1038/s41586-2025-example-valid")
    assert result.found is True
    assert result.metadata is not None
    assert "title" in result.metadata


def test_openalex_lookup_not_found(mock_openalex_client):
    from doi_verify_multisource import openalex_lookup
    result = openalex_lookup("10.xxxx/notfound_sentinel_1")
    assert result.found is False
    assert result.metadata is None


def test_crossref_lookup_signature_compatible():
    """Crossref lookup must return same SourceLookupResult shape as OpenAlex."""
    from doi_verify_multisource import crossref_lookup
    # Just signature check: callable with (doi: str) -> SourceLookupResult
    import inspect
    sig = inspect.signature(crossref_lookup)
    assert "doi" in sig.parameters


def test_doi_org_head_for_existence_only():
    """DOI.org HEAD returns found=True with empty metadata (existence only)."""
    from doi_verify_multisource import doi_org_head
    # HEAD 返回 200/302 → found=True; 404 → found=False
    # 不 mock, 测试 callable shape
    import inspect
    sig = inspect.signature(doi_org_head)
    assert "doi" in sig.parameters


def test_verify_chain_first_source_verified(monkeypatch, tmp_path):
    from doi_verify_multisource import (
        verify_doi_multisource, SourceLookupResult,
    )
    import doi_verify_multisource as mod
    monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        "doi_verify_multisource.openalex_lookup",
        lambda doi, **kw: SourceLookupResult(True, {"id": "W123"})
    )
    r = verify_doi_multisource("10.1038/example")
    assert r.status == "verified"
    assert r.source == "openalex"


def test_verify_chain_non_authoritative_not_found_continues_to_authoritative(monkeypatch, tmp_path):
    """OpenAlex returns not_found (non-authoritative) — should continue to Crossref."""
    from doi_verify_multisource import (
        verify_doi_multisource, SourceLookupResult,
    )
    import doi_verify_multisource as mod
    monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        "doi_verify_multisource.openalex_lookup",
        lambda doi, **kw: SourceLookupResult(False, None)
    )
    monkeypatch.setattr(
        "doi_verify_multisource.crossref_lookup",
        lambda doi, **kw: SourceLookupResult(True, {"DOI": "10.1038/example"})
    )
    r = verify_doi_multisource("10.1038/example")
    assert r.status == "verified"
    assert r.source == "crossref"


def test_verify_chain_doi_head_is_the_absence_authority(monkeypatch, tmp_path):
    """Only doi.org HEAD (resolves every registration agency) terminates on a
    negative. A Crossref miss must NOT stop the chain, because Crossref does not
    index DataCite/Zenodo/mEDRA DOIs — its miss says nothing about existence."""
    from doi_verify_multisource import verify_doi_multisource, SourceLookupResult
    import doi_verify_multisource as mod
    monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path)
    head_called = []
    for name in ("openalex_lookup", "crossref_lookup", "s2_lookup", "lens_lookup"):
        monkeypatch.setattr(
            f"doi_verify_multisource.{name}",
            lambda doi, **kw: SourceLookupResult(False, None),
        )
    def head_spy(doi, **kw):
        head_called.append(doi)
        return SourceLookupResult(False, None)
    monkeypatch.setattr("doi_verify_multisource.doi_org_head", head_spy)
    r = verify_doi_multisource("10.1038/example")
    assert r.status == "not_found"
    assert r.source == "doi_head"
    assert head_called, "Crossref miss must fall through to doi.org HEAD before declaring not_found"


def test_verify_chain_crossref_miss_falls_through_to_doi_head(monkeypatch, tmp_path):
    """Regression (DeepSeek audit #2): a DataCite/Zenodo DOI absent from Crossref
    but resolvable by doi.org HEAD must verify, not be falsely reported not_found."""
    from doi_verify_multisource import verify_doi_multisource, SourceLookupResult
    import doi_verify_multisource as mod
    monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path)
    for name in ("openalex_lookup", "crossref_lookup", "s2_lookup", "lens_lookup"):
        monkeypatch.setattr(
            f"doi_verify_multisource.{name}",
            lambda doi, **kw: SourceLookupResult(False, None),
        )
    monkeypatch.setattr(
        "doi_verify_multisource.doi_org_head",
        lambda doi, **kw: SourceLookupResult(True, {}),
    )
    r = verify_doi_multisource("10.5281/zenodo.123456")
    assert r.status == "verified"
    assert r.source == "doi_head"


def test_verify_chain_all_sources_http_error(monkeypatch, tmp_path):
    """All sources raise HTTPError → verifier_error, all_sources_failed."""
    import httpx
    from doi_verify_multisource import verify_doi_multisource
    import doi_verify_multisource as mod
    monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path)

    def raises(doi, **kw):
        raise httpx.ConnectError("network down")
    monkeypatch.setattr("doi_verify_multisource.openalex_lookup", raises)
    monkeypatch.setattr("doi_verify_multisource.crossref_lookup", raises)
    monkeypatch.setattr("doi_verify_multisource.s2_lookup", raises)
    monkeypatch.setattr("doi_verify_multisource.lens_lookup", raises)
    monkeypatch.setattr("doi_verify_multisource.doi_org_head", raises)
    r = verify_doi_multisource("10.1038/example")
    assert r.status == "verifier_error"
    assert r.source == "all_sources_failed"
    assert r.error_detail is not None
    assert "errors" in r.error_detail


def test_cache_hit_skips_lookup(monkeypatch, tmp_path):
    from doi_verify_multisource import verify_doi_multisource, SourceLookupResult
    import doi_verify_multisource as mod
    monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path)
    call_count = [0]
    def counting_lookup(doi, **kw):
        call_count[0] += 1
        return SourceLookupResult(True, {"id": "W1"})
    monkeypatch.setattr("doi_verify_multisource.openalex_lookup", counting_lookup)
    # First call: hits OpenAlex
    r1 = verify_doi_multisource("10.1038/cached")
    assert r1.status == "verified"
    assert call_count[0] == 1
    # Second call: hits cache, no lookup
    r2 = verify_doi_multisource("10.1038/cached")
    assert r2.status == "verified"
    assert call_count[0] == 1, "Second call should hit cache, not OpenAlex"


def test_cache_does_not_store_verifier_error(monkeypatch, tmp_path):
    """verifier_error 状态不入 cache, 下次还应该 retry."""
    import httpx
    from doi_verify_multisource import verify_doi_multisource
    import doi_verify_multisource as mod
    monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path)

    call_count = [0]
    def maybe_fail(doi, **kw):
        call_count[0] += 1
        if call_count[0] <= 5:
            raise httpx.ConnectError("flaky")
        from doi_verify_multisource import SourceLookupResult
        return SourceLookupResult(True, {"id": "W2"})
    monkeypatch.setattr("doi_verify_multisource.openalex_lookup", maybe_fail)
    monkeypatch.setattr("doi_verify_multisource.crossref_lookup", maybe_fail)
    monkeypatch.setattr("doi_verify_multisource.s2_lookup", maybe_fail)
    monkeypatch.setattr("doi_verify_multisource.lens_lookup", maybe_fail)
    monkeypatch.setattr("doi_verify_multisource.doi_org_head", maybe_fail)

    r1 = verify_doi_multisource("10.1038/flaky")
    assert r1.status == "verifier_error"
    # Cache should NOT store verifier_error → retry should hit again
    verify_doi_multisource("10.1038/flaky")
    # call_count > 5 means subsequent retry happened
    assert call_count[0] > 5, "verifier_error should not be cached, retry expected"


def _fake_head_client(status_code):
    """Build a fake httpx.Client whose .head() returns the given status."""
    import httpx

    class _FakeResp:
        def __init__(self, code, url):
            self.status_code = code
            self.request = httpx.Request("HEAD", url)

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def head(self, url):
            return _FakeResp(status_code, url)

    return _FakeClient


def test_doi_org_head_404_is_absence(monkeypatch):
    """404 from doi.org → genuine absence (found=False)."""
    from doi_verify_multisource import doi_org_head
    monkeypatch.setattr("doi_verify_multisource.httpx.Client", _fake_head_client(404))
    assert doi_org_head("10.1/gone").found is False


def test_doi_org_head_transient_status_raises(monkeypatch):
    """Regression (Codex audit #4): 503/429 must RAISE (→ verifier_error), not be
    silently treated as absence and cached for 24h."""
    import httpx
    import pytest
    from doi_verify_multisource import doi_org_head
    monkeypatch.setattr("doi_verify_multisource.httpx.Client", _fake_head_client(503))
    with pytest.raises(httpx.HTTPError):
        doi_org_head("10.1/transient")


def test_transient_doi_head_yields_verifier_error_not_not_found(monkeypatch, tmp_path):
    """End-to-end: a transient doi.org failure must surface as verifier_error,
    never a (cached) false not_found — doi_head is now the sole absence authority."""
    import httpx
    from doi_verify_multisource import verify_doi_multisource, SourceLookupResult
    import doi_verify_multisource as mod
    monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path)
    for name in ("openalex_lookup", "crossref_lookup", "s2_lookup", "lens_lookup"):
        monkeypatch.setattr(
            f"doi_verify_multisource.{name}",
            lambda doi, **kw: SourceLookupResult(False, None),
        )
    def head_down(doi, **kw):
        raise httpx.ConnectError("doi.org unreachable")
    monkeypatch.setattr("doi_verify_multisource.doi_org_head", head_down)
    r = verify_doi_multisource("10.1/transient")
    assert r.status == "verifier_error"
