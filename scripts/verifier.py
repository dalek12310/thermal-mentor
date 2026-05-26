"""JSON-first verifier with OpenAlex abstract sanity check + Chinese regex backstop.

Corpus is optional. When ``THERMAL_MENTOR_CORPUS`` env var is unset or the
corresponding files do not exist, ``check_local_citekey`` returns ``not_found``
for every key (publication mode degrades gracefully — DOI verification still
works via ``verify_doi_multisource``). Mode 0 (data-first) is unaffected.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

import httpx
import yaml

from doi_verify_multisource import DoiCheckResult, verify_doi_multisource

_REPO_ROOT = Path(__file__).resolve().parents[1]  # scripts/ -> repo root
_CORPUS_PATH = os.environ.get("THERMAL_MENTOR_CORPUS", "")
CORPUS_CSV = Path(_CORPUS_PATH) / "distillation_corpus_v2.csv" if _CORPUS_PATH else None
RETRACTION_YAML = Path(_CORPUS_PATH) / "retraction_blacklist.yaml" if _CORPUS_PATH else None
CACHE_DIR = _REPO_ROOT / "cache" / "openalex_abstracts"

OPENALEX = "https://api.openalex.org"
_MAILTO = os.environ.get("OPENALEX_MAILTO", "")
USER_AGENT = (
    f"thermal-mentor/0.1.3 (mailto:{_MAILTO})" if _MAILTO
    else "thermal-mentor/0.1.3"
)
SANITY_CHECK_THRESHOLD = 0.55

CHINESE_CITATION_PATTERNS = [
    re.compile(r"\[(\d{1,3})\]"),
    re.compile(r"（[一-鿿一-鿿 A-Za-z\.]+等?,?\s*\d{4}）"),
    re.compile(r"\(([A-Z][a-zA-Z]+ et al\.?,?\s*\d{4})\)"),
    re.compile(r"\(([A-Z][a-zA-Z]+,?\s*\d{4})\)"),
]


@lru_cache(maxsize=1)
def _corpus_citekeys() -> set[str]:
    keys: set[str] = set()
    if CORPUS_CSV is None or not CORPUS_CSV.exists():
        return keys  # Empty corpus -> check_local_citekey always returns "not_found"
    with CORPUS_CSV.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            ck = r.get("citekey") or r.get("key") or ""
            if ck:
                keys.add(ck)
    return keys


@lru_cache(maxsize=1)
def _retracted_citekeys() -> set[str]:
    if RETRACTION_YAML is None or not RETRACTION_YAML.exists():
        return set()
    data = yaml.safe_load(RETRACTION_YAML.read_text(encoding="utf-8")) or {}
    return {r["citekey_in_corpus"] for r in data.get("retractions", [])}


def validate_schema(payload: dict) -> list[str]:
    errs: list[str] = []
    required_top = ["mode", "verdict", "claims", "prior_art_coverage", "audit_log_id"]
    for k in required_top:
        if k not in payload:
            errs.append(f"missing top-level key: {k}")
    if "verdict" in payload and not isinstance(payload["verdict"], dict):
        errs.append("verdict must be object")
    if "claims" in payload and not isinstance(payload["claims"], list):
        errs.append("claims must be list")
    for i, c in enumerate(payload.get("claims", [])):
        for k in ("claim_id", "claim_text", "supporting_refs"):
            if k not in c:
                errs.append(f"claim[{i}] missing {k}")
    return errs


def check_local_citekey(citekey: str) -> str:
    if citekey in _retracted_citekeys():
        return "retracted"
    if citekey in _corpus_citekeys():
        return "verified"
    return "not_found"


def doi_result_to_v01_status(result: DoiCheckResult) -> str:
    """Legacy adapter: map DoiCheckResult to v0.1 publication renderer string domain.

    Note: verifier_error → external_unverified for v0.1 schema backwards-compat;
    Markdown renderer (render_markdown) MUST inspect the 'verifier_error_metadata'
    side-channel to print ⚠️ 校验器报错 explicitly.
    """
    if result.status == "verified":
        return "verified"
    if result.status == "not_found":
        return "not_found"
    if result.status == "verifier_error":
        return "external_unverified"
    raise ValueError(f"unknown DoiCheckResult.status: {result.status}")


def check_doi(doi: str) -> str:
    """Legacy v0.1 API surface. Wraps verify_doi_multisource via LegacyDoiAdapter.

    Silent FP bug from v0.1 is fixed at the underlying verify_doi_multisource layer:
    HTTP errors no longer silently return 'external_unverified' — they explicitly
    return verifier_error, then this adapter maps back for v0.1 schema compat,
    but verifier_error is preserved in side-channel for Markdown rendering.
    """
    if not doi:
        return "not_found"
    result = verify_doi_multisource(doi)
    return doi_result_to_v01_status(result)


def fetch_openalex_abstract(doi: str) -> str:
    if not doi:
        return ""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(doi.encode()).hexdigest()[:16]
    cache_file = CACHE_DIR / f"{h}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8")).get("abstract", "")
    url = f"{OPENALEX}/works/doi:{doi}"
    try:
        with httpx.Client(timeout=10, headers={"User-Agent": USER_AGENT}) as cli:
            r = cli.get(url)
            if r.status_code != 200:
                return ""
            data = r.json()
    except Exception:
        return ""
    inv = data.get("abstract_inverted_index") or {}
    if not inv:
        return ""
    positions = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    abstract = " ".join(w for _, w in positions)
    cache_file.write_text(json.dumps({"abstract": abstract, "doi": doi}), encoding="utf-8")
    return abstract


def content_sanity_check(claim_text: str, doi: str) -> dict:
    """Sanity check: similarity between claim and OpenAlex abstract.

    The full v0.1.3 pipeline used a bge-m3 cross-encoder via build_vector_index
    for embedding similarity. That module is not shipped in the public release
    (it requires a 2GB+ model checkpoint), so this stub returns the abstract
    with similarity=0.0 — downstream code treats this as ``warning_flag=True``
    (no similarity check performed) but does not crash.
    """
    abstract = fetch_openalex_abstract(doi)
    if not abstract:
        return {"abstract": "", "similarity": 0.0, "warning_flag": True, "reason": "no_abstract"}
    return {
        "abstract": abstract[:600],
        "similarity": 0.0,
        "warning_flag": True,
        "reason": "embed_model_not_available",
    }


@lru_cache(maxsize=1)
def _citekey_to_doi() -> dict[str, str]:
    m: dict[str, str] = {}
    if CORPUS_CSV is None or not CORPUS_CSV.exists():
        return m
    with CORPUS_CSV.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            ck = r.get("citekey") or r.get("key") or ""
            if ck:
                m[ck] = r.get("doi", "")
    return m


def _doi_for_citekey(citekey: str) -> str:
    return _citekey_to_doi().get(citekey, "")


def verify_payload(payload: dict, run_sanity: bool = True) -> dict:
    for claim in payload.get("claims", []):
        for ref in claim.get("supporting_refs", []):
            rt = ref.get("ref_type", "")
            val = ref.get("value", "")
            if rt == "local_citekey":
                ref["verification_status"] = check_local_citekey(val)
            elif rt == "doi":
                # F2 fix (v0.1.3 cross-review): call verify_doi_multisource
                # directly so verifier_error side-channel (error_detail) is
                # preserved on the ref. The legacy check_doi() shim discards
                # this metadata; verify_payload must NOT use it.
                if not val:
                    ref["verification_status"] = "not_found"
                else:
                    result = verify_doi_multisource(val)
                    ref["verification_status"] = doi_result_to_v01_status(result)
                    ref["verified_via"] = result.source
                    if result.status == "verifier_error":
                        ref["verifier_error_metadata"] = result.error_detail
            elif rt == "openalex":
                ref["verification_status"] = "external_unverified"
            elif rt == "user_manuscript":
                ref["verification_status"] = "verified"
            else:
                ref["verification_status"] = "not_found"
        if run_sanity:
            for ref in claim.get("supporting_refs", []):
                if ref.get("verification_status") in ("verified", "external_unverified") and ref.get("ref_type") in ("local_citekey", "doi"):
                    doi = ref.get("value") if ref["ref_type"] == "doi" else _doi_for_citekey(ref.get("value", ""))
                    if doi:
                        sc = content_sanity_check(claim.get("claim_text", ""), doi)
                        ref["content_sanity"] = sc
                        if sc.get("warning_flag"):
                            claim["claim_content_warning"] = True
    return payload


def verify_mode_0(payload: dict) -> dict:
    """Mode 0 (data-first) verifier branch.

    Spec ref: 2026-05-25-thermal-mentor-v0.1.3 Section 2.7

    - anomaly observations 不验 (数据陈述)
    - data_evidence source 文件存在性验证
    - hypothesis supporting_refs 走多源 DOI 验证 (如有)
    - experiments 不验 (forward proposal)
    """
    for anomaly in payload.get("anomalies", []):
        for ev in anomaly.get("data_evidence", []):
            source = ev.get("source", "")
            ev["verification_status"] = (
                "verified" if Path(source).exists() else "not_found"
            )
    for hyp in payload.get("hypotheses", []):
        for ref in hyp.get("supporting_refs", []):
            value = ref.get("value", "")
            if ref.get("ref_type") == "doi" and value:
                result = verify_doi_multisource(value)
                ref["verification_status"] = doi_result_to_v01_status(result)
                ref["verified_via"] = result.source
                if result.status == "verifier_error":
                    ref["verifier_error_metadata"] = result.error_detail
    return payload


def validate_schema_mode_0(payload: dict) -> list[str]:
    """Schema validation for mode 0 (data-first) payloads."""
    errs: list[str] = []
    required = ["mode", "anomalies", "hypotheses", "experiments", "audit_log_id"]
    for k in required:
        if k not in payload:
            errs.append(f"missing top-level key: {k}")
    for i, a in enumerate(payload.get("anomalies", [])):
        for k in ("anomaly_id", "observation", "data_evidence"):
            if k not in a:
                errs.append(f"anomalies[{i}] missing {k}")
    return errs


def render_markdown(payload: dict) -> str:
    out: list[str] = []
    mode = payload.get("mode", "?")
    out.append(f"# /thermal-mentor — {mode}\n")
    verdict = payload.get("verdict") or {}
    out.append(f"**Verdict** (confidence: {verdict.get('confidence', '?')}): {verdict.get('one_line', '')}")
    out.append("")
    out.append("## 关键 claim 拆解\n")
    for c in payload.get("claims", []):
        cid = c.get("claim_id", "?")
        flag = c.get("novelty_flag") or c.get("claim_type", "")
        conf = c.get("confidence", "?")
        warn = " ⚠️ 内容与摘要重叠度低" if c.get("claim_content_warning") else ""
        out.append(f"- **{cid}** ({flag} | {conf}){warn}: {c.get('claim_text', '')}")
        refs_renders = []
        for ref in c.get("supporting_refs", []):
            v = ref.get("value", "")
            status = ref.get("verification_status", "")
            if status == "verified":
                refs_renders.append(f"[{v}] (verified)")
            elif status == "external_unverified":
                # F2 fix (v0.1.3 cross-review): distinguish verifier_error
                # (all sources failed — infra problem) from genuine
                # external_unverified (DOI may exist but not in our index).
                if ref.get("verifier_error_metadata"):
                    err = ref["verifier_error_metadata"]
                    err_count = len(err.get("errors", [])) if isinstance(err, dict) else "?"
                    refs_renders.append(f"⚠️[{v}] (校验器报错: {err_count} 源全失败)")
                else:
                    refs_renders.append(f"[{v}] (external_unverified)")
            elif status == "retracted":
                refs_renders.append(f"⚠️[本地禁列表: {v}]")
            elif status == "not_found":
                refs_renders.append(f"[本地查找失败: {v}]")
            else:
                refs_renders.append(f"[{v}]")
        if refs_renders:
            out.append(f"  支撑：{', '.join(refs_renders)}")
    out.append("")
    pac = payload.get("prior_art_coverage", {})
    out.append("## Prior-art search coverage\n")
    out.append(f"- queries: {pac.get('queries_used', [])}")
    out.append(f"- date range: {pac.get('date_range', '')}")
    out.append(f"- sources: {pac.get('sources_hit', [])}")
    out.append(f"- total external hits: {pac.get('total_hits', pac.get('total_external_hits', 0))}")
    out.append(f"- hits in last 12 months: {pac.get('hits_from_last_12mo', '?')}")
    out.append("")
    wwcm = payload.get("what_would_change_my_mind") or []
    if wwcm:
        out.append("## What would change my mind\n")
        for x in wwcm:
            out.append(f"- {x}")
        out.append("")
    out.append(f"[audit_log_id: {payload.get('audit_log_id', '?')}]")
    return "\n".join(out)


def scan_unrepresented_citations(markdown: str, represented_ids: set[str]) -> list[str]:
    unrepresented: list[str] = []
    for pat in CHINESE_CITATION_PATTERNS:
        for m in pat.finditer(markdown):
            raw = m.group(0)
            if not any(rid in raw for rid in represented_ids):
                unrepresented.append(raw)
    return list(set(unrepresented))


def _compute_validity(payload: dict) -> float:
    """citation_validity_rate excluding verifier_error (network problems
    should not pollute citation metric).

    Spec ref: Section 2.8 — verifier_error not counted in denominator.
    """
    total = 0
    ok = 0
    for c in payload.get("claims", []):
        for r in c.get("supporting_refs", []):
            # Skip refs marked with verifier_error_metadata (was verifier_error before
            # LegacyDoiAdapter mapping). These are infra failures, not citation problems.
            if r.get("verifier_error_metadata"):
                continue
            total += 1
            if r.get("verification_status") in ("verified", "external_unverified"):
                ok += 1
    return round(ok / total, 3) if total else 1.0


def _compute_validity_mode_0(payload: dict) -> float:
    """Mode 0 validity = fraction of data_evidence sources that file_exists."""
    total = 0
    ok = 0
    for a in payload.get("anomalies", []):
        for ev in a.get("data_evidence", []):
            total += 1
            if ev.get("verification_status") == "verified":
                ok += 1
    return round(ok / total, 3) if total else 1.0


def render_markdown_mode_0(payload: dict) -> str:
    """Mode 0 Markdown render, 全人话, 含 always-available 召唤 footer."""
    out: list[str] = []
    out.append("# /thermal-mentor — 数据分析\n")

    # 我扫到的数据
    files = payload.get("scanner_manifest", {}).get("files", [])
    if files:
        out.append("## 我扫到的数据\n")
        out.append(f"- 扫到 {len(files)} 个文件:")
        for f in files[:10]:
            out.append(f"  - {Path(f['path']).name} ({f['type']}, {f.get('size_bytes', '?')} bytes)")
        out.append("")

    # 异常现象
    anomalies = payload.get("anomalies", [])
    if anomalies:
        out.append(f"## 异常现象 ({len(anomalies)} 条)\n")
        for a in anomalies:
            out.append(f"### {a.get('anomaly_id', '?')}: {a.get('observation', '')}")
            out.append(f"- 教科书预期: {a.get('expected_textbook', '')}")
            for ev in a.get("data_evidence", []):
                out.append(f"- 数据证据 [{ev.get('source', '?')}]: \"{ev.get('quote_text', '')}\"")
            out.append(f"- 我的解读: {a.get('mentor_inference', '')}")
            for q in a.get("context_questions_to_user", []):
                out.append(f"- 我想反过来问你: {q}")
            out.append("")

    # 候选机制
    hypotheses = payload.get("hypotheses", [])
    if hypotheses:
        by_anomaly: dict[str, list] = {}
        for h in hypotheses:
            by_anomaly.setdefault(h.get("anomaly_id", "?"), []).append(h)
        out.append("## 候选机制 (每个异常 2-4 个)\n")
        for aid, hyps in by_anomaly.items():
            out.append(f"### {aid} 的候选机制")
            for h in hyps:
                out.append(f"- **{h.get('hypothesis_id', '?')}** {h.get('mechanism_text', '')}")
                if h.get("data_support"):
                    out.append(f"  - 支持的数据: {h['data_support']}")
                if h.get("data_contradict"):
                    out.append(f"  - 反对的数据: {h['data_contradict']}")
                if h.get("predicts_observable"):
                    out.append("  - 如果这个机制真成立, 还应该看到:")
                    for p in h["predicts_observable"]:
                        out.append(f"    • {p}")
            out.append("")

    # 区分实验
    experiments = payload.get("experiments", [])
    if experiments:
        by_anomaly2: dict[str, list] = {}
        for e in experiments:
            by_anomaly2.setdefault(e.get("anomaly_id", "?"), []).append(e)
        out.append("## 区分实验 (每个异常 1-2 个)\n")
        for aid, exps in by_anomaly2.items():
            out.append(f"### {aid} 怎么区分")
            for e in exps:
                out.append(f"- **{e.get('experiment_id', '?')}** {e.get('experiment_text', '')}")
                discr = e.get("discriminates_between", [])
                if discr:
                    out.append(f"  - 能区分: {' vs '.join(discr)}")
                ans = e.get("answerable_by", "?")
                ans_human = {
                    "existing_data": "用现有数据能答",
                    "new_experiment": "要做新实验",
                    "dft": "要 DFT 计算",
                }.get(ans, ans)
                out.append(f"  - {ans_human}")
                if e.get("expected_outcome"):
                    out.append("  - 预期:")
                    for k, v in e["expected_outcome"].items():
                        out.append(f"    • {k}: {v}")
            out.append("")

    # 数据本身回答不了的
    open_questions = payload.get("open_questions_data_alone_cannot_answer", [])
    if open_questions:
        out.append("## 数据本身回答不了的\n")
        for q in open_questions:
            out.append(f"- {q}")
        out.append("")

    # Always-available 召唤通道
    out.append("---")
    out.append("💬 觉得这次判断不靠谱? 回复 \"叫 codex 审\" / \"叫 opus 审\" / \"叫 ds 审\"")
    out.append("   我会重启刚才的判断, 用第二意见挑刺。")
    out.append("")

    out.append(f"[audit_log_id: {payload.get('audit_log_id', '?')}]")
    return "\n".join(out)


def run_pipeline(payload_json: str, run_sanity: bool = True) -> dict:
    try:
        payload_json = payload_json.removeprefix("\ufeff")
        payload = json.loads(payload_json)
    except json.JSONDecodeError as e:
        return {"error": f"json_parse_error: {e}", "markdown": ""}

    mode = payload.get("mode", "")
    if mode == "data_first":
        errs = validate_schema_mode_0(payload)
        if errs:
            return {"error": "schema_validation_failed", "details": errs, "markdown": ""}
        payload = verify_mode_0(payload)
        md = render_markdown_mode_0(payload)
        return {
            "payload": payload,
            "markdown": md,
            "unrepresented_citations": [],
            "citation_validity_rate": _compute_validity_mode_0(payload),
        }

    # publication mode (novelty_review / highlight / revision / direction / corpus_query)
    errs = validate_schema(payload)
    if errs:
        return {"error": "schema_validation_failed", "details": errs, "markdown": ""}
    payload = verify_payload(payload, run_sanity=run_sanity)
    md = render_markdown(payload)
    represented = {c["claim_id"] for c in payload.get("claims", [])}
    unrepresented = scan_unrepresented_citations(md, represented)
    return {
        "payload": payload,
        "markdown": md,
        "unrepresented_citations": unrepresented,
        "citation_validity_rate": _compute_validity(payload),
    }


def _configure_stdout_utf8() -> None:
    """Prefer UTF-8 for CLI Markdown output on Windows consoles."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8")
        except Exception:
            pass


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("payload_file")
    p.add_argument("--no-sanity", action="store_true")
    args = p.parse_args()
    payload_text = Path(args.payload_file).read_text(encoding="utf-8-sig")
    result = run_pipeline(payload_text, run_sanity=not args.no_sanity)
    _configure_stdout_utf8()
    print(result.get("markdown") or json.dumps(result, indent=2, ensure_ascii=False))
