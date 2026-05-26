# thermal-mentor

[![Tests](https://img.shields.io/github/actions/workflow/status/dalek12310/thermal-mentor/test.yml?label=tests&logo=github)](https://github.com/dalek12310/thermal-mentor/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-skill-7c3aed.svg)](https://docs.claude.com/en/docs/claude-code/skills)
[![v0.1.3](https://img.shields.io/badge/version-0.1.3-brightgreen.svg)](CHANGELOG.md)

> A Claude Code skill for **data-first mentor sessions** on scientific manuscripts.
> Built for researchers doing materials science, physics, chemistry, and engineering.

[简体中文文档 / Chinese version](README_zh-CN.md) · [Full Manual](docs/MANUAL.md) · [完整手册](docs/MANUAL_zh-CN.md)

---

## What it does

When you invoke `/thermal-mentor` in Claude Code, the skill runs a **three-step reflective routing protocol** on your data:

1. **Step 0** — Scans your current working directory for manuscripts (`.docx/.pdf/.md/.txt`) and structured data (`.csv/.xlsx`), then builds a `data_brief.json` scaffold. The mentor session (you, the LLM) enriches it with anomaly extraction.

2. **Step 0.5** — Shows a 1-screen reading to the user: detected files, key claims (with source citations), and candidate anomalies (with verbatim quotes). User can interrupt and correct.

3. **Step 1** — Inner monologue infers user intent (case A/B/C/D), then presents 2-4 tailored options via `AskUserQuestion`. Each option includes a verbatim quote + mentor inference pair.

Then it dispatches to one of two pipelines:

- **Mode 0 (data-first)** — anomaly enumeration -> hypothesis enumeration -> discriminating experiment proposal -> optional cross-review -> verifier -> audit log
- **Publication-strategy mode** — original v0.1 workflow for novelty review / highlight / revision / direction / corpus query

Or **both** — mode 0 first, then publication strategy as a handover.

## Key Features

### Multi-source DOI verification

Multi-source DOI verification chain: 4 always-on sources (OpenAlex, Crossref, Semantic Scholar, DOI.org HEAD) + 2 env-gated sources (Lens.org via `LENS_API_TOKEN`, Web of Science via `WOS_API_KEY`). Authoritative `not_found` semantic (Crossref + DOI.org HEAD = ground truth). 24h disk cache. Network failures explicitly returned as `verifier_error` (not silently mapped to `verified`).

### Anomaly-driven mentor reasoning

Mode 0 actively looks for **textbook surprises** in the data — places where the user's measurements contradict standard predictions. Each anomaly gets the 6-field schema (`observation`, `expected_textbook`, `surprise_score`, `data_evidence`, `mentor_inference`, `context_questions_to_user`).

### Round-table cross-review

Independent reviewers (Opus / Codex / DeepSeek) critique the mentor output in parallel (Round 1), see each other's findings (Round 2), then Python merges with non-discriminatory DOI attribution (Round 3-4). No reviewer-discrimination in citation provenance.

> Non-discriminatory means no reviewer is singled out as "high risk" by default; technically the merge uses first-wins ordering when the same DOI is introduced by multiple reviewers.

### paper-pdf-acquisition handoff

When mentor needs paper full-text it can't access, it generates a CSV manifest (`doi, citekey, why_needed, expected_section, resume_token`) for the user to run `/paper-pdf-acquisition` in a separate session.

### Reproducibility lock

`data_brief_hash` is computed over scanner-determined invariants only (file SHA256s, CSV summaries, text content). LLM-enriched fields are excluded so multiple runs against the same cwd produce the same hash. The `run_acceptance.py` script supports `--repeat N` for N-trial stability testing.

### Plain-language hard rule (人话)

User-facing language (Markdown rendering, `AskUserQuestion` options) is plain Chinese/English — no internal codenames (`mode_0`, `L1/L3`, `anomaly_brief`). Technical terms (DFT, XAFS, XPS, phonon) are preserved.

## Installation

### As a Claude Code skill (recommended)

```bash
git clone https://github.com/dalek12310/thermal-mentor.git ~/.claude/skills/thermal-mentor
# Restart Claude Code; the skill auto-activates on /thermal-mentor invocations
```

### As a standalone Python library

```bash
git clone https://github.com/dalek12310/thermal-mentor.git
cd thermal-mentor
pip install -e .

# Run unit tests (no live network, no corpus needed — should pass)
pytest tests/ -v
```

Requires Python >= 3.10.

## Configuration

Set these environment variables for full functionality (all optional):

| Variable | Purpose | Default behavior if unset |
|---|---|---|
| `OPENALEX_MAILTO` | Your email for OpenAlex/Crossref polite pool | Anonymous pool (rate-limited, slower) |
| `THERMAL_MENTOR_CORPUS` | Directory containing `distillation_corpus_v2.csv` + `retraction_blacklist.yaml` | Publication-mode local citekey checks return `not_found`; mode 0 unaffected |
| `LENS_API_TOKEN` | Lens.org Scholarly API token | Lens source omitted from L3 fan-out |
| `WOS_API_KEY` | Web of Science Starter API key | WoS source omitted |
| `CLAUDE_MODEL_ID`, `CLAUDE_MODEL_VERSION` | Recorded in reproducibility block of acceptance runs | `"unknown"` recorded |

Set them in your shell profile (`.bashrc`/`.zshrc`) or via a `.env` file at the repo root (`.env` is gitignored).

## Quick Start

### 1. As a Claude Code skill

Just invoke `/thermal-mentor` in any Claude Code session. The skill scans your CWD and routes you.

### 2. As CLI tools

```bash
# Step 1: scan your data dir into a scaffold
python scripts/anomaly_brief.py path/to/your/data/dir --out tmp/data_brief.json --include-text

# Step 2: hand-edit tmp/data_brief.json (or let the skill session enrich it via Claude)
#   - fill in central_claims, candidate_anomalies, materials_system, manuscript_stage

# Step 3: run the verifier on your mode 0 payload
python scripts/verifier.py tmp/payload.json

# Step 4: persist the acceptance run with reproducibility manifest
python scripts/run_acceptance.py tmp/payload.json \
    --run-name "myproject_v1_data_first_run1" \
    --reproducibility-manifest tmp/data_brief.json \
    --repeat 3   # N=3 repeats for stability testing

# Cross-review merge (after collecting reviewer JSON files)
python scripts/cross_review_merge.py \
    tmp/round1_opus.json tmp/round1_codex.json tmp/round1_ds.json \
    --out tmp/cross_review_final.json
```

## Architecture

```
thermal-mentor/
|-- SKILL.md                 # Claude Code skill entry point
|-- README.md                # This file
|-- README_zh-CN.md          # Chinese version
|-- LICENSE                  # MIT
|-- pyproject.toml           # Python package config
|-- scripts/                 # 11 Python modules
|   |-- anomaly_brief.py     # Step 0 scanner + data_brief scaffold + summarize_csv
|   |-- audit_log.py         # JSONL append-only audit trail
|   |-- cross_review_merge.py  # Round 3-4: classify findings + non-discriminatory DOI attribution + Markdown render
|   |-- doi_verify_multisource.py  # 4 always-on + 2 env-gated verification chain + 24h cache
|   |-- eval_runner.py       # Mode 0 metrics (anomaly_recall, hypothesis_completeness, ...)
|   |-- live_search.py       # L3 fan-out: OpenAlex/S2/arXiv + optional Lens/WoS
|   |-- manuscript_brief.py  # Document text extraction (.docx/.pdf/.md/.txt)
|   |-- paper_pdf_handoff.py # Manifest CSV + resume instruction
|   |-- run_acceptance.py    # Persist run JSON+MD + reproducibility block + N-repeat
|   `-- verifier.py          # Mode dispatch + verify_mode_0 + verify_payload (publication)
|-- references/              # 7 design docs
|   |-- ask-first-prompts.md
|   |-- data-first-prompts.md
|   |-- output-schemas.md
|   |-- output-schemas-data-first.md
|   |-- user-facing-language.md
|   |-- cross-review-protocol.md
|   `-- pdf-acquisition-handoff.md
|-- docs/
|   |-- MANUAL.md            # Full English user manual
|   `-- MANUAL_zh-CN.md      # Full Chinese user manual
`-- tests/                   # 64 unit tests, no external dependencies
    |-- conftest.py
    |-- fixtures/sample_dataset/
    `-- test_*.py
```

See [`docs/MANUAL.md`](docs/MANUAL.md) for the full English manual or [`docs/MANUAL_zh-CN.md`](docs/MANUAL_zh-CN.md) for the Chinese manual.

## Testing

```bash
pytest tests/ -v
# Expected: 64 passed
```

No live network or corpus needed — all tests use mocked `httpx` clients and the generic `sample_dataset` fixture.

## Roadmap (v0.1.4+)

- Add `pipeline_version` field to `audit_log` records
- DataCite / mEDRA DOI source extensions
- Reproducibility block: include Python version + dependency hashes + random seed
- SKILL.md mirror drift pre-commit hook
- Defensive invariants for `verifier_error_metadata` propagation

## Citation

If this tool helps your research workflow, please cite:

```bibtex
@software{thermal_mentor_2026,
  author = {thermal-mentor contributors},
  title = {thermal-mentor: Reflective routing + data-first mode for scientific manuscript mentor sessions},
  year = {2026},
  version = {0.1.3},
  url = {https://github.com/dalek12310/thermal-mentor}
}
```

## Contributing

Issues and PRs welcome. Please read the design docs in `references/` first.

## License

MIT — see [LICENSE](LICENSE).
