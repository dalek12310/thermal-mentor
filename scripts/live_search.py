"""L3 — Live external retrieval: OpenAlex + Semantic Scholar + arXiv.

v0.1.3 (Task 11): adds env-gated Lens.org + WoS source wrappers via
`build_l3_sources()`. The async `live_search()` fan-out protocol is unchanged
(still OpenAlex + S2 + arXiv); the new sources are registered for future
integration but not wired into the active orchestrator.
"""
from __future__ import annotations

import asyncio
import os
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, NamedTuple

import httpx
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]  # scripts/ -> repo root
_CORPUS_PATH = os.environ.get("THERMAL_MENTOR_CORPUS", "")
RETRACTION_YAML = Path(_CORPUS_PATH) / "retraction_blacklist.yaml" if _CORPUS_PATH else None
CACHE_DIR = _REPO_ROOT / "cache" / "openalex_abstracts"

_MAILTO = os.environ.get("OPENALEX_MAILTO", "")
USER_AGENT = (
    f"thermal-mentor/0.1.3 (mailto:{_MAILTO})" if _MAILTO
    else "thermal-mentor/0.1.3"
)
DEFAULT_SINCE = "2018-01-01"

OPENALEX = "https://api.openalex.org"
SEMANTIC_SCHOLAR = "https://api.semanticscholar.org/graph/v1"
ARXIV = "http://export.arxiv.org/api/query"


def recency_weight(year: int | str, anchor: int = 2023, slope: float = 0.5) -> float:
    """1 + slope * max(0, year - anchor). Floor 1.0 for pre-anchor years."""
    try:
        y = int(year)
    except (TypeError, ValueError):
        return 1.0
    return 1.0 + slope * max(0, y - anchor)


def _load_retraction_dois() -> set[str]:
    if RETRACTION_YAML is None or not RETRACTION_YAML.exists():
        return set()
    data = yaml.safe_load(RETRACTION_YAML.read_text(encoding="utf-8")) or {}
    return {r["doi"].lower() for r in data.get("retractions", []) if r.get("doi")}


def drop_retracted(hits: list[dict], blacklist: set[str]) -> list[dict]:
    bl = {d.lower() for d in blacklist}
    return [h for h in hits if (h.get("doi") or "").lower() not in bl and not h.get("retracted_flag")]


def dedupe_by_doi(hits: list[dict]) -> list[dict]:
    """Dedup by DOI (fallback: arxiv_id / openalex_id). Prefer richer abstract."""
    seen: dict[str, dict] = {}
    order: list[str] = []
    for h in hits:
        key = (h.get("doi") or "").lower() or h.get("arxiv_id", "") or h.get("openalex_id", "")
        if not key:
            continue
        if key in seen:
            if (not seen[key].get("abstract")) and h.get("abstract"):
                seen[key] = h
            continue
        seen[key] = h
        order.append(key)
    return [seen[k] for k in order]


def expand_query_via_corpus(query: str, top_n_keywords: int = 5) -> list[str]:
    """Expand the query with noun-phrases mined from top-10 local-corpus hits.

    Fail-soft: if hybrid_retrieve isn't available (not shipped in public
    release — requires corpus + bge-m3 model), just return [query].
    """
    try:
        from hybrid_retrieve import query as hybrid_query  # type: ignore
        hits = hybrid_query(query, top_k=10)
    except Exception:
        return [query]
    text = " ".join((h.get("document") or "")[:500] for h in hits)
    phrases = re.findall(r"\b[A-Z][a-zA-Z]+(?:[- ][A-Z]?[a-z]+){0,3}\b", text)
    counted: dict[str, int] = {}
    for ph in phrases:
        ph2 = ph.strip()
        if len(ph2) < 4 or ph2.lower() in {"the", "this", "that", "with", "from"}:
            continue
        counted[ph2] = counted.get(ph2, 0) + 1
    top = sorted(counted.items(), key=lambda x: -x[1])[:top_n_keywords]
    variants = [query]
    for ph, _ in top:
        if ph.lower() not in query.lower():
            variants.append(f"{query} {ph}")
    return variants[:5]


