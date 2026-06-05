"""cross_review_merge — Round 3-4 Python: DOI verify + finding classification + Markdown.

Spec ref: 2026-05-25-science-mentor-v0.1.3 Section 4.4

Round 1-2 (each reviewer critique + roundtable update) is SKILL.md orchestration
(mentor session uses Agent tool to invoke reviewers). This module handles Round 3
(DOI non-discriminatory multi-source verification — first-wins ordering, no
reviewer singled out) + Round 4 (merge into final payload + Markdown render).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:  # package mode: python -m scripts.cross_review_merge
    from .doi_verify_multisource import verify_doi_multisource
except ImportError:  # script mode: python scripts/cross_review_merge.py
    from doi_verify_multisource import verify_doi_multisource


def classify_findings(reviews: dict[str, dict]) -> list[dict]:
    """Classify findings by reviewer overlap.

    consensus (all reviewers agree) -> confidence=high
    majority (2 of 3) -> confidence=medium
    singleton (1 of N) -> confidence=low

    Overlap detection: by finding text similarity (first 30 chars normalized).
    """
    all_findings: list[tuple[str, dict]] = []
    for reviewer, data in reviews.items():
        for f in data.get("findings", []):
            all_findings.append((reviewer, f))

    # Group by normalized text prefix
    groups: dict[str, list[tuple[str, dict]]] = {}
    for reviewer, f in all_findings:
        key = _normalize_for_grouping(f.get("text", ""))
        groups.setdefault(key, []).append((reviewer, f))

    n_reviewers = len(reviews)
    classified = []
    for key, group in groups.items():
        reviewers_in_group = set(r for r, _ in group)
        n_match = len(reviewers_in_group)
        if n_match == n_reviewers:
            confidence = "high"
        elif n_match >= max(2, (n_reviewers // 2) + 1):
            confidence = "medium"
        else:
            confidence = "low"
        # Use first finding as representative
        representative = group[0][1].copy()
        representative["reviewers"] = sorted(reviewers_in_group)
        representative["confidence"] = confidence
        representative["original_count"] = len(group)
        classified.append(representative)
    return classified


def _normalize_for_grouping(text: str) -> str:
    """First 30 chars, lowercased, stripped. Used for similarity grouping."""
    return text[:30].strip().lower()


def attribute_refs(reviews: dict[str, dict]) -> dict[str, str]:
    """Non-discriminatory attribution: all reviewers' introduced refs get source label.

    Spec 4.4.3: 三方对称, 不歧视 DS. Markdown render 会显式标 attribution.
    NOT marking DS-introduced refs as 'high_risk' or similar — just attribution.

    Note: this is first-wins ordering — if the same DOI is introduced by multiple
    reviewers, only the first one (by dict iteration order) is recorded. The intent
    is "no reviewer singled out as high risk", not bit-for-bit symmetric set ops.
    """
    out: dict[str, str] = {}
    for reviewer, data in reviews.items():
        for ref in data.get("introduced_refs", []):
            value = ref.get("value", "")
            if value and value not in out:
                out[value] = reviewer
    return out


def merge_reviews(reviews: dict[str, dict]) -> dict[str, Any]:
    """Round 3-4: verify all DOI + classify findings + record deletions.

    Returns:
      {
        "findings": [classified, ...],
        "surviving_refs": [refs that passed verification, ...],
        "deleted_refs": [refs that failed verification, ...],
        "attribution": {ref_value: reviewer},
        "reviewers_used": [list of reviewer names],
      }
    """
    findings = classify_findings(reviews)
    attribution = attribute_refs(reviews)

    surviving_refs = []
    deleted_refs = []
    unverifiable_refs = []  # verifier_error: network/infra failure, NOT a citation problem
    for ref_value, reviewer in attribution.items():
        result = verify_doi_multisource(ref_value)
        attribution_entry = {
            "value": ref_value,
            "introduced_by": reviewer,
            "verified_via": result.source,
            "status": result.status,
        }
        if result.status == "verified":
            surviving_refs.append(attribution_entry)
        elif result.status == "verifier_error":
            # Honor the project's "network failure != not verified" principle
            # (the same one verifier.py preserves via verifier_error_metadata):
            # do NOT delete on a transient outage — retain for retry.
            attribution_entry["error_detail"] = result.error_detail
            unverifiable_refs.append(attribution_entry)
        else:  # not_found
            deleted_refs.append(attribution_entry)

    return {
        "findings": findings,
        "surviving_refs": surviving_refs,
        "deleted_refs": deleted_refs,
        "unverifiable_refs": unverifiable_refs,
        "attribution": attribution,
        "reviewers_used": sorted(reviews.keys()),
    }


def render_merge_markdown(merged: dict[str, Any]) -> str:
    """Render Markdown for the merged cross-review result.

    Sections:
      ## Cross-review consensus findings (high/medium/low)
      ## Refs surviving verification (with non-discriminatory attribution)
      ## Refs deleted by verification (论点 retained, ref dropped)
    """
    out: list[str] = []
    out.append("## Cross-review 共识 findings\n")

    for conf in ["high", "medium", "low"]:
        bucket = [f for f in merged["findings"] if f["confidence"] == conf]
        if not bucket:
            continue
        out.append(f"### {conf.upper()} confidence ({len(bucket)})\n")
        for f in bucket:
            reviewers = ", ".join(f.get("reviewers", []))
            out.append(f"- **{f.get('id', '?')}** [{reviewers}]: {f.get('text', '')}")
        out.append("")

    out.append("## 通过验证的引用 (三方对称标注)\n")
    for ref in merged["surviving_refs"]:
        out.append(
            f"- `{ref['value']}` — {ref['introduced_by']} 引入, "
            f"已 {ref['verified_via']} 通过"
        )
    out.append("")

    if merged["deleted_refs"]:
        out.append("## 验证不通过, 已剔除 (论点保留)\n")
        for ref in merged["deleted_refs"]:
            out.append(
                f"- ~~`{ref['value']}`~~ — {ref['introduced_by']} 引入, "
                f"{ref['verified_via']} {ref['status']}"
            )
        out.append("")

    if merged.get("unverifiable_refs"):
        out.append("## 暂时无法核验 (网络问题, 非引用错误 — 保留待重试)\n")
        for ref in merged["unverifiable_refs"]:
            out.append(
                f"- ⚠️ `{ref['value']}` — {ref['introduced_by']} 引入, "
                f"校验器报错 (网络故障), 未剔除"
            )
        out.append("")

    return "\n".join(out)


def main() -> None:
    """CLI: python cross_review_merge.py <round_json_files>... --out final.json

    Each input JSON must have keys: reviewer (str), findings (list), introduced_refs (list).
    """
    import argparse
    import json
    import sys

    p = argparse.ArgumentParser(
        description="Merge multi-reviewer round-table JSON into final cross-review report."
    )
    p.add_argument("round_files", nargs="+", type=Path,
                   help="One or more reviewer round JSON files")
    p.add_argument("--out", type=Path, required=True,
                   help="Output path for merged JSON; sibling .md is also written")
    args = p.parse_args()

    reviews: dict[str, dict] = {}
    for f in args.round_files:
        if not f.exists():
            print(f"[warn] skipping missing file: {f}", file=sys.stderr)
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[error] cannot parse {f}: {e}", file=sys.stderr)
            sys.exit(2)
        reviewer = data.get("reviewer", f.stem)
        # Merge multiple rounds from same reviewer (round 2 overrides round 1)
        reviews[reviewer] = {
            "findings": data.get("findings", []),
            "introduced_refs": data.get("introduced_refs", []),
        }

    if not reviews:
        print("[error] no valid reviewer inputs", file=sys.stderr)
        sys.exit(1)

    merged = merge_reviews(reviews)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )

    md_path = args.out.with_suffix(".md")
    md_path.write_text(render_merge_markdown(merged), encoding="utf-8")

    print(f"[saved] merged JSON: {args.out}")
    print(f"[saved] merged Markdown: {md_path}")
    print(
        f"[summary] {len(reviews)} reviewers, "
        f"{len(merged['findings'])} findings, "
        f"{len(merged['surviving_refs'])} surviving refs, "
        f"{len(merged['deleted_refs'])} deleted refs"
    )


if __name__ == "__main__":
    main()
