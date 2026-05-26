# Cross-review round-table protocol

Spec ref: v0.1.3 Section 4 (4.1 motivation, 4.3 trigger UI, 4.4 protocol, 4.5 always-available 召唤, 4.8 paper-pdf-acquisition联动).

The mentor can call in second opinions from one or several independent reviewers (Opus subagent / Codex GPT-5 xhigh / DeepSeek V4 Pro) at user request. This is **never the default** — runs 30-90 min and adds latency the user does not need on most invocations.

## When cross-review fires

| Trigger point | Mode | Where in pipeline |
|---|---|---|
| User picks reviewers in Step F.5 gate | `data-first` / `both` | After Step F (discriminating experiment), before Step G (verifier) |
| User picks reviewers in v0.1 publication gate | `publication-strategy` | After mentor JSON output, before verifier |
| Always-available 召唤 keyword reply | any mode | After final Markdown was rendered; reuses last `tmp/payload.json` (does not re-run Step A-F) |

The reviewer panel is **flat** — no hierarchy, no model is more authoritative than the others. The mentor (Claude session running this skill) is the chair, *not* a reviewer.

## Round 1-4 flow

### Round 1 — parallel independent critique

Mentor uses the `Agent` tool to spawn each selected reviewer **in parallel** within a single message. Each reviewer receives the same input (mentor payload JSON + current spec / brief context).

```
spawned in parallel via Agent tool:
  - Opus 4.7 subagent  (subagent_type=general-purpose, model=opus)
  - Codex GPT-5 xhigh  (subagent_type=codex:codex-rescue or codex:rescue)
  - DeepSeek V4 Pro    (subagent_type=deepseek-code-reviewer)
```

Each reviewer returns a critique JSON saved to `tmp/cross_review_round1_<reviewer>.json` with shape:

```json
{
  "reviewer": "opus|codex|ds",
  "findings": [
    {"text": "...", "severity": "critical|major|minor", "evidence": "...", "introduced_refs": [{"value": "doi/citekey", ...}]}
  ],
  "introduced_refs": [{"value": "doi or arxiv id", ...}],
  "round": 1
}
```

### Round 2 — cross-update with peer critiques

Mentor merges all three Round 1 critiques into one bundle and sends to each reviewer for an updated stance. Reviewers can:

- **Endorse** another reviewer's finding (raises confidence).
- **Refute** with counter-evidence.
- **Supplement** with additional detail.
- **Pass** if they have no evidence to add either way.

Output saved to `tmp/cross_review_round2_<reviewer>.json`.

Round 2 can run parallel or serial — parallel preferred for speed, serial useful if Codex stdout deadlock recurs.

### Round 3 — DOI multi-source verification (Python)

All DOIs / citekeys introduced by any reviewer go through `cross_review_merge.merge_reviews`, which calls `doi_verify_multisource.verify_doi_multisource` (spec Section 4.4.2). The chain:

```
OpenAlex (qps=10) → Crossref (qps=50, authoritative) → S2 (qps=1)
                  → Lens (qps=0.1) → [WoS if WOS_API_KEY] → DOI.org HEAD (authoritative)
```

Non-authoritative source `not_found` continues fallback; authoritative source `not_found` returns immediately. All-source HTTP failure → `verifier_error`.

Verified refs: keep, label with source attribution.
Not-found refs: **delete the ref but keep the finding text** (论点跟引用解耦). Mentioned in `cross_review.deleted_refs` for audit transparency.
Verifier-error refs: keep the finding, mark "校验器报错 (网络问题, 非引用错误)" in the final Markdown.

### Round 4 — merge into final payload

`cross_review_merge.classify_findings` groups findings by 30-char prefix similarity and assigns confidence:

- `high` — all reviewers agree (overlap = panel size).
- `medium` — majority agreement (≥⌈N/2⌉+1, but not all).
- `low` — singleton finding (one reviewer only).

`cross_review_merge.attribute_refs` adds **non-discriminatory attribution** for every ref any reviewer introduced (per Section 4.4.3). No reviewer is flagged "high risk" in the runtime Markdown — the DS historical fabrication rate (~75% per audit 2026-05-25) is recorded in the project CROSS_MODEL_REVIEW_SOP, not re-litigated in the user-facing report. (Technically: the merge uses first-wins ordering when the same DOI is introduced by multiple reviewers.)

The final payload appends:

```json
{
  "cross_review": {
    "reviewers_used": ["opus", "codex", "ds"],
    "round_table_summary": [{...classified findings...}],
    "deleted_refs": [{"value": "10.xxxx/...", "reason": "Crossref not_found", "introduced_by": "ds"}],
    "attribution_per_ref": {"10.1038/...": "opus", "10.1016/...": "codex", ...}
  }
}
```

Markdown render adds a "Cross-review 第二意见" section under Step F, with the `Ref | Status | Verified via | Attribution` table (Section 4.4.3 example).

## Agent tool invocation template

For each reviewer in Round 1 / Round 2, the mentor session calls the `Agent` tool with:

