# science-mentor — User Manual

> Full user guide for science-mentor v0.2.0.
> For a quick overview, see [README.md](../README.md). Chinese version: [MANUAL_zh-CN.md](MANUAL_zh-CN.md).

## Table of Contents

1. [Conceptual Overview](#1-conceptual-overview)
2. [Installation and Setup](#2-installation-and-setup)
3. [Configuration: Environment Variables](#3-configuration-environment-variables)
4. [Using as a Claude Code Skill](#4-using-as-a-claude-code-skill)
5. [Using as CLI Tools](#5-using-as-cli-tools)
6. [Mode 0 Workflow (Data-First)](#6-mode-0-workflow-data-first)
7. [Publication-Strategy Workflow](#7-publication-strategy-workflow)
8. [Cross-Review Round-Table Protocol](#8-cross-review-round-table-protocol)
9. [DOI Multi-Source Verification](#9-doi-multi-source-verification)
10. [paper-pdf-acquisition Handoff](#10-paper-pdf-acquisition-handoff)
11. [Reproducibility and Acceptance Runs](#11-reproducibility-and-acceptance-runs)
12. [Output Schemas](#12-output-schemas)
13. [Troubleshooting](#13-troubleshooting)
14. [Extending the Tool](#14-extending-the-tool)

---

## 1. Conceptual Overview

`science-mentor` is a **research mentor in a box**. It is designed for one specific moment:

- You have raw experimental data and a draft manuscript.
- You are uncertain whether your data tells a Nature-Materials-level story or just a routine paper.
- You want a second opinion that engages with *your* data, not generic templates.

Most LLM "research assistants" exhibit one of two failure modes:

- **Generic encouragement** ("This looks like a great paper!") — useless.
- **Generic critique** ("Cite more papers, tighten the discussion") — also useless.

`science-mentor` tries to do something different: **start from your data**, find the places where your measurements contradict textbook predictions, and reason forward from there.

### 1.1 The reflective routing pattern

Most skills jump straight to "what do you want me to do?" — but the user's stated question often misses the most surprising thing in their data. `science-mentor` first scans the data, builds inferred-intent options based on what it sees, *then* asks — giving you the chance to either confirm or redirect.

This is documented in `references/data-first-prompts.md` (the Step 1 inner-monologue rubric).

### 1.2 Two-mode architecture

```
                    +------------------+
                    |  /science-mentor |
                    +--------+---------+
                             |
                +------------+------------+
                | Step 0/0.5/1 reflective |
                |      routing protocol   |
                +------------+------------+
                             |
              +--------------+--------------+
              |              |              |
        +-----v-----+ +------v------+ +----v-----+
        |  Mode 0   | |    Both     | |Publication|
        |data-first | |  (handover) | | -strategy |
        +-----------+ +-------------+ +----------+
```

- **Mode 0 (data-first)**: anomaly enumeration -> hypothesis enumeration -> discriminating experiments. The mode-0 kernel carries no domain logic (physics/materials-first today, mechanism-general — other fields need a domain pack).
- **Publication-strategy**: novelty review / highlight / revision / direction / corpus query. Original v0.1 pipeline.
- **Both**: mode 0 first, then publication strategy reads `mode_0_handover` from the mode 0 payload and pre-fills its Level-2 ask.

### 1.3 Five hard rules

The skill enforces five rules at every invocation (documented in `SKILL.md`):

1. **NEVER skip the three-level ask gate.** Even if the user's request looks unambiguous, run Step 0/0.5/1 first.
2. **NEVER fabricate citations.** Every `supporting_refs` entry must be a verifiable citekey, DOI, arXiv ID, or manuscript-chunk reference. The verifier catches violations.
3. **Honest evaluation.** Never inflate novelty to encourage the user. If the corpus shows X is published, say so.
4. **First-principles reasoning, Chinese output.** Respond in Chinese (technical terms in English are OK). Justify with mechanism, not "literature says".
5. **Plain language for user-facing surfaces.** No internal codenames (`mode 0`, `L1/L3`, `anomaly_brief`, `supporting_refs`) leak into AskUserQuestion options or rendered Markdown.

### 1.4 Where the design decisions live

| File | What it documents |
|---|---|
| `SKILL.md` | Orchestration, hard rules, Step 0/0.5/1, Mode 0 pipeline Step A-I, publication pipeline Step A-H |
| `references/ask-first-prompts.md` | Level 1/2/3 question banks |
| `references/data-first-prompts.md` | Step 1 inner-monologue rubric (case A/B/C/D) |
| `references/output-schemas.md` | Publication-mode JSON schemas |
| `references/output-schemas-data-first.md` | Mode 0 JSON schemas (`data_brief.json`, anomaly 6-field, hypothesis, experiment, handover) |
| `references/cross-review-protocol.md` | Round 1-4 round-table, 召唤 keywords, attribution table |
| `references/pdf-acquisition-handoff.md` | T1/T2/T3 triggers, manifest CSV, resume instruction |
| `references/user-facing-language.md` | 人话 hard rule (codename -> plain-language translation table) |

---

## 2. Installation and Setup

### 2.1 As a Claude Code skill

The skill is designed to be cloned directly into the Claude skills directory:

```bash
# Linux / macOS
git clone https://github.com/dalek12310/science-mentor.git ~/.claude/skills/science-mentor

# Windows (PowerShell)
git clone https://github.com/dalek12310/science-mentor.git $env:USERPROFILE\.claude\skills\science-mentor
```

Restart Claude Code; the skill picks up on `/science-mentor` invocations.

To verify install:

```bash
ls ~/.claude/skills/science-mentor/SKILL.md  # should exist
```

### 2.2 As Python scripts / CLI tools

For CLI usage or testing from the checkout, install editable:

```bash
git clone https://github.com/dalek12310/science-mentor.git
cd science-mentor
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

Dependencies (declared in `pyproject.toml`): `httpx`, `python-docx`, `pdfplumber`, `pyyaml`, `pytest` (test extras).

Requires Python >= 3.10. Tested on 3.10 / 3.11 / 3.12 / 3.13.

### 2.3 Verifying the install

```bash
pytest tests/ -v
```

Expected: `77 passed in <time>`.

If tests fail:

- Check Python version (`python --version`).
- Check `pip install -e .` succeeded without warnings.
- Make sure no environment variables leaked from another project; in particular, `unset SCIENCE_MENTOR_CORPUS` if it points to a nonexistent directory.
- Make sure `tests/` and `scripts/` are both on `sys.path`. The `conftest.py` handles this for pytest, but ad-hoc Python invocations should add `scripts/` explicitly.

---

## 3. Configuration: Environment Variables

All variables are optional; the tool degrades gracefully when they are not set.

### 3.1 `OPENALEX_MAILTO`

OpenAlex and Crossref offer a "polite pool" with higher rate limits if you identify yourself via a `mailto` parameter or User-Agent. Set this to your email:

```bash
export OPENALEX_MAILTO="you@example.com"
```

Without it, requests use the anonymous pool: slower, more 429s, occasional cold-start delay. The skill still works but DOI verification can take several seconds longer per ref.

### 3.2 `SCIENCE_MENTOR_CORPUS`

Path to a directory containing a local citation corpus. The corpus directory is expected to have at least:

- `distillation_corpus_v2.csv` — bibliographic CSV with at least `citekey` and `doi` columns.
- `retraction_blacklist.yaml` — list of retracted citekeys/DOIs the verifier refuses to verify.

```bash
export SCIENCE_MENTOR_CORPUS="/path/to/your/local/corpus"
```

Unset: publication-mode local citekey lookups return `not_found`; the verifier falls back to DOI multi-source. Mode 0 does not use the corpus (it is data-driven, not citation-driven), so it is unaffected.

### 3.3 `LENS_API_TOKEN`

Lens.org Scholarly API token. With it set, the multi-source DOI verification chain includes Lens as a secondary metadata source.

```bash
export LENS_API_TOKEN="your_token_here"
```

Unset: Lens is skipped silently in `_build_chain` (see `scripts/doi_verify_multisource.py:151`).

### 3.4 `WOS_API_KEY`

Web of Science Starter API key. Inserted into the verification chain at position 2 (after Crossref, before Semantic Scholar) when present.

### 3.5 `CLAUDE_MODEL_ID`, `CLAUDE_MODEL_VERSION`, `CLAUDE_TEMPERATURE`

Used by `run_acceptance.save_run` to populate the `reproducibility` block on persisted payloads (see Section 11). Defaults to `"unknown"` when not set.

### 3.6 `.env` file convention

The repo's `.gitignore` excludes `.env`. You can put a development `.env` at the repo root:

```bash
# .env
OPENALEX_MAILTO=you@example.com
LENS_API_TOKEN=lens_xxxxx
WOS_API_KEY=wos_xxxxx
```

and source it (`set -a; . ./.env; set +a` in bash, `Get-Content .env | ForEach-Object { ... }` in PowerShell) before running CLI tools. The skill does not auto-load `.env` — set vars in your parent shell so Claude Code inherits them.

---

## 4. Using as a Claude Code Skill

### 4.1 Invocation

In any Claude Code session, type:

```
/science-mentor
```

The skill activates, then immediately runs Step 0 (deterministic scan of your current working directory).

If the CWD has zero supported files, the skill falls back to a Level-3 input source `AskUserQuestion`:

- `folder` — project folder path (mentor will scan)
- `question + text` — you describe the data inline
- `manuscript` — path to a single manuscript file
- `from-corpus` — existing citekey in your local corpus
- `review-pdf` — external PDF file path

### 4.2 Step-by-step walkthrough

A typical session looks like this:

```
You: /science-mentor

Mentor: [silent scan happens]
        基于以上数据, 你想让我做什么?
        
        Option 1: 深挖你 X-ray 数据里的奇怪现象
                  【数据原文】(notes.txt:7) "XPS+EPR 0/2/4/6% signal decreases monotonically"
                  【mentor 解读】掺杂应该 net-increase defects, 但这里反而降, 像是 self-compensation 没解释完
                  -> 深挖数据 (推荐, 这是你数据里最反直觉的点)
                  trade-off: 可能没时间评估投稿方向
        
        Option 2: 评估这篇论文能投哪
                  【数据原文】(draft.docx:p1) "We report a novel synthesis route..."
                  【mentor 解读】方法 novelty 是卖点, 但需要先 anchor 一下机制
                  -> 评估投稿策略
                  trade-off: 不会深挖数据 anomaly
        
        Option 3: 先深挖数据, 再评估投稿
                  -> 两条 pipeline 串起来
                  trade-off: 时间最长
        
        Option 4: 其他

You: [pick Option 1 or Option 3]
```

### 4.3 What the skill does not do

- Does **not** run pip / install dependencies during a session.
- Does **not** modify your manuscript files.
- Does **not** upload your data to any server (DOI verification only sends DOI strings, not your data).
- Does **not** fabricate DOIs to fill `supporting_refs`. If mentor cannot ground a citation, it omits it.

### 4.4 Interrupting the mentor

If Step 0.5 surfaces a claim or anomaly that you disagree with, you can interrupt naturally:

```
You: 等等, 这个 trend 是上升不是下降, 你看错了
Mentor: [re-reads the quote_verbatim from data_brief.json, re-renders the reading]
```

The skill counts interrupts (max 5 per session by design). If you interrupt more than 5 times, the skill suggests restarting because the data brief is clearly off.

### 4.5 The 召唤 (summons) keyword footer

Every final Markdown ends with:

```
---
💬 觉得这次判断不靠谱? 回复 "叫 codex 审" / "叫 opus 审" / "叫 ds 审"
   我会重启刚才的判断, 用第二意见挑刺。
```

If you reply with one of those keywords, the skill reads `tmp/payload.json` and re-enters Step F.5 cross-review — it does NOT re-run Step A-F. This is the "lazy second-opinion" channel.

Keyword matching is fuzzy. Variations like "叫 codex 来审", "codex review", "再 opus 审一次" all work. Ambiguous replies trigger an `AskUserQuestion` to pick a reviewer.

---

## 5. Using as CLI Tools

All ten scripts in `scripts/` are usable from the command line. Below is the full reference; help for each script is also available via `--help`.

### 5.1 `scripts/anomaly_brief.py`

Scan a directory and emit a `data_brief.json` scaffold.

```bash
python scripts/anomaly_brief.py /path/to/data --out tmp/data_brief.json --include-text
```

- `cwd` (positional) — directory to scan recursively.
- `--out` — output JSON path. Default `tmp/data_brief.json`.
- `--include-text` — include extracted text from `.docx`/`.pdf`/`.md`/`.txt` files (the CLI scaffold path; the full anomaly extraction happens in the mentor session).

The CLI mode writes a *scaffold* — fields like `central_claims`, `candidate_anomalies`, `study_system`, `manuscript_stage` are left empty for the mentor (LLM) to fill. The `data_brief_hash` is computed over the scanner-determined invariants only, so the scaffold and the mentor-enriched brief share the same hash for the same input snapshot.

### 5.2 `scripts/verifier.py`

Run DOI / citekey verification on a payload JSON.

```bash
python scripts/verifier.py tmp/payload.json
```

Dispatches on `payload["mode"]`:

- `data_first` -> `verify_mode_0`: checks `data_evidence` source file existence + DOI multi-source for each hypothesis ref.
- `novelty_review` / `highlight_mining` / `revision` / `direction_guidance` / `corpus_query` -> `verify_payload`: full publication-mode verifier including local citekey lookups, retraction blacklist, anchor registry cross-checks.

By default outputs the **rendered Markdown** to stdout (what the user sees). To get the
**verified payload JSON** instead (e.g. to feed `run_acceptance.py`), add `--json`:

```bash
python scripts/verifier.py tmp/payload.json --json > tmp/payload.verified.json
```

(`run_acceptance.save_run` also re-verifies internally before persisting, so the saved
JSON/Markdown always reflect verification even if you skip this step.)

The Markdown rendering (`verifier.render_markdown` / `verifier.render_markdown_mode_0`) is exposed as Python API but is also invoked by `run_acceptance.save_run`.

### 5.3 `scripts/run_acceptance.py`

Persist a verified payload as both JSON and Markdown, append an audit-log record, optionally repeat N times for stability testing.

```bash
python scripts/run_acceptance.py tmp/payload.json \
    --run-name "myproject_v0.1.3_data_first_20260525" \
    --reproducibility-manifest tmp/data_brief.json \
    --repeat 3
```

- `payload_json` (positional) — path to the verified payload.
- `--run-name` (required) — unique run name; convention `<task>_<release>_<mode>_<date>`.
- `--reproducibility-manifest` (optional) — path to `data_brief.json`; `data_brief_hash` is read from there.
- `--repeat N` (default 1) — write N separate runs, each suffixed `_run<i>` in the run_name.

For N=1, output filename is `<run_name>_<YYYYMMDD>.json` / `.md`. For N>1, output filename is `<run_name>_run<i>_<YYYYMMDD>.json` / `.md`.

`save_run` injects a `reproducibility` block into the saved payload BEFORE writing JSON:

```json
{
  "reproducibility": {
    "model_id": "<from $CLAUDE_MODEL_ID>",
    "model_version": "<from $CLAUDE_MODEL_VERSION>",
    "sampler_temperature": "<from $CLAUDE_TEMPERATURE>",
    "data_brief_hash": "<from --reproducibility-manifest>",
    "system_prompt_hash": "<sha256(SKILL.md)[:16]>",
    "pipeline_version": "0.2.0",
    "run_name": "<--run-name>"
  }
}
```

### 5.4 `scripts/cross_review_merge.py`

Merge cross-review reviewer JSON files into a single classified finding bundle with non-discriminatory DOI attribution.

```bash
python scripts/cross_review_merge.py \
    tmp/round1_opus.json tmp/round1_codex.json tmp/round1_ds.json \
    --out tmp/cross_review_final.json
```

Inputs: any number of reviewer JSON files (Round 1 or Round 2 format).
Output: merged JSON with:

- `round_table_summary` — list of findings classified by confidence (`high`/`medium`/`low`).
- `deleted_refs` — refs deleted because of failed DOI verification.
- `attribution_per_ref` — which reviewer introduced each ref.
- `reviewers_used` — list of reviewer labels.

The merged JSON can be folded back into a `payload.json` as the `cross_review` field.

### 5.5 `scripts/live_search.py`

Multi-source live academic search.

```bash
python scripts/live_search.py "<query>" --since 2018-01-01 --top-k 10
```

Sources: OpenAlex, Semantic Scholar, arXiv (always); Lens.org and Web of Science added when their API tokens are set. Returns deduplicated top-K results sorted by recency / relevance.

### 5.6 `scripts/paper_pdf_handoff.py`

Programmatic API (no CLI). Generate a manifest CSV and a resume instruction Markdown block:

```python
from scripts.paper_pdf_handoff import write_manifest, render_resume_instruction

rows = [
    {
        "doi": "10.1038/s41563-024-xxxx",
        "citekey": "Author2024Title",
        "why_needed": "Verify hypothesis H1a against original Method section",
        "expected_section": "methods",
        "resume_token": "20260525-103200-xyz789",
    },
]
write_manifest("tmp/pdf_handoff_20260525-103200-xyz789.csv", rows)

instruction = render_resume_instruction(
    "tmp/pdf_handoff_20260525-103200-xyz789.csv",
    "20260525-103200-xyz789",
    [r["doi"] for r in rows],
)
print(instruction)  # paste into Markdown end
```

Max 5 rows per manifest (`MAX_DOI_PER_MANIFEST = 5`); the function raises `ValueError` otherwise.

### 5.7 Other scripts

- `manuscript_brief.py` — text extraction from `.docx`/`.pdf`/`.md`/`.txt`. Used by `anomaly_brief.py` for the `--include-text` path.
- `doi_verify_multisource.py` — exposes `verify_doi_multisource(doi)` for ad-hoc verification.
- `audit_log.py` — exposes `audit_log.append(record)` for appending to the monthly JSONL log.
- `eval_runner.py` — four pure helper functions for mode 0 metrics (`compute_anomaly_recall_rate`, `compute_hypothesis_completeness`, `compute_existing_data_answerable_rate`, `compute_false_anomaly_rate`).

---

## 6. Mode 0 Workflow (Data-First)

Mode 0 is the data-first pipeline that runs after the user picks an option mapped to `data-first` or `both` in Step 1. It has 9 sub-steps (A through I).

### 6.1 Step A — data_brief.json already produced

Mentor reads `tmp/data_brief.json` produced in Step 0. Does not re-scan or regenerate.

### 6.2 Step B — anomaly enumeration

Promotes `candidate_anomalies` from `data_brief.json` to the formal 6-field schema:

```json
{
  "anomaly_id": "A1",
  "observation": "Across 0/2/4/6 mol% dopant series, the defect signal (XPS O1s + EPR) decreases monotonically",
  "expected_from_prior_knowledge": "Aliovalent substitution textbook: trivalent dopant on tetravalent site should net-increase defects to maintain charge balance",
  "surprise_score": "high",
  "data_evidence": [
    {
      "source": "notes.txt:7",
      "quote_text": "XPS+EPR 0/2/4/6% defect signal decreases monotonically",
      "line_or_para": "p2"
    }
  ],
  "context_questions_to_user": [
    "Did you measure 3+ vs 4+ speciation via XPS?",
    "What was the oxygen partial pressure during sintering?",
    "Do you have EXAFS coordination evidence for the dopant site occupation?"
  ]
}
```

If `idea_critique_subbranch=True` (case B), Step B is skipped — the pipeline jumps to Step E with the user's hypothesis as `hypotheses[0]`.

### 6.3 Step C — user gate 1: literature lookup?

Renders an `AskUserQuestion`:

- `让我凭物理直觉先想机制` — mentor proposes 2-4 mechanisms based on the data only.
- `先帮我查文献再想机制` — run Step D before Step E.
- `两阶段并行` — Step E first (no retrieval), then Step D, then a Step E2 enrichment pass.
- `先停一下让我消化 / 别的`

Notice the option labels: **no "推荐" tag**, only neutral trade-offs. This is a deliberate anti-bias rule.

### 6.4 Step D (optional) — L1 + L3 retrieval

Only runs if Step C user picked "先帮我查文献" or "两阶段并行".

```bash
# L1 (local corpus hybrid retrieve) — only if the corpus bundle script exists
if [ -n "$SCIENCE_MENTOR_CORPUS" ] && [ -f ~/.claude/skills/science-mentor/scripts/hybrid_retrieve.py ]; then
  python ~/.claude/skills/science-mentor/scripts/hybrid_retrieve.py "<anomaly observation>" --top-k 5
fi

# L3 (live academic search)
python ~/.claude/skills/science-mentor/scripts/live_search.py "<anomaly observation>" --since 2018-01-01 --top-k 10
```

Annotates each anomaly with `prior_art_hits`.

### 6.5 Step E — hypothesis enumeration

For each anomaly, propose 2-4 candidate mechanisms:

```json
{
  "hypothesis_id": "H1a",
  "anomaly_id": "A1",
  "mechanism_text": "Dual-site self-compensation: dopant occupies both A and B sublattices",
  "data_support": ["Raman shift at 4 mol% consistent with B-site occupancy (notes.txt:14)"],
  "data_contradict": ["..."],
  "supporting_refs": [...],
  "predicts_observable": [
    "A-site:B-site occupation ratio ~ 1:1 if purely charge-compensated",
    "EXAFS coordination number = mean of (CN_A, CN_B)",
    "Raman should show modes from both A-site and B-site dopant"
  ]
}
```

`predicts_observable` is **critical**. For each mechanism, mentor lists what else should be visible in the data IF the mechanism is true. The user can self-verify by checking their own data — no need to trust mentor.

### 6.6 Step F — discriminating experiment proposal

For each anomaly, 1-2 experiments that can discriminate between candidate mechanisms:

```json
{
  "experiment_id": "E1",
  "anomaly_id": "A1",
  "discriminates_between": ["H1a", "H1b"],
  "experiment_text": "Measure 3+ vs 4+ speciation via XPS at 4 mol% dopant",
  "answerable_by": "existing_data",
  "if_new_experiment": {"effort": "low", "rough_cost": "1 day on existing XPS"},
  "expected_outcome": {
    "H1a_predicts": "All dopant in 4+ state",
    "H1b_predicts": "Shoulder peak from 3+ state appears"
  }
}
```

`answerable_by=existing_data` is **preferred** — actively look for user's existing assets that have not been mined.

### 6.7 Step F.5 — cross-review gate (optional, default OFF)

Renders `AskUserQuestion`:

- `不用` (default; skips Round 1-4 entirely).
- `叫 Codex` / `叫 Opus` / `叫 DS` / `叫全员` / `自己挑`.

If user picks reviewers, mentor uses the `Agent` tool to spawn them in parallel. See Section 8 for full protocol.

### 6.8 Step G — verifier

```bash
python ~/.claude/skills/science-mentor/scripts/verifier.py tmp/payload.json
```

Mode 0 verifier checks:

- Each anomaly's `data_evidence` source file exists at the claimed path.
- Each hypothesis's `supporting_refs` DOI passes multi-source verification (see Section 9).
- Non-discriminatory Markdown rendering via `render_markdown_mode_0`.

### 6.9 Step H — render + audit log + acceptance save

```bash
python ~/.claude/skills/science-mentor/scripts/run_acceptance.py \
    tmp/payload.json --mode data_first \
    --reproducibility-manifest tmp/data_brief.json \
    --run-name "<task>_v0.1.3_data_first_<date>_runN"
```

Persists JSON+MD, appends audit_log record, injects reproducibility block. Always includes the 召唤 footer.

### 6.10 Step I (only if "both" mode) — publication gate

After mode 0 finishes in "both" mode, mentor asks:

- `要不要叠投稿策略评估?`
- Yes -> jump to publication pipeline Level-2 with auto-prefilled options from `mode_0_handover`.
- No -> end.

---

## 7. Publication-Strategy Workflow

The original v0.1 pipeline. Five modes, structurally similar.

### 7.1 Level-1 mode selection

`AskUserQuestion`:

1. `novelty` — evaluate originality; is the result already published?
2. `highlight` — find selling points; pitch a one-line narrative.
3. `revision` — manuscript editing.
4. `direction` — research direction guidance.
5. `corpus_query` — query the local corpus.

### 7.2 Level-2 per-mode clarifier

Mode-specific. For `novelty`:

- Q1: novelty definition — first to propose / first to apply method / first in your material system.
- Q2: failure tolerance — none / 5% / 10%.
- Q3: target journal — Nat Mater / Nat Commun / Adv Mater / JACS-ACS Nano-Nano Lett / other (**placed last** to avoid framing bias on the ceiling estimate).

For other modes, see `references/ask-first-prompts.md`.

### 7.3 Level-3 input source

`AskUserQuestion`:

1. `folder` — project folder path.
2. `question + text` — inline description.
3. `manuscript` — path to manuscript file.
4. `from-corpus` — existing citekey.
5. `review-pdf` — external PDF path.

### 7.4 Pipeline Steps A-H

| Step | Action |
|---|---|
| A | Ingest input -> manuscript brief if applicable (`manuscript_brief.py`) |
| B | Retrieve from local corpus L1 (`hybrid_retrieve.py`, if corpus configured) |
| C | Live external search L3 (`live_search.py`) |
| D | Pull anchor registry context (when corpus is configured) |
| E | Reason and produce JSON per `references/output-schemas.md` |
| F | Verify via `verifier.py` |
| G | Persist run (acceptance + audit log) via `run_acceptance.save_run` |
| H | Present rendered Markdown to user |

---

## 8. Cross-Review Round-Table Protocol

Documented in `references/cross-review-protocol.md`. Below is the operational summary.

### 8.1 When cross-review fires

- User picks reviewers in Step F.5 gate (mode 0 / both).
- User picks reviewers in v0.1 publication gate.
- User replies with a 召唤 keyword after the final Markdown.

Cross-review is **never the default**. Runs 30-90 min and adds latency that most invocations do not need.

### 8.2 Round 1 — parallel independent critique

Mentor uses the `Agent` tool to spawn each selected reviewer in parallel within a single message. Reviewers (Opus 4.7 subagent / Codex GPT-5 xhigh / DeepSeek V4 Pro) each receive the same input (payload JSON + brief context) and return JSON of shape:

```json
{
  "reviewer": "opus|codex|ds",
  "findings": [
    {"text": "...", "severity": "critical|major|minor", "evidence": "...",
     "introduced_refs": [{"value": "doi/citekey", ...}]}
  ],
  "introduced_refs": [{"value": "doi or arxiv id", ...}],
  "round": 1
}
```

Saved to `tmp/cross_review_round1_<reviewer>.json`.

### 8.3 Round 2 — cross-update with peer critiques

Mentor merges all Round 1 critiques into a single bundle and sends to each reviewer. Reviewers can:

- **Endorse** another reviewer's finding (raises confidence).
- **Refute** with counter-evidence.
- **Supplement** with additional detail.
- **Pass** if they have no evidence to add either way.

Saved to `tmp/cross_review_round2_<reviewer>.json`.

### 8.4 Round 3 — DOI multi-source verification

All DOIs introduced by any reviewer go through `cross_review_merge.merge_reviews` -> `doi_verify_multisource.verify_doi_multisource`.

- Verified refs: kept; labelled with source attribution.
- Not-found refs: **deleted, but the finding text is preserved** (论点跟引用解耦). Recorded in `cross_review.deleted_refs` for audit transparency.
- Verifier-error refs: kept, marked "校验器报错 (网络问题, 非引用错误)" in the final Markdown.

### 8.5 Round 4 — merge into final payload

`cross_review_merge.classify_findings` groups findings by 30-char prefix similarity and assigns confidence:

- `high` — all reviewers agree.
- `medium` — majority agreement (>= ceil(N/2)+1).
- `low` — singleton.

`cross_review_merge.attribute_refs` assigns **non-discriminatory attribution** for every reviewer-introduced ref. No reviewer is flagged "high risk" in the runtime Markdown. Technically the merge uses first-wins ordering when the same DOI is introduced by multiple reviewers.

### 8.6 The anti-discrimination rule

Per Section 4.4.3 of the design spec:

1. Every reviewer-introduced DOI gets an `Attribution` column entry, regardless of which reviewer introduced it.
2. The DeepSeek historical fabrication signal (~75% measured in audit 2026-05-25) lives in the project-level `CROSS_MODEL_REVIEW_SOP.md`, NOT in runtime Markdown. Reason: re-litigating reviewer reliability inside each user report would visually depress DS architectural critiques, which audit found genuinely useful at the high level.
3. All reviewer DOIs go through identical multi-source verification. No special chain for any reviewer.
4. If a DOI fails verification: ref is deleted, finding text is preserved, `cross_review.deleted_refs` records `(value, reason, introduced_by)`. The user sees `attribution = "<reviewer> 引入 -> 自动剔除, 论点保留"` in the Markdown.

### 8.7 召唤 keyword table

| User keyword (case-insensitive, fuzzy) | Reviewer | subagent_type |
|---|---|---|
| `叫 codex 审` / `codex 来审` / `codex review` | Codex GPT-5 xhigh | `codex:codex-rescue` |
| `叫 opus 审` / `opus subagent` / `再 opus 审一次` | Opus 4.7 subagent | `general-purpose` (model=opus) |
| `叫 ds 审` / `deepseek 审` / `v4 来审` | DeepSeek V4 Pro | `deepseek-code-reviewer` |
| `叫全员审` / `三方审` / `roundtable` | all three | three parallel `Agent` calls |
| ambiguous | mentor falls back to `AskUserQuestion` to disambiguate | — |

---

## 9. DOI Multi-Source Verification

### 9.1 The chain

**4 always-on sources** (OpenAlex, Crossref, Semantic Scholar, DOI.org HEAD) **+ 2 env-gated sources** (Lens.org via `LENS_API_TOKEN`, Web of Science via `WOS_API_KEY`):

```
OpenAlex (qps=10)  -> Crossref (qps=50)              -> Semantic Scholar (qps=1)
                   -> [Lens.org if LENS_API_TOKEN]   -> [WoS if WOS_API_KEY]
                   -> DOI.org HEAD (AUTHORITATIVE for absence)
```

Source order is fixed; `_build_chain` only inserts Lens / WoS conditionally based on env vars.

### 9.2 Semantics

- **Any source `found`**: return `verified` immediately, with that source as the attribution.
- **Non-authoritative source `not_found`**: continue fallback. This includes **Crossref** — a positive Crossref hit proves existence, but a Crossref miss does **not** prove absence, because Crossref does not index DataCite/Zenodo/mEDRA DOIs. So a Crossref miss only continues the chain.
- **DOI.org HEAD `not_found`** (the only authority for *absence* — it resolves every registration agency): confirmed absence; chain terminates with `status=not_found`.
- **Any source `verified`**: return immediately with that source as the attribution.
- **All sources raise HTTPError / TimeoutException**: return `status=verifier_error` with the accumulated error list in `error_detail.all_sources_failed`.

The `verifier_error` status is explicitly distinct from `verified` and `not_found`. It is a **side-channel** that the user-facing Markdown surfaces as "校验器报错 (网络问题, 非引用错误)".

### 9.3 Caching

- 24-hour disk cache at `cache/doi_verify/<hash>.json`.
- `verified` and `not_found` results are cached; `verifier_error` is **not** (it is transient).
- Cache key is sha256(normalized_doi)[:24].
- Cache miss -> full chain run.

### 9.4 DOI normalization

`normalize_doi` strips `https?://(dx\.)?doi\.org/` and `doi:` prefixes (case-insensitive), then lowercases. Used everywhere a DOI enters the chain to prevent cache fragmentation.

### 9.5 LegacyDoiAdapter

The publication-mode `verifier.py` has a `LegacyDoiAdapter` that wraps `verify_doi_multisource` to look like the v0.1 `check_doi` interface. This lets the old Step-F verifier code call the new multi-source chain transparently without business-logic changes.

---

## 10. paper-pdf-acquisition Handoff

### 10.1 Why this is a separate skill

`paper-pdf-acquisition` is an Edge / CARSI / Shibboleth interactive skill — it cannot be called as a Python API. It enforces 5 immutable hard rules:

1. No Sci-Hub.
2. No Cloudflare bypass.
3. Clean Edge profile (CARSI / Shibboleth login).
4. No Zotero SQLite write without explicit user authorization.
5. Validate every PDF (header check).

Rules 2-3 require a Chrome DevTools Protocol session piloting a real Edge profile the user has authenticated. Embedding that into science-mentor would either bypass user authentication (rule violation) or block every invocation on a 30-60s setup ceremony. Decision: lazy invoke on demand, **cross-session manifest handoff**.

### 10.2 T1 / T2 / T3 trigger conditions

| Trigger | Who triggers | Mentor behavior |
|---|---|---|
| **T1 — user explicit request** | User: "我想看这篇 [DOI]" / "深挖 [citekey]" | Mentor invokes `write_manifest` + `render_resume_instruction`, appends to current Markdown |
| **T2 — mentor active recommendation** | Mode 0 Step E identifies a paper as critical for hypothesis validation | Mentor does NOT interrupt the pipeline. Recommendation goes into the **final** Markdown end (after Step H) |
| **T3 — verifier_error fallback** | Multi-source chain returns `verifier_error` for a DOI a reviewer insists on | Markdown adds: "可调 paper-pdf-acquisition 物理验证 DOI 存在性" |

T2 is **non-interrupting** by design. The cost of breaking session flow + asking the user to launch CARSI mid-pipeline outweighs the value of an inline PDF retrieval.

### 10.3 Manifest CSV schema

`paper_pdf_handoff.write_manifest` writes to `tmp/pdf_handoff_<audit_log_id>.csv`:

| Column | Description |
|---|---|
| `doi` | DOI string. Required if no citekey. |
| `citekey` | Local corpus citekey. Required if no DOI. |
| `why_needed` | Plain-text reason: "验证 H1a hypothesis 的关键证据" / "用户 trigger 显式要求深挖" |
| `expected_section` | Which manuscript section mentor will read once full text arrives: `methods` / `results` / `discussion` / `full` |
| `resume_token` | `audit_log_id` of the current mentor run. Used to relink the fulltext when the user returns. |

Max 5 rows per manifest (`MAX_DOI_PER_MANIFEST = 5`). Larger requests split into multiple handoffs. The cap prevents accidental "pull every paper in the L3 results" requests.

### 10.4 Resume instruction template

The Markdown block emitted by `render_resume_instruction`:

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

The "PDF 拿好了, 继续 <audit_log_id>" reply pattern is the **only** way the original session resumes.

### 10.5 Cross-session flow

1. **Mentor session (original)**: writes manifest CSV, appends resume instruction, saves payload state to `tmp/payload.json`.
2. **User new session**: runs `/paper-pdf-acquisition <CSV path>`. paper-pdf-acquisition downloads via OA / CARSI / Shibboleth / arXiv as appropriate.
3. **User returns to mentor session** with `PDF 拿好了, 继续 <audit_log_id>`. Mentor reads `04_fulltext/<citekey>.txt`, re-enters Step E with the new full text appended to reasoning context.

If some DOIs come back `unresolved`, mentor adjusts hypotheses based on partial fulltext + flags the unresolved DOIs in the new Markdown.

---

## 11. Reproducibility and Acceptance Runs

### 11.1 The `data_brief_hash` invariant

`data_brief_hash` is sha256 over the canonical-serialized **hash-payload subset** of `data_brief.json`:

```python
HASH_PAYLOAD_KEYS = ("files_found", "scanner_manifest", "csv_summaries", "text_files_content")
```

LLM-enriched fields (`central_claims`, `performance_numbers`, `candidate_anomalies`, `study_system`, `manuscript_stage`) are **excluded**. They are non-deterministic given the same input, and model-side reproducibility is captured separately via `reproducibility.model_id` / `system_prompt_hash`.

Why this matters: this guarantee allows the CLI scaffold path (`build_data_brief_scaffold`, deterministic) and the mentor session full pipeline (`build_data_brief`, includes LLM enrichment) to produce the same `data_brief_hash` for the same cwd snapshot. Multiple acceptance runs against the same data lock identically.

> **Caveat: this is per-machine reproducibility.** The `scanner_manifest` includes absolute file paths, so running the same dataset on different machines (or under different mount points) produces different hashes. For true cross-machine reproducibility, the underlying scan paths would need to be relativized — planned for v0.2. In practice, the hash is sufficient for "same dataset, same machine, multiple LLM runs" (the v0.1.3 acceptance use case) but should not be claimed as universal.

### 11.2 The `reproducibility` block

`run_acceptance.save_run` injects this into the saved payload:

```json
{
  "reproducibility": {
    "model_id": "<from $CLAUDE_MODEL_ID, default 'unknown'>",
    "model_version": "<from $CLAUDE_MODEL_VERSION, default 'unknown'>",
    "sampler_temperature": "<from $CLAUDE_TEMPERATURE, default 'default'>",
    "data_brief_hash": "<from --reproducibility-manifest>",
    "system_prompt_hash": "<sha256(SKILL.md)[:16]>",
    "pipeline_version": "0.2.0",
    "run_name": "<--run-name>"
  }
}
```

`system_prompt_hash` is computed from `SKILL.md` (either repo-local or installed at `~/.claude/skills/science-mentor/SKILL.md`). Fallback sentinel: `"skill_md_not_found"`.

### 11.3 N=3 stability testing

`--repeat 3` writes three separate acceptance runs from the same payload, each tagged `_run1` / `_run2` / `_run3`. Used for v0.1.3 release validation:

```bash
python scripts/run_acceptance.py tmp/payload.json \
    --run-name "myproject_v0.1.3_data_first_20260525" \
    --reproducibility-manifest tmp/data_brief.json \
    --repeat 3
```

Same JSON payload + same SKILL.md = same `data_brief_hash` + same `system_prompt_hash`. Any divergence in the rendered Markdown across N=3 isolates a non-determinism in the verifier or renderer.

### 11.4 Audit log

`audit_log.py` provides a JSONL append-only log at `audit_log/<YYYY-MM>.jsonl`. Each acceptance run appends a summary record:

```json
{
  "type": "acceptance_run",
  "run_name": "...",
  "audit_log_id": "20260525-103200-xyz789",
  "mode": "data_first",
  "claims_count": 0,
  "json_path": "...",
  "md_path": "...",
  "timestamp": "2026-05-25T10:32:00"
}
```

`audit_log_id` follows the pattern `<YYYYMMDD>-<HHMMSS>-<6-char-alnum>` and is the canonical identifier across the manifest CSV, resume instruction, and downstream lineage.

---

## 12. Output Schemas

Full schemas live in `references/output-schemas.md` (publication modes) and `references/output-schemas-data-first.md` (mode 0). Highlights below.

### 12.1 `data_brief.json`

```json
{
  "files_found": [{"path": "notes.txt", "type": "txt", "tokens": 1240}],
  "central_claims": [
    {"claim_text": "...", "source_file": "notes.txt",
     "quote_line": 12, "quote_verbatim": "..."}
  ],
  "performance_numbers": [...],
  "candidate_anomalies": [
    {"anomaly_id": "A1", "observation_short": "...",
     "observed_trend": "monotonic_decrease|monotonic_increase|non_monotonic|unknown",
     "expectation_basis": "defect-chemistry textbook|Shannon radii|...",
     "quote_verbatim": "...", "quote_source": "notes.txt:7",
     "quote_hash": "sha256:...",
     "expected_from_prior_knowledge_short": "...",
     "mentor_inference": "...",
     "surprise_score": "high|medium|low"}
  ],
  "study_system": "doped oxide series",
  "manuscript_stage": "draft|plan|data-only|mixed",
  "data_brief_hash": "sha256:...",
  "scanner_manifest": {
    "cwd": "...",
    "files_glob_pattern": "**/*.{txt,md,docx,pdf,csv,xlsx}",
    "file_hashes": {"notes.txt": "sha256:..."},
    "scanner_version": "0.1.3",
    "timestamp": "2026-05-25T10:32:00Z"
  },
  "audit_log_id": "..."
}
```

### 12.2 Mode 0 payload

```json
{
  "mode": "data_first",
  "anomalies": [...6-field schema...],
  "hypotheses": [...with predicts_observable...],
  "experiments": [...with discriminates_between + answerable_by...],
  "cross_review": {...if Round 1-4 ran...},
  "mode_0_handover": {...if 'both' mode...},
  "reproducibility": {...},
  "audit_log_id": "..."
}
```

### 12.3 Publication payload

```json
{
  "mode": "novelty_review|highlight_mining|revision|direction_guidance|corpus_query",
  "verdict": {"one_line": "...", "confidence": "low|medium|high"},
  "claims": [
    {"claim_id": "C001", "claim_text": "...",
     "claim_type": "novelty|method|mechanism|performance|citation|limitation",
     "supporting_refs": [
       {"ref_id": "R001", "ref_type": "local_citekey|doi|openalex|user_manuscript",
        "value": "...", "verification_status": "verified|not_found|verifier_error"}
     ],
     "novelty_flag": "novel|not_novel|incremental|uncertain",
     "evidence_span": "exact quote or null",
     "confidence": "low|medium|high"}
  ],
  "prior_art_coverage": {...},
  "what_would_change_my_mind": [...],
  "audit_log_id": "..."
}
```

### 12.4 Mode-0 -> publication handover

When mode 0 finishes in `both` mode, the payload carries a top-level `mode_0_handover` field:

```json
{
  "mode_0_handover": {
    "central_claim_candidates": ["..."],
    "mechanism_claim_candidates": ["..."],
    "selling_point_candidates": ["..."],
    "existing_data_assets": ["..."],
    "study_system": "...",
    "data_brief_hash": "sha256:..."
  }
}
```

Publication mode reads it and pre-fills Level-2 `AskUserQuestion` option descriptions. The user can still revise each candidate — handover only eliminates "system forgot what we just discussed" friction.

---

## 13. Troubleshooting

### 13.1 Tests fail

- `ModuleNotFoundError: doi_verify_multisource` — make sure `scripts/` is on `sys.path` (the `conftest.py` does this for pytest). For ad-hoc Python invocation, `sys.path.insert(0, "scripts")`.
- `httpx.ConnectError` — network down or rate-limited. Set `OPENALEX_MAILTO` for the polite pool.
- `UnicodeDecodeError` on CSV — file is GB18030 or other non-UTF-8. `summarize_csv` tries fallback encodings (UTF-8 -> GB18030 -> Latin-1) automatically.
- `_llm_extract_anomalies NotImplementedError` — you called `build_data_brief` directly. Use `build_data_brief_scaffold` for CLI scenarios; the full path is for the mentor session only.

### 13.2 Skill does not activate on `/science-mentor`

- Check `ls ~/.claude/skills/science-mentor/SKILL.md` exists.
- Restart Claude Code (the skills registry is loaded at session start).
- Check that `SKILL.md` frontmatter has `name: science-mentor` (case-sensitive).

### 13.3 DOI verification stuck on a single DOI

- Check `cache/doi_verify/<hash>.json` for the DOI. If present and `status=verifier_error`, it should not have been cached — file a bug.
- Delete the cache file to force a fresh chain run: `rm cache/doi_verify/*.json`.

### 13.4 `data_brief_hash` differs between CLI scaffold and mentor session

This should not happen by design. If it does:

- Check `HASH_PAYLOAD_KEYS` in `anomaly_brief.py` — should be `("files_found", "scanner_manifest", "csv_summaries", "text_files_content")`.
- Make sure CSV files do not have None-keyed columns (DictReader will produce them when header has empty fields). `_stringify_keys` handles this — verify it runs.

### 13.5 Cross-review reviewer times out

- Codex GPT-5 xhigh: 30-90 min, occasional stdout deadlock; `codex:codex-rescue` has retry logic.
- Opus subagent: 5-30 min depending on payload size.
- DeepSeek V4 Pro: 5-15 min via API; requires `DEEPSEEK_API_KEY` in parent session env.

If a reviewer fails to return, mentor proceeds with the remaining reviewers and notes the omission in the merged JSON.

---

## 14. Extending the Tool

### 14.1 Adding a new DOI verification source

1. Implement a lookup function in `scripts/doi_verify_multisource.py`:

```python
def datacite_lookup(doi: str, timeout: float = DEFAULT_TIMEOUT) -> SourceLookupResult:
    url = f"https://api.datacite.org/dois/{doi}"
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as cli:
        r = cli.get(url)
        if r.status_code == 200:
            data = r.json()
            if data and data.get("data"):
                return SourceLookupResult(True, data["data"])
        return SourceLookupResult(False, None)
```

2. Add it to `_build_chain()`:

```python
Source("datacite", datacite_lookup, False),  # non-authoritative
```

3. Add a unit test in `tests/test_doi_verify_multisource.py` that mocks the httpx Client.

### 14.2 Adding a new mode

1. Define the schema in `references/output-schemas.md` (or a new file).
2. Add a `verify_<mode>` function in `scripts/verifier.py`.
3. Add it to the `MODE_DISPATCH` table at the top of `verifier.py`.
4. Add a `render_markdown_<mode>` function.
5. Update `SKILL.md` Level-1 mode options.
6. Add a unit test in `tests/test_verifier_mode_dispatch.py`.

### 14.3 Adding a new mode 0 metric

1. Add a pure function to `scripts/eval_runner.py`:

```python
def compute_<metric_name>(payload: dict) -> float:
    ...
    return round(value, 3)
```

2. Add a unit test in `tests/test_mode_0_metrics.py`.

### 14.4 Changing the skill name

If you fork this and want to rename:

1. Rename the repo directory.
2. Update `SKILL.md` frontmatter `name: <new-name>` and `description: ...`.
3. Update slash-command references in `references/*.md` and `docs/MANUAL*.md`.
4. Update Python import paths if you renamed `scripts/` -> something else.

### 14.5 Adding a domain pack (using the tool in another field)

The kernel is domain-general; field-specific vocabulary lives in `domains/`. To target a new field:

1. Copy `domains/_template.md` to `domains/<your-field>.md`.
2. Fill the four slots: `research_directions`, `target_journals`, `preserved_terms`,
   `expectation_vocabulary`.
3. At session start, set `MENTOR_DOMAIN_PACK=<your-field>` (or tell the mentor "use the
   `<your-field>` domain pack").

No code changes are needed — a pack is data, not logic. The shipped `domains/thermal.md` is the
reference pack; `domains/_template.md` includes worked biology and economics examples showing the
anomaly → hypothesis → discriminating-experiment loop is field-agnostic. See `domains/README.md`.

---

*Manual last updated for v0.2.0.*
