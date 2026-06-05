"""Shared pytest fixtures for science-mentor tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_dataset_dir() -> Path:
    return FIXTURES_DIR / "sample_dataset"


@pytest.fixture(scope="session")
def openalex_responses() -> dict:
    return json.loads((FIXTURES_DIR / "openalex_responses.json").read_text(encoding="utf-8"))


@pytest.fixture
def mock_openalex_client(monkeypatch, openalex_responses):
    """Replace httpx.Client.get with mock that returns openalex_responses by DOI."""
    import httpx

    class MockResponse:
        def __init__(self, status_code: int, data: dict | None):
            self.status_code = status_code
            self._data = data
        def json(self):
            return self._data

    def mock_get(self, url, **kwargs):
        for doi, resp in openalex_responses.items():
            if doi in url:
                return MockResponse(200, resp) if resp else MockResponse(404, None)
        return MockResponse(404, None)

    monkeypatch.setattr(httpx.Client, "get", mock_get)
    return mock_get
