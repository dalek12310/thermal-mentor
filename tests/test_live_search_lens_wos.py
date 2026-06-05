"""Tests for Lens.org and WoS source addition to L3 fan-out."""
from __future__ import annotations

import sys
from pathlib import Path

# Make scripts/ importable (flattened release layout)
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_lens_source_in_chain_when_token_present(monkeypatch):
    monkeypatch.setenv("LENS_API_TOKEN", "fake-token")
    from live_search import build_l3_sources
    sources = build_l3_sources()
    names = [s.name for s in sources]
    assert "lens" in names


def test_lens_source_excluded_when_no_token(monkeypatch):
    monkeypatch.delenv("LENS_API_TOKEN", raising=False)
    from live_search import build_l3_sources
    sources = build_l3_sources()
    names = [s.name for s in sources]
    assert "lens" not in names


def test_wos_source_in_chain_when_key_present(monkeypatch):
    monkeypatch.setenv("WOS_API_KEY", "fake-key")
    from live_search import build_l3_sources
    sources = build_l3_sources()
    names = [s.name for s in sources]
    assert "wos" in names


def test_wos_source_excluded_when_no_key(monkeypatch):
    monkeypatch.delenv("WOS_API_KEY", raising=False)
    from live_search import build_l3_sources
    sources = build_l3_sources()
    names = [s.name for s in sources]
    assert "wos" not in names


def test_default_sources_unchanged(monkeypatch):
    """Without optional env vars, default chain is OpenAlex + S2 + arXiv (v0.1 baseline)."""
    monkeypatch.delenv("LENS_API_TOKEN", raising=False)
    monkeypatch.delenv("WOS_API_KEY", raising=False)
    from live_search import build_l3_sources
    sources = build_l3_sources()
    names = [s.name for s in sources]
    assert set(names) == {"openalex", "semantic_scholar", "arxiv"}


def test_lens_search_returns_empty_on_http_error(monkeypatch):
    """lens_search swallows httpx.HTTPError and returns []."""
    import httpx
    monkeypatch.setenv("LENS_API_TOKEN", "fake-token")

    def raise_http_error(*args, **kwargs):
        raise httpx.ConnectError("simulated network failure")

    monkeypatch.setattr(httpx.Client, "post", raise_http_error)
    from live_search import lens_search
    result = lens_search("test query")
    assert result == []


def test_wos_search_returns_empty_on_http_error(monkeypatch):
    """wos_search swallows httpx.HTTPError and returns []."""
    import httpx
    monkeypatch.setenv("WOS_API_KEY", "fake-key")

    def raise_http_error(*args, **kwargs):
        raise httpx.ConnectError("simulated network failure")

    monkeypatch.setattr(httpx.Client, "get", raise_http_error)
    from live_search import wos_search
    result = wos_search("test query")
    assert result == []


def test_live_search_dispatches_to_build_l3_sources(monkeypatch):
    """live_search async orchestrator uses build_l3_sources() — Lens fires when token set."""
    import asyncio
    monkeypatch.setenv("LENS_API_TOKEN", "fake-token")
    monkeypatch.delenv("WOS_API_KEY", raising=False)

    called_names: list[str] = []

    async def fake_oa(q, since=None, top_k=10):
        called_names.append("openalex")
        return []

    async def fake_ss(q, since=None, top_k=10):
        called_names.append("semantic_scholar")
        return []

    async def fake_ax(q, since=None, top_k=10):
        called_names.append("arxiv")
        return []

    def fake_lens(q, top_k=10, since=None):
        called_names.append("lens")
        return []

    monkeypatch.setattr("live_search.openalex_search", fake_oa)
    monkeypatch.setattr("live_search.semantic_scholar_search", fake_ss)
    monkeypatch.setattr("live_search.arxiv_search", fake_ax)
    monkeypatch.setattr("live_search.lens_search", fake_lens)
    monkeypatch.setattr("live_search.expand_query_via_corpus", lambda q, **kw: [q])

    from live_search import live_search
    asyncio.run(live_search("test query"))

    assert "openalex" in called_names
    assert "semantic_scholar" in called_names
    assert "arxiv" in called_names
    assert "lens" in called_names, "lens should fire when LENS_API_TOKEN is set"
