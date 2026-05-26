"""DOI multi-source verification chain.

Spec ref: 2026-05-25-thermal-mentor-v0.1.3-mode-routing-design.md Section 4.4.2
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, NamedTuple, Optional

import httpx


VALID_STATUSES = {"verified", "not_found", "verifier_error"}


@dataclass
class DoiCheckResult:
    """Result of DOI verification across multi-source chain."""
    status: Literal["verified", "not_found", "verifier_error"]
    source: Optional[str]
    metadata: Optional[dict]
    error_detail: Optional[dict]

    def __post_init__(self):
        if self.status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}, got {self.status!r}")


_DOI_PREFIX_RE = re.compile(r"^(https?://(?:dx\.)?doi\.org/|doi:)", re.IGNORECASE)


def normalize_doi(doi: str) -> str:
    """Normalize DOI: strip URL/doi: prefix, lowercase, strip whitespace."""
    s = doi.strip()
    s = _DOI_PREFIX_RE.sub("", s)
    return s.lower()


_MAILTO = os.environ.get("OPENALEX_MAILTO", "")
USER_AGENT = (
    f"thermal-mentor/0.1.3 (mailto:{_MAILTO})" if _MAILTO
    else "thermal-mentor/0.1.3"
)
DEFAULT_TIMEOUT = 10.0


class SourceLookupResult(NamedTuple):
    found: bool
    metadata: Optional[dict]


def openalex_lookup(doi: str, timeout: float = DEFAULT_TIMEOUT) -> SourceLookupResult:
    """OpenAlex /works/doi:{DOI}. Returns SourceLookupResult."""
    url = f"https://api.openalex.org/works/doi:{doi}"
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as cli:
        r = cli.get(url)
        if r.status_code == 200:
            data = r.json()
            if data and data.get("id"):
                return SourceLookupResult(True, data)
        return SourceLookupResult(False, None)


def crossref_lookup(doi: str, timeout: float = DEFAULT_TIMEOUT) -> SourceLookupResult:
    """Crossref /works/{DOI}. Returns SourceLookupResult."""
    url = f"https://api.crossref.org/works/{doi}"
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as cli:
        r = cli.get(url)
        if r.status_code == 200:
            data = r.json()
            if data and data.get("message"):
                return SourceLookupResult(True, data["message"])
        return SourceLookupResult(False, None)


def s2_lookup(doi: str, timeout: float = DEFAULT_TIMEOUT) -> SourceLookupResult:
    """Semantic Scholar /paper/{DOI}. Returns SourceLookupResult."""
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as cli:
        r = cli.get(url, params={"fields": "title,year,authors,abstract"})
        if r.status_code == 200:
            data = r.json()
            if data and data.get("paperId"):
                return SourceLookupResult(True, data)
        return SourceLookupResult(False, None)


def lens_lookup(doi: str, timeout: float = DEFAULT_TIMEOUT) -> SourceLookupResult:
    """Lens.org Scholarly API. Returns SourceLookupResult. Requires LENS_API_TOKEN."""
    token = os.environ.get("LENS_API_TOKEN")
    if not token:
        return SourceLookupResult(False, None)
    url = "https://api.lens.org/scholarly/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    body = {"query": {"term": {"external_ids.value": doi}}, "size": 1}
    with httpx.Client(timeout=timeout, headers=headers) as cli:
        r = cli.post(url, json=body)
        if r.status_code == 200:
            data = r.json()
            if data and data.get("data"):
                return SourceLookupResult(True, data["data"][0])
        return SourceLookupResult(False, None)


def wos_lookup(doi: str, timeout: float = DEFAULT_TIMEOUT) -> SourceLookupResult:
    """Web of Science Starter API. Returns SourceLookupResult. Requires WOS_API_KEY."""
    key = os.environ.get("WOS_API_KEY")
    if not key:
        return SourceLookupResult(False, None)
    url = "https://api.clarivate.com/apis/wos-starter/v1/documents"
    headers = {"X-ApiKey": key, "User-Agent": USER_AGENT}
    params = {"q": f"DO=({doi})", "limit": 1}
    with httpx.Client(timeout=timeout, headers=headers) as cli:
        r = cli.get(url, params=params)
        if r.status_code == 200:
            data = r.json()
            if data and data.get("hits"):
                return SourceLookupResult(True, data["hits"][0])
        return SourceLookupResult(False, None)


def doi_org_head(doi: str, timeout: float = DEFAULT_TIMEOUT) -> SourceLookupResult:
    """DOI.org HEAD. Authoritative for DOI existence (protocol-level resolver)."""
    url = f"https://doi.org/{doi}"
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False, headers={"User-Agent": USER_AGENT}) as cli:
            r = cli.head(url)
            if r.status_code in (200, 301, 302):
                return SourceLookupResult(True, {})
            return SourceLookupResult(False, None)
    except httpx.HTTPError:
        raise


class Source(NamedTuple):
    name: str
    lookup_fn: Callable[[str], SourceLookupResult]
    is_authoritative_for_existence: bool


def _build_chain() -> list[Source]:
    chain = [
        Source("openalex", openalex_lookup, False),
        Source("crossref", crossref_lookup, True),   # 权威 (DOI 注册机构)
        Source("semantic_scholar", s2_lookup, False),
        Source("lens", lens_lookup, False),
        Source("doi_head", doi_org_head, True),       # 权威 (protocol-level resolver)
    ]
    if os.environ.get("WOS_API_KEY"):
        # WoS 插在 S2 之前作为 metadata 二次源 (非权威)
        chain.insert(2, Source("wos", wos_lookup, False))
    return chain


_REPO_ROOT = Path(__file__).resolve().parents[1]  # scripts/ -> repo root
_CACHE_DIR = _REPO_ROOT / "cache" / "doi_verify"
_CACHE_TTL_SECONDS = 86400  # 24h


def _cache_path(doi: str) -> Path:
    h = hashlib.sha256(doi.encode()).hexdigest()[:24]
    return _CACHE_DIR / f"{h}.json"


def _cache_get(doi: str) -> Optional[DoiCheckResult]:
    path = _cache_path(doi)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - data["timestamp"] > _CACHE_TTL_SECONDS:
            return None
        return DoiCheckResult(
            status=data["status"],
            source=data["source"],
            metadata=data["metadata"],
            error_detail=data["error_detail"],
        )
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def _cache_set(doi: str, result: DoiCheckResult) -> None:
    # Don't cache verifier_error (transient network failures should retry)
    if result.status == "verifier_error":
        return
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": result.status,
        "source": result.source,
        "metadata": result.metadata,
        "error_detail": result.error_detail,
        "timestamp": time.time(),
        "doi": doi,
    }
    _cache_path(doi).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def verify_doi_multisource(doi: str) -> DoiCheckResult:
    """Multi-source DOI verification chain with not_found semantic.

    - non-authoritative source not_found → continue fallback (could be indexing gap)
    - authoritative source (Crossref / DOI.org HEAD) not_found → confirmed absence
    - any source verified → return verified
    - all sources raise HTTPError → verifier_error, all_sources_failed

    24h disk cache; verifier_error is intentionally NOT cached (transient).
    """
    doi_n = normalize_doi(doi)
    cached = _cache_get(doi_n)
    if cached is not None:
        return cached
    accumulated_errors: list[dict] = []
    chain = _build_chain()
    for src in chain:
        try:
            result = src.lookup_fn(doi_n)
            if result.found:
                final = DoiCheckResult("verified", src.name, result.metadata, None)
                _cache_set(doi_n, final)
                return final
            elif src.is_authoritative_for_existence:
                final = DoiCheckResult("not_found", src.name, None, None)
                _cache_set(doi_n, final)
                return final
            # non-authoritative not_found → 继续 fallback
            continue
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            accumulated_errors.append({
                "src": src.name,
                "error": type(e).__name__,
                "detail": str(e)[:200],
            })
            continue
    final = DoiCheckResult(
        "verifier_error", "all_sources_failed", None,
        {"errors": accumulated_errors}
    )
    _cache_set(doi_n, final)  # NO-OP for verifier_error
    return final
