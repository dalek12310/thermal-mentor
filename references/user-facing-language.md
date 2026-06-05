# 人话 hard rule — user-facing language

The skill talks to the user with **plain Chinese (人话)** — no internal codename leaks into anything the user reads.

## Rationale

Earlier versions mixed internal codename (`mode 0`, `L1/L3`, `anomaly_brief`, JSON field names like `claim_id`, `supporting_refs`) into AskUserQuestion options and Markdown rendering. This made the skill feel like a tool dressed as a mentor — the opposite of the design intent. The hard rule fixes this at the surface boundary.

## Allowed codename contexts

Internal codename is **fine** in:

- `SKILL.md` (the orchestration spec, read by Claude not the user).
- Python source code (`anomaly_brief.py`, `verifier.py`, `cross_review_merge.py`, ...).
- Mentor *inner monologue* (the silent reasoning step in Step 1).
- `tmp/payload.json` and other on-disk JSON artifacts (audit / acceptance traces; not user-facing).
- Audit log entries (`audit_log/{YYYY-MM}.jsonl`).
- Reference docs in this directory (`references/*.md`) — these are read by Claude, not the user.

## Forbidden codename contexts

Internal codename **must not** appear in:

- `AskUserQuestion` option labels, descriptions, or headers.
- Final Markdown rendered by Step H.
- Error messages shown to the user (e.g. cwd-empty fallback prompt).
- The always-available 召唤 footer.
- The resume instruction emitted by `paper_pdf_handoff.render_resume_instruction`.

Examples of leaks to avoid:

| Forbidden | Preferred |
|---|---|
| "进入 mode 0" | "深挖数据异常" |
| "L1 命中 8 条" | "本地文献库找到 8 篇相关" |
| "L3 fan-out" | "在公开学术数据库再查一轮" |
| "candidate_anomalies surfaced 4 条" | "我从你数据里看到 4 个异常现象" |
| "supporting_refs 全 verified" | "引用都查过, 都对得上" |
| "audit_log_id 20260525-103200" | "本次记录已存档" (only show id if user explicitly asks) |
| "anomaly_id A1" | 用纯序号 "异常 1" 或直接 "氧空位单调下降" |
| "hypothesis_id H1a" | "候选机制 1" 或直接 "dual-site self-compensation 假设" |
| "predicts_observable" | "如果这个机制真成立, 还应该看到…" |
| "answerable_by=existing_data" | "用你现有数据就能答" |
| "verifier_error" | "校验器报错 (网络问题, 非引用错误)" |
| "scanner_manifest" | "扫描记录" (only if user asks) |
| "data_brief_hash" | not shown to user at all |

## Preserved technical terms

The list of domain terms kept verbatim comes from the **active domain pack**'s `preserved_terms`
slot (default `domains/thermal.md`) — translating them would harm clarity. The thermal pack, for
example, preserves DFT/DFPT/AIMD/MLIP, XAFS/EXAFS/XPS/Raman/TEM, phonon/e-ph, κ/ZT/TBC,
Kröger-Vink/Shannon radii/Boltzmann. Swap the pack for another field's term set (see
[`domains/`](../domains/)).

Infrastructure terms — `DOI / arXiv / OpenAlex / Crossref / Semantic Scholar / WoS` — are
preserved in **every** pack regardless of field.

These terms appear in the user's own writing and in standard textbooks; mentor uses them with a Chinese connector when needed (e.g. "EXAFS 看配位数").

## Translation table — codename → 人话

| Internal codename | Pipeline meaning | User-facing 人话 |
|---|---|---|
| mode 0 / data-first | data anomaly enumeration pipeline | 深挖数据 / 看你数据里有什么意外 |
| publication-strategy | v0.1 5-mode pipeline | 评估投稿策略 / 想看创新性和卖点 |
| both | mode 0 → publication chained | 先深挖数据, 再评估投稿 |
| L1 retrieval | hybrid_retrieve bge-m3 + BM25 | 翻本地文献库 |
| L3 fan-out | live_search.py 多源 API | 公开学术数据库再查一轮 |
| anomaly enumeration | Step B | 列出异常现象 |
| hypothesis enumeration | Step E | 提候选机制 |
| discriminating experiment | Step F | 区分实验 / 怎么验 |
| predicts_observable | "what else mechanism implies" | 如果这个机制真成立, 还应该看到… |
| anchor registry | 锚点研究者 YAML 集合 | 主流研究者档案 |
| retraction blacklist | retraction filter | 撤稿过滤 |
| verifier / check_doi | verifier.py 多源 DOI | 引用核对 |
| verifier_error | 多源 chain 全宕 | 校验器报错 (网络问题) |
| cross-review round-table | Section 4 三方审 | 叫第二意见来挑刺 |
| 召唤 footer | Section 4.5 always-available | "回复 '叫 codex 审' / '叫 opus 审' / '叫 ds 审'" |
| paper-pdf-acquisition handoff | Section 4.8 manifest 协议 | 让 PDF 工具去拉全文, 跑完回来 |
| handover schema | Section 2.10.1 mode_0 → publication | (用户不需要知道, 自动续接) |
| acceptance run | run_acceptance.py 落盘 | 这次跑的存档 |
| audit_log | JSONL append-only | 内部日志 |

## Enforcement

`SKILL.md` Hard rule #5 references this file. Cross-review checks in Step F.5 / always-available 召唤 should scan rendered Markdown for forbidden codename strings (manual visual check sufficient; automated linter is a future enhancement).