```
subagent_type: <see table>
prompt: """
You are an independent reviewer for thermal-mentor v0.1.3 mode 0 output.

CONTEXT
- skill spec ref: docs/superpowers/specs/2026-05-25-thermal-mentor-v0.1.3-mode-routing-design.md
- mentor payload JSON: <paste from tmp/payload.json>
- data brief: <paste from tmp/data_brief.json>
- prior reviewer critiques (Round 2 only): <paste merged Round 1 bundle>

YOUR JOB
- Independent critique of the mentor's data-first reasoning.
- Focus on: anomaly classification correctness, hypothesis enumeration completeness,
  discriminating experiment feasibility, confirmation bias risk.
- Any DOI / citekey you introduce will be verified via Crossref / OpenAlex / DOI.org HEAD;
  do not fabricate citations. If unsure, omit the ref and keep the argument.

OUTPUT (write to <tmp/cross_review_round{N}_{reviewer}.json>)
{
  "reviewer": "<your label>",
  "round": <N>,
  "findings": [{"text": "...", "severity": "critical|major|minor", "evidence": "..."}],
  "introduced_refs": [{"value": "doi or citekey", "context": "what finding it supports"}],
  "endorse": [<other reviewer's finding text>],
  "refute": [<other reviewer's finding text + counter>]
}
"""
```

For `codex:rescue` calls, Codex CLI is invoked through the codex plugin — see `codex:codex-cli-runtime` skill for required env vars.

For DeepSeek (`deepseek-code-reviewer`), the `DEEPSEEK_API_KEY` env var must be set in the parent session (see `deepseek-v4-reviewer` skill).

## 三方对称 DOI attribution rules

Per spec Section 4.4.3 (merge cross-review #1 / Opus F4 + DS D3):

1. **Every** reviewer-introduced DOI gets a `Attribution` column entry in the Markdown table, regardless of which reviewer introduced it.
2. The DS historical fabrication signal (audit 2026-05-25 measured ~75%) lives in the project-level `CROSS_MODEL_REVIEW_SOP.md`, not in runtime Markdown. Reason: re-litigating the DS reliability inside each user report would visually depress DS architectural critiques (which audit found genuinely useful at the high level).
3. **All** reviewer DOIs go through identical multi-source verification. No special chain for any reviewer.
4. If a DOI fails verification: ref is deleted, finding text is preserved, `cross_review.deleted_refs` records `(value, reason, introduced_by)`. The user sees `attribution = "<reviewer> 引入 → 自动剔除, 论点保留"` in the Markdown.

This is the **anti-discrimination** rule: DS is allowed to make architecture-level claims (where it is genuinely strong) without those claims being pre-rejected by reliability framing.

## 召唤 keyword trigger table

The final Markdown of *every* mode (mode 0 / publication-strategy / both) ends with the always-available footer:

```
---
💬 觉得这次判断不靠谱? 回复 "叫 codex 审" / "叫 opus 审" / "叫 ds 审"
   我会重启刚才的判断, 用第二意见挑刺。
```

When the user replies with one of these keywords, the skill:

1. Reads `tmp/payload.json` (the last rendered payload — NOT re-running Step A-F).
2. Reads `tmp/data_brief.json` if mode 0.
3. Spawns the requested reviewer via Agent tool with the same Round 1 prompt template.
4. Runs Round 2 → 3 → 4 (single-reviewer call is degenerate but consistent).
5. Updates `tmp/payload.json` with the new `cross_review` block.
6. Re-renders the Markdown.

| User keyword (case-insensitive, fuzzy) | Reviewer spawned | subagent_type |
|---|---|---|
| "叫 codex 审" / "codex 来审" / "codex review" | Codex GPT-5 xhigh | `codex:codex-rescue` (or `codex:rescue`) |
| "叫 opus 审" / "opus subagent" / "再 opus 审一次" | Opus 4.7 subagent | `general-purpose` (model=opus) |
| "叫 ds 审" / "deepseek 审" / "v4 来审" | DeepSeek V4 Pro | `deepseek-code-reviewer` |
| "叫全员审" / "三方审" / "roundtable" | all three | three parallel Agent calls |
| 其他不明确 keyword | mentor 用 `AskUserQuestion` 让用户挑 | — |

Keyword matching is fuzzy; mentor falls back to AskUserQuestion only if the reply is ambiguous (e.g. "再审一次" without naming a reviewer).

## Latency expectations

- Codex GPT-5 xhigh: 30-90 min, occasional stdout deadlock (codex:rescue has retry logic).
- Opus subagent: 5-30 min depending on payload size.
- DS V4 Pro: 5-15 min via API.

Default is **不用** (skip Round 1-4 entirely) — Section 4.6. The skill should not auto-trigger cross-review.

## Distinction from open-spec cross-review (Appendix A)

The same Round 1-4 protocol is used for *development-time* cross-review of the spec / plan / code. That is a one-shot exercise per release (Appendix A). The runtime cross-review documented here is **user-selectable per skill invocation**.