def _reconstruct_abstract(inv: dict) -> str:
    if not inv:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)


async def openalex_search(query: str, since: str = DEFAULT_SINCE, top_k: int = 10) -> list[dict]:
    url = f"{OPENALEX}/works"
    params = {
        "search": query,
        "per_page": str(top_k),
        "filter": f"from_publication_date:{since}",
    }
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": USER_AGENT}) as cli:
        r = await cli.get(url, params=params)
        if r.status_code != 200:
            return []
        data = r.json()
    out = []
    for w in data.get("results", []):
        abstract_inv = w.get("abstract_inverted_index") or {}
        abstract = _reconstruct_abstract(abstract_inv)
        out.append({
            "title": w.get("title", ""),
            "abstract": abstract,
            "venue": (w.get("primary_location") or {}).get("source", {}).get("display_name", ""),
            "year": w.get("publication_year") or 0,
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "openalex_id": w.get("id", ""),
            "citations": w.get("cited_by_count", 0),
            "source": "OpenAlex",
            "is_preprint": (w.get("type") == "preprint"),
            "retracted_flag": w.get("is_retracted", False),
            "authors": [a["author"]["display_name"] for a in w.get("authorships", [])[:5]],
        })
    return out


async def semantic_scholar_search(query: str, since: str = DEFAULT_SINCE, top_k: int = 10) -> list[dict]:
    year_min = since.split("-")[0]
    url = f"{SEMANTIC_SCHOLAR}/paper/search"
    params = {
        "query": query,
        "limit": str(top_k),
        "year": f"{year_min}-",
        "fields": "title,abstract,venue,year,externalIds,citationCount,authors",
    }
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": USER_AGENT}) as cli:
        r = await cli.get(url, params=params)
        if r.status_code != 200:
            return []
        data = r.json()
    out = []
    for w in data.get("data", []):
        doi = (w.get("externalIds") or {}).get("DOI", "")
        out.append({
            "title": w.get("title", ""),
            "abstract": w.get("abstract") or "",
            "venue": w.get("venue", ""),
            "year": w.get("year") or 0,
            "doi": doi,
            "openalex_id": "",
            "citations": w.get("citationCount", 0),
            "source": "Semantic Scholar",
            "is_preprint": False,
            "retracted_flag": False,
            "authors": [a.get("name", "") for a in (w.get("authors") or [])[:5]],
        })
    return out


async def arxiv_search(query: str, since: str = DEFAULT_SINCE, top_k: int = 10) -> list[dict]:
    params = {
        "search_query": f"all:{query}",
        "max_results": str(top_k * 3),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV}?{urllib.parse.urlencode(params)}"
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": USER_AGENT}) as cli:
        r = await cli.get(url)
        if r.status_code != 200:
            return []
        text = r.text

    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    out = []
    cutoff = datetime.strptime(since, "%Y-%m-%d")
    for entry in root.findall("atom:entry", ns):
        published = entry.findtext("atom:published", "", ns)
        try:
            pub_dt = datetime.strptime(published[:10], "%Y-%m-%d")
        except ValueError:
            continue
        if pub_dt < cutoff:
            continue
        arxiv_id = (entry.findtext("atom:id", "", ns) or "").split("/abs/")[-1]
        doi = entry.findtext("arxiv:doi", "", ns) or ""
        out.append({
            "title": (entry.findtext("atom:title", "", ns) or "").strip(),
            "abstract": (entry.findtext("atom:summary", "", ns) or "").strip(),
            "venue": "arXiv",
            "year": pub_dt.year,
            "doi": doi,
            "openalex_id": "",
            "arxiv_id": arxiv_id,
            "citations": 0,
            "source": "arXiv",
            "is_preprint": True,
            "retracted_flag": False,
            "authors": [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)[:5]],
        })
        if len(out) >= top_k:
            break
    return out


