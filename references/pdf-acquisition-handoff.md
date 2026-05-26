# paper-pdf-acquisition handoff protocol

`paper-pdf-acquisition` is an Edge / CARSI / Shibboleth interactive skill — it cannot be called as a Python API. `thermal-mentor` collaborates with it **across sessions** via a manifest CSV + a resume instruction the user runs in a new Claude Code session.

## Why manifest + resume, not inline call

The `paper-pdf-acquisition` skill enforces 5 immutable hard rules:

1. No Sci-Hub.
2. No Cloudflare bypass.
3. Clean Edge profile (CARSI / Shibboleth login).
4. No Zotero SQLite write without explicit user authorization.
5. Validate every PDF (header check).

Rules 2-3 require a Chrome DevTools Protocol session piloting a real Edge profile the user authenticated. Embedding that into thermal-mentor's pipeline would either bypass user authentication (rule violation) or block the entire skill on a 30-60 s setup ceremony every invocation. Decision: lazy invoke on demand, **cross-session manifest handoff**.

The handoff is implemented by `paper_pdf_handoff.py` — it writes a manifest CSV and a human-readable resume instruction. It does **not** invoke Edge / CDP / publisher APIs.

## T1 / T2 / T3 trigger conditions

| Trigger | Who triggers | Mentor behavior |
|---|---|---|
| **T1 — user explicit request** | User: "我想看这篇 [DOI]" / "深挖 [citekey]" / "把这几篇 paper 拉下来再分析" | Mentor invokes `paper_pdf_handoff.write_manifest` + `render_resume_instruction`, appends to current Markdown |
| **T2 — mentor active recommendation** | Mode 0 Step E identifies a paper as **critical** for hypothesis validation | Mentor does **NOT interrupt the pipeline**. Recommendation goes into the **final** Markdown end (after Step H), the user decides whether to spin up paper-pdf-acquisition |
| **T3 — verifier_error fallback** | Section 4.4 multi-source chain returns `verifier_error` for a DOI a reviewer insists on | Markdown adds: "可调 paper-pdf-acquisition 物理验证 DOI 存在性, 需要你启动 Edge 走 CARSI" |

T2 is **non-interrupting** by design. The cost of breaking session flow + asking the user to launch CARSI mid-pipeline outweighs the value of an inline PDF retrieval in most cases.

## Manifest CSV schema

`paper_pdf_handoff.write_manifest` writes `tmp/pdf_handoff_<audit_log_id>.csv`:

| Column | Description |
|---|---|
| `doi` | DOI string. Required if no citekey. |
| `citekey` | Local corpus citekey (matches your reference manager). Required if no DOI. |
| `why_needed` | Plain-text reason: "验证 H1a hypothesis 的关键证据" / "用户 trigger 显式要求深挖" |
| `expected_section` | Which manuscript section the mentor will read once full text arrives: `methods` / `results` / `discussion` / `full` |
| `resume_token` | `audit_log_id` of the current mentor run. Mentor uses this to relink the fulltext back to the paused run when the user returns. |

**Max 5 rows per manifest** — `paper_pdf_handoff.MAX_DOI_PER_MANIFEST = 5`. Larger requests should be split into multiple handoffs. The cap prevents accidental "pull every paper in the L3 results" requests.

Manifest CSV is written with `csv.DictWriter` + UTF-8 + LF line endings (cross-platform friendly).

## Resume instruction template

`paper_pdf_handoff.render_resume_instruction(manifest_path, audit_log_id, doi_list)` emits this human-readable block, which the mentor appends to the Markdown:

```
我需要这些 paper 的全文才能验证当前 hypothesis (audit_log_id=<id>):

  - <DOI 1>
  - <DOI 2>
  - ...

请在**新会话**跑:
  /paper-pdf-acquisition 用 tmp/pdf_handoff_<id>.csv

完成后回到本 session 跟我说 "PDF 拿好了, 继续 <audit_log_id>",
我会读 04_fulltext/ 下提取的文本进行 hypothesis 验证。

(paper-pdf-acquisition 走你机构 CARSI/Shibboleth 合法路径, 不绕 Cloudflare,
不用 Sci-Hub。如果 CARSI 没机构订阅, 该 paper 会被 paper-pdf-acquisition
显式 mark 为 unresolved, 不会假装下载成功。)
```

Notes:

- The 5-rule guarantee is restated in the instruction — reminds the user there is no shortcut and sets the expectation that some DOIs may come back `unresolved`.
- The "PDF 拿好了, 继续 <audit_log_id>" reply pattern is the **only** way the original session resumes — mentor scans for this keyword + audit_log_id pair.

## Cross-session collaboration protocol

End-to-end flow:

1. **Mentor session (original)** — mentor decides T1/T2/T3 fires:
   - Calls `paper_pdf_handoff.write_manifest(out_path, rows)` → CSV on disk.
   - Calls `paper_pdf_handoff.render_resume_instruction(...)` → Markdown block.
   - Appends Markdown block to the current report (mode 0 Step H output, publication final, or 召唤 follow-up).
   - Saves payload state to `tmp/payload.json` so the resume step can read it.

2. **User opens new Claude Code session** — typically in the same project root.
   - Runs `/paper-pdf-acquisition` with the CSV path the mentor emitted.
   - `paper-pdf-acquisition` skill follows its own decision tree:
     - Open Access (Unpaywall) → direct download.
     - CARSI / Shibboleth → user authenticates once per Edge profile session.
     - WebVPN / Service Worker → fallback for some Chinese institutions.
     - arXiv → if a preprint exists.
     - `unresolved` → explicit failure, recorded in the manifest's status file.
   - Successful downloads land in a project-local PDF queue directory.
   - Text extraction pipeline runs and writes `04_fulltext/<citekey>.txt`.

3. **User returns to mentor session** with a reply like:
   `PDF 拿好了, 继续 20260525-103200-xyz789`
   - Mentor matches `(audit_log_id=20260525-103200-xyz789)`.
   - Reads the manifest CSV at `tmp/pdf_handoff_<id>.csv`.
   - For each row, locates `04_fulltext/<citekey>.txt` (or by DOI lookup → citekey).
   - Re-enters Step E hypothesis enumeration with the full text appended to the reasoning context.
   - Saves the new payload to a fresh acceptance file, with `linked_audit_log_id=<original id>` for lineage.

If the user reports "几篇没拿到" or the manifest's status file shows `unresolved`:

- Mentor adjusts hypotheses based on partial fulltext (still useful — even 2 of 5 papers can shift the analysis).
- Mentor flags the unresolved DOIs in the new Markdown with `[unresolved — 全文不可达, hypothesis 仍待 falsify]`.

## What mentor must NOT do

- Mentor must not call paper-pdf-acquisition Python modules directly from within the same session — they require a piloted Edge profile.
- Mentor must not bypass any of paper-pdf-acquisition's 5 hard rules. If a paper comes back `unresolved`, that is the canonical outcome; mentor states the hypothesis remains testable but lacks one piece of evidence.
- Mentor must not write to the manifest CSV without explicit user authorization for T1. T2 / T3 manifests are mentor-initiated but the user always has the option to ignore the resume instruction.
- Mentor must not stage > 5 DOIs in a single manifest. Split into multiple handoffs if needed.
