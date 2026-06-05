"""Manuscript brief pipeline — chunk + read + merge utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def split_into_chunks(text: str, chunk_tokens: int = 4000, overlap: int = 400) -> list[str]:
    """Split by whitespace tokens with overlap. Token ~= whitespace word."""
    tokens = text.split()
    if not tokens:
        return []
    chunks: list[str] = []
    step = chunk_tokens - overlap
    i = 0
    while i < len(tokens):
        chunk = tokens[i : i + chunk_tokens]
        chunks.append(" ".join(chunk))
        if i + chunk_tokens >= len(tokens):
            break
        i += step
    return chunks


def read_text(path: Path) -> str:
    """Read text from .md / .txt / .docx / .pdf."""
    suffix = path.suffix.lower()
    if suffix in (".md", ".txt"):
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".docx":
        import docx
        d = docx.Document(str(path))
        return "\n".join(p.text for p in d.paragraphs if p.text.strip())
    if suffix == ".pdf":
        import pymupdf
        out = []
        with pymupdf.open(str(path)) as doc:
            for page in doc:
                out.append(page.get_text())
        return "\n".join(out)
    raise ValueError(f"Unsupported file type: {suffix}")


def merge_chunk_briefs(per_chunk_briefs: list[dict[str, Any]]) -> dict[str, Any]:
    """Reduce per-chunk brief dicts into one final brief."""
    merged: dict[str, list] = {
        "central_claims": [],
        "method_claims": [],
        "performance_claims": [],
        "citations_used": [],
        "evidence_spans": [],
    }
    materials = []
    for b in per_chunk_briefs:
        for k in ("central_claims", "method_claims", "performance_claims", "citations_used", "evidence_spans"):
            v = b.get(k) or []
            if isinstance(v, list):
                merged[k].extend(v)
            elif v:
                merged[k].append(v)
        if b.get("study_system"):
            materials.append(b["study_system"])
    for k in merged:
        seen = set()
        unique = []
        for item in merged[k]:
            key = item if isinstance(item, str) else str(item)
            if key not in seen:
                seen.add(key)
                unique.append(item)
        merged[k] = unique
    merged["study_system"] = " | ".join(sorted(set(materials))) if materials else ""
    return merged


def brief_to_markdown(brief: dict[str, Any]) -> str:
    """Compact markdown rendering for the mentor prompt."""
    lines = ["# Manuscript brief\n"]
    if brief.get("study_system"):
        lines.append(f"**Study system**: {brief['study_system']}\n")
    for label, key in (
        ("Central claims", "central_claims"),
        ("Method claims", "method_claims"),
        ("Performance claims", "performance_claims"),
        ("Citations used", "citations_used"),
    ):
        items = brief.get(key) or []
        if items:
            lines.append(f"**{label}**:")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")
    spans = brief.get("evidence_spans") or []
    if spans:
        lines.append("**Key evidence spans**:")
        for s in spans[:10]:
            quote = s.get("quote") if isinstance(s, dict) else s
            lines.append(f"  > {quote}"[:500])
        lines.append("")
    return "\n".join(lines)


def build_manuscript_scaffold(path: Path) -> dict[str, Any]:
    """Read a manuscript file into a scaffold brief (text + chunks).

    Like ``anomaly_brief``'s scanner half, this is the deterministic part: it
    extracts text and splits it into chunks. The LLM-enriched fields
    (central_claims / method_claims / ...) are left empty for the mentor session
    to fill (it cannot be done in a Python subprocess).
    """
    path = Path(path)
    text = read_text(path)
    return {
        "source": str(path),
        "text": text,
        "chunks": split_into_chunks(text),
        "central_claims": [],
        "method_claims": [],
        "performance_claims": [],
        "citations_used": [],
        "evidence_spans": [],
        "study_system": "",
    }


def main() -> None:
    import argparse
    import json
    import sys
    p = argparse.ArgumentParser(description="Extract a manuscript brief scaffold (text + chunks).")
    p.add_argument("path", help="manuscript file (.md/.txt/.docx/.pdf)")
    p.add_argument("--out", default="tmp/brief.json", help="output JSON path")
    args = p.parse_args()
    brief = build_manuscript_scaffold(Path(args.path))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8")
        except Exception:
            pass
    print(f"[saved] {out_path} (scaffold: {len(brief['chunks'])} chunks; "
          f"mentor session must fill central_claims/etc.)")


if __name__ == "__main__":
    main()