async def live_search(
    query_text: str,
    since: str = DEFAULT_SINCE,
    top_k_per_source: int = 10,
) -> dict[str, Any]:
    queries = expand_query_via_corpus(query_text)
    blacklist = _load_retraction_dois()
    sources_hit: list[str] = []

    # Map registry key -> display name (preserves v0.1 output schema)
    DISPLAY_NAMES = {
        "openalex": "OpenAlex",
        "semantic_scholar": "Semantic Scholar",
        "arxiv": "arXiv",
        "lens": "Lens.org",
        "wos": "Web of Science",
    }

    sources = build_l3_sources()

    async def run_source(src: "L3Source"):
        display = DISPLAY_NAMES.get(src.name, src.name)
        try:
            sub_hits: list[dict] = []
            for q in queries:
                if asyncio.iscoroutinefunction(src.query_fn):
                    sub = await src.query_fn(q, since=since, top_k=top_k_per_source)
                else:
                    # Sync sources (lens_search, wos_search) bridged via to_thread
                    sub = await asyncio.to_thread(
                        src.query_fn, q, top_k=top_k_per_source, since=since
                    )
                sub_hits.extend(sub)
            if sub_hits:
                sources_hit.append(display)
            return sub_hits
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            print(f"[live_search] {display} HTTP error: {type(e).__name__}: {e}")
            return []
        except Exception as e:
            # Catch-all for unexpected errors (parsing, key errors) — log + continue
            print(f"[live_search] {display} unexpected error: {type(e).__name__}: {e}")
            return []

    tasks = [asyncio.create_task(run_source(src)) for src in sources]
    results = await asyncio.gather(*tasks)
    all_hits = [hit for source_hits in results for hit in source_hits]

    all_hits = drop_retracted(all_hits, blacklist)
    deduped = dedupe_by_doi(all_hits)
    import math
    for h in deduped:
        h["recency_boost"] = recency_weight(h.get("year", 0))
        cit = h.get("citations") or 0
        h["fused_score"] = h["recency_boost"] * math.log(1 + cit + 0.5)
    deduped.sort(key=lambda x: -x["fused_score"])
    hits_from_last_12mo = sum(1 for h in deduped if int(h.get("year") or 0) >= datetime.now().year - 1)
    return {
        "hits": deduped[:30],
        "coverage": {
            "queries_used": queries,
            "sources_hit": sources_hit,
            "date_range": f"{since[:4]}-{datetime.now().year}",
            "recency_boost_applied": True,
            "total_hits": len(deduped),
            "hits_from_last_12mo": hits_from_last_12mo,
            "closest_baseline": (
                {"doi": deduped[0].get("doi"), "year": deduped[0].get("year"), "title": deduped[0].get("title", "")[:120]}
                if deduped else None
            ),
        },
    }


