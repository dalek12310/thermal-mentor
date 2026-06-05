"""paper_pdf_handoff — manifest CSV + resume instruction for paper-pdf-acquisition skill.

Spec ref: 2026-05-25-science-mentor-v0.1.3 Section 4.8.3

This script does NOT invoke Edge/CDP/publisher APIs. It writes a CSV manifest +
generates a human-readable resume instruction Markdown block. The actual PDF
acquisition is performed by /paper-pdf-acquisition skill in a separate session,
following its own hard rules (No Sci-Hub / No CF bypass / Clean Edge profile).
"""
from __future__ import annotations

import csv
from pathlib import Path

MAX_DOI_PER_MANIFEST = 5

MANIFEST_FIELDS = ["doi", "citekey", "why_needed", "expected_section", "resume_token"]


def write_manifest(out_path: Path, rows: list[dict]) -> None:
    """Write DOI handoff manifest CSV. Max 5 DOI per manifest."""
    if len(rows) > MAX_DOI_PER_MANIFEST:
        raise ValueError(
            f"manifest has {len(rows)} rows, max {MAX_DOI_PER_MANIFEST} per spec 4.8.3"
        )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in MANIFEST_FIELDS})


def render_resume_instruction(
    manifest_path: Path,
    audit_log_id: str,
    doi_list: list[str],
) -> str:
    """Render human-readable resume instruction for user to run /paper-pdf-acquisition.

    Spec ref: Section 4.8.3 step 2
    """
    doi_lines = "\n".join(f"  - {d}" for d in doi_list)
    return f"""
我需要这些 paper 的全文才能验证当前 hypothesis (audit_log_id={audit_log_id}):

{doi_lines}

请在**新会话**跑:
  /paper-pdf-acquisition 用 {manifest_path}

完成后回到本 session 跟我说 "PDF 拿好了, 继续 {audit_log_id}",
我会读 04_fulltext/ 下提取的文本进行 hypothesis 验证。

(paper-pdf-acquisition 走你机构 CARSI/Shibboleth 合法路径, 不绕 Cloudflare,
不用 Sci-Hub。如果 CARSI 没机构订阅, 该 paper 会被 paper-pdf-acquisition
显式 mark 为 unresolved, 不会假装下载成功。)
"""