def lens_search(query: str, top_k: int = 10, since: str | None = None) -> list[dict]:
    """Lens.org Scholarly API search (sync, env-gated by LENS_API_TOKEN).

    Endpoint: POST https://api.lens.org/scholarly/search
    Auth: Bearer LENS_API_TOKEN
    """
    token = os.environ.get("LENS_API_TOKEN")
    if not token:
        return []  # defensive: should never be called without token via build_l3_sources gate
    body: dict = {"query": {"match": {"abstract": query}}, "size": top_k}
    if since:
        body["query"] = {
            "bool": {
                "must": [{"match": {"abstract": query}}],
                "filter": [{"range": {"date_published": {"gte": since}}}],
            }
        }
    try:
        with httpx.Client(timeout=15) as cli:
            r = cli.post(
                "https://api.lens.org/scholarly/search",
                json=body,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            if r.status_code != 200:
                return []
            data = r.json()
            return [_lens_to_unified_hit(item) for item in data.get("data", [])]
    except (httpx.HTTPError, httpx.TimeoutException):
        return []


def _lens_to_unified_hit(item: dict) -> dict:
    """Map Lens.org hit to unified L3 hit schema."""
    return {
        "title": item.get("title", ""),
        "abstract": item.get("abstract", ""),
        "venue": (item.get("source") or {}).get("title", ""),
        "year": item.get("year_published"),
        "doi": next(
            (eid["value"] for eid in item.get("external_ids", []) if eid.get("type") == "doi"),
            None,
        ),
        "source": "lens",
        "is_preprint": False,
        "retracted_flag": False,
        "citations": item.get("scholarly_citations_count", 0),
    }


def wos_search(query: str, top_k: int = 10, since: str | None = None) -> list[dict]:
    """Web of Science Starter API search (sync, env-gated by WOS_API_KEY).

    Endpoint: GET https://api.clarivate.com/apis/wos-starter/v1/documents
    Auth: X-ApiKey WOS_API_KEY
    """
    key = os.environ.get("WOS_API_KEY")
    if not key:
        return []  # defensive: should never be called without key via build_l3_sources gate
    q = f"TS=({query})"
    if since:
        py_year = since.split("-")[0]
        q += f" AND PY={py_year}-2026"
    try:
        with httpx.Client(timeout=15) as cli:
            r = cli.get(
                "https://api.clarivate.com/apis/wos-starter/v1/documents",
                params={"q": q, "limit": top_k},
                headers={"X-ApiKey": key},
            )
            if r.status_code != 200:
                return []
            data = r.json()
            return [_wos_to_unified_hit(item) for item in data.get("hits", [])]
    except (httpx.HTTPError, httpx.TimeoutException):
        return []


def _wos_to_unified_hit(item: dict) -> dict:
    """Map WoS hit to unified L3 hit schema."""
    return {
        "title": item.get("title", ""),
        "abstract": item.get("abstract", ""),
        "venue": item.get("source_title", ""),
        "year": item.get("publication_year"),
        "doi": (item.get("identifiers") or {}).get("doi"),
        "source": "wos",
        "is_preprint": False,
        "retracted_flag": False,
        "citations": item.get("citation_count", 0),
        "jcr_quartile": item.get("jcr_quartile"),
        "impact_factor": item.get("impact_factor"),
    }


class L3Source(NamedTuple):
    """A registered L3 fan-out source.

    `name` is the lowercase registry key (e.g. "openalex"). `query_fn` may be
    sync or async — the orchestrator is responsible for awaiting if needed.
    `enabled_by_env` records the env var that gated registration (None = always).
    """

    name: str
    query_fn: Callable
    enabled_by_env: str | None = None


def build_l3_sources() -> list[L3Source]:
    """Build L3 fan-out source list, optionally including Lens.org + WoS.

    Default chain (no env vars set): OpenAlex + Semantic Scholar + arXiv —
    the v0.1 baseline. Lens.org joins when LENS_API_TOKEN is set; WoS joins
    when WOS_API_KEY is set. The async `live_search()` orchestrator currently
    consumes only the baseline three; new sources are registered for future
    integration (Task 11 keeps fan-out 协议不变).
    """
    sources: list[L3Source] = [
        L3Source("openalex", openalex_search, enabled_by_env=None),
        L3Source("semantic_scholar", semantic_scholar_search, enabled_by_env=None),
        L3Source("arxiv", arxiv_search, enabled_by_env=None),
    ]
    if os.environ.get("LENS_API_TOKEN"):
        sources.append(L3Source("lens", lens_search, enabled_by_env="LENS_API_TOKEN"))
    if os.environ.get("WOS_API_KEY"):
        sources.append(L3Source("wos", wos_search, enabled_by_env="WOS_API_KEY"))
    return sources


def main() -> None:
    import argparse, json
    p = argparse.ArgumentParser()
    p.add_argument("query")
    p.add_argument("--since", default=DEFAULT_SINCE)
    p.add_argument("--top-k", type=int, default=10)
    args = p.parse_args()
    out = asyncio.run(live_search(args.query, since=args.since, top_k_per_source=args.top_k))
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
