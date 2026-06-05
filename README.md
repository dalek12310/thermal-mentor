# science-mentor

[![Tests](https://img.shields.io/github/actions/workflow/status/dalek12310/science-mentor/test.yml?label=tests&logo=github)](https://github.com/dalek12310/science-mentor/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-skill-7c3aed.svg)](https://docs.claude.com/en/docs/claude-code/skills)
[![v0.2.0](https://img.shields.io/badge/version-0.2.0-brightgreen.svg)](CHANGELOG.md)

> **A Claude Code mentor that reads your experimental data, finds where your measurements
> contradict the textbook, and turns each surprise into a testable hypothesis + a discriminating
> experiment — with every citation cross-checked against up to 6 sources (4 always-on, +2 with
> API keys), never fabricated.**

It runs a disciplined **scientific-method protocol** with teeth where it counts: **every citation
is code-verified against multiple sources and never fabricated**, while the skill's hard rules
require a verbatim quote behind every claim and a falsifiable prediction behind every mechanism.

*Scope, honestly:* the discovery + verification engine is domain-general (it operates on generic
CSV columns, text, and DOIs). The shipped prompt examples and the optional publication corpus are
**physics / materials-science flavored** — other fields work but benefit from a domain pack.

[简体中文文档 / Chinese version](README_zh-CN.md) · [Full Manual](docs/MANUAL.md) · [完整手册](docs/MANUAL_zh-CN.md)

---

## The problem it solves

You have raw data and a draft. You can't tell whether you're holding a *Nature Materials* story
or a routine paper — and the people who could tell you are busy.

So you ask an LLM, and you get one of two useless answers:

- **Generic encouragement** — *"This looks like a great paper!"*
- **Generic critique** — *"Cite more references and tighten the discussion."*

Neither one actually *looked at your numbers*. `science-mentor` starts from your data: it finds
the places where your measurements disagree with what theory predicts, and reasons forward from
those surprises — the same move a good advisor makes when they lean over your plots.

## What makes it different

- **It reads your data before it talks.** A deterministic scan of your folder runs first
  (trend detection on every column, quotes pulled from your notes) — *then* it asks what you want.
  The most surprising thing in your data drives the conversation, not a template.
- **Every "mechanism" comes with a way to kill it.** For each candidate explanation it lists the
  *other things you should see in your data if it's true*, so you can check it yourself instead of
  trusting the model — then it proposes one experiment that tells competing explanations apart
  (preferring ones you can answer with data you already have).
- **It can't fabricate a citation.** Every reference is checked through OpenAlex → Crossref →
  Semantic Scholar → DOI.org (+ Lens / Web of Science if you have keys). Unverifiable refs are
  dropped, not bluffed — and a network failure is reported as a network failure, never silently
  upgraded to "verified."

## A worked example

Suppose your folder has a 4-row CSV from a doping series:

```csv
sample,dopant_pct,lattice_param_A,conductivity_Scm,activation_eV
S0,0,12.974,1.8e-4,0.42
S2,2,12.961,2.7e-4,0.38
S4,4,12.945,3.5e-4,0.34
S6,6,12.926,4.2e-4,0.31
```

You run the skill. Instead of "looks promising!", you get:

> **Anomaly (high surprise).** The lattice *contracts* with doping, yet conductivity *rises 4×*
> and the activation energy *drops* 0.42 → 0.31 eV.
> *Textbook expectation:* a tighter lattice narrows the ion channel and should **raise** the
> barrier. Evidence: `data.csv`, `activation_eV` column, monotonic decrease.
>
> **Two competing mechanisms** —
> *H1: local-distortion percolation.* If true, you should also see broader PDF peaks at high
> doping and new Raman modes.
> *H2: carrier-concentration jump.* If true, a Hall measurement should show carrier density
> rising ~4×.
>
> **One experiment that separates them:** run Hall on the same 4 samples. Flat carrier density ⇒
> H1; ~4× rise ⇒ H2. *(Answerable with a standard 4-point setup — no new synthesis.)*
>
> **Is this novel?** Two prior reports describe the conductivity rise, but neither pairs it with
> the E_a drop under lattice contraction — *that* pairing is the unclaimed angle. *(Refs:
> `10.xxxx/...` verified, `10.yyyy/...` verified.)*

That is the difference between a chatbot and a mentor: a falsifiable next step, grounded in *your*
rows, with citations you can trust.

## Quick start — as a Claude Code skill (recommended)

```bash
git clone https://github.com/dalek12310/science-mentor.git ~/.claude/skills/science-mentor
# Restart Claude Code, then from a folder that has your data + draft:
```

```
You: /science-mentor
Mentor: [silently scans the folder]
        Based on your data, what do you want me to do?
          1. Dig into the surprising result in your conductivity vs. lattice data  (recommended)
          2. Assess where this manuscript could be submitted
          3. Both — dig first, then strategy
          4. Something else
You: 1
Mentor: [anomaly → hypotheses → discriminating experiment, as above]
```

It scans your current working directory, shows you what it found (with quotes you can correct),
infers your intent, and routes you. You stay in control at every step.

## What you get: two modes

| Mode | What it does for you |
|---|---|
| **Discovery** (data-first) | Turns your raw data into: the anomalies that contradict expectation → competing mechanisms, each with a self-check prediction → one discriminating experiment per anomaly. Best when you have data and want to know *what's really going on*. |
| **Publication strategy** | Honest novelty review, selling-point mining, revision help, and direction suggestions — grounded in your data, not in journal hype. Best when you have a draft and want to know *where it can go*. (Uses an optional local corpus; physics/materials flavored.) |

Or run **both**: discovery first, then strategy picks up where discovery left off.

## How we keep it honest

Some are enforced in Python, some are hard rules the skill must follow at every step — not good intentions:

- **No fabricated citations.** Multi-source DOI verification; unverifiable refs are dropped and
  logged, network errors are surfaced (not hidden) as "verifier error."
- **No flattery.** A hard rule forbids inflating novelty to encourage you; if the literature
  shows your result is already published, it says so.
- **Reproducible runs.** A `data_brief_hash` over the deterministic scan lets you re-run the same
  data and get the same starting point; model/version provenance is recorded separately.
- **Plain language.** User-facing output never leaks internal codenames; technical terms (DFT,
  XAFS, phonon, …) are preserved.

## Advanced: use the Python scripts / CLI

The scan → verify → persist pipeline is also usable headless from the checkout:

```bash
git clone https://github.com/dalek12310/science-mentor.git
cd science-mentor && pip install -e .
pytest tests/ -v          # 77 passed — no network, no corpus needed

# Scan a data dir into a scaffold
python scripts/anomaly_brief.py path/to/data --out tmp/data_brief.json --include-text
# (a mentor session, or you by hand, fills in claims + anomalies)
python scripts/verifier.py tmp/payload.json                      # verify + render
python scripts/run_acceptance.py tmp/payload.json \
    --run-name "myproject_run1" --reproducibility-manifest tmp/data_brief.json --repeat 3
```

See [`docs/DEMO.md`](docs/DEMO.md) for a full end-to-end walkthrough on a sample dataset.

## Installation & configuration

Python ≥ 3.10. All environment variables are **optional** — the tool degrades gracefully without
them (e.g. unset corpus ⇒ local citekey checks return `not_found`, discovery mode unaffected).
Full table in [the manual](docs/MANUAL.md#3-configuration-environment-variables); the common one:

```bash
export OPENALEX_MAILTO="you@example.com"   # faster, friendlier DOI verification
```

## Under the hood

For readers who want the mechanism (you don't need this to use it):

- **Three-step reflective routing** — *Step 0* deterministic scan → *Step 0.5* shows you the
  reading (files, claims, candidate anomalies, with quotes) → *Step 1* infers intent (cases
  A/B/C/D) and offers tailored options, each backed by a verbatim quote + the mentor's inference
  so you can challenge either independently.
- **Mode-0 pipeline** — anomaly enumeration → hypothesis enumeration (with `predicts_observable`)
  → discriminating experiment → optional cross-review → verifier → audit log.
- **Round-table cross-review** — independent reviewers critique in parallel, then see each other's
  findings, then a deterministic merge grades confidence by agreement (consensus / majority /
  singleton) with non-discriminatory citation attribution.
- **paper-pdf-acquisition handoff** — when full text is needed, it emits a manifest CSV to run the
  separate `/paper-pdf-acquisition` skill, rather than blocking the session.

Design docs live in [`references/`](references/); the full protocol is in [`docs/MANUAL.md`](docs/MANUAL.md).

## Project info

```
science-mentor/
├── SKILL.md            # Claude Code skill entry point
├── scripts/            # Python backend (scanner, verifier, DOI chain, cross-review, …)
├── references/         # design docs (routing, schemas, cross-review, plain-language rule)
├── docs/               # MANUAL (EN/zh), DEMO walkthrough, blog notes
├── examples/           # sample dataset for the demo
└── tests/              # 77 unit tests — no network, no corpus needed
```

- **Testing:** `pytest tests/ -v` → 77 passed (mocked `httpx`, generic sample fixture).
- **Roadmap (v0.1.4+):** `pipeline_version` in audit records; DataCite/mEDRA DOI sources;
  cross-machine reproducibility (relativize scan paths); pluggable per-domain packs.
- **Contributing:** issues and PRs welcome — please read the design docs in `references/` first.
- **License:** MIT — see [LICENSE](LICENSE).

## Citation

```bibtex
@software{science_mentor_2026,
  author  = {science-mentor contributors},
  title   = {science-mentor: a code-enforced scientific-method engine (data-first anomaly →
             hypothesis → discriminating experiment) for Claude Code},
  year    = {2026},
  version = {0.2.0},
  url     = {https://github.com/dalek12310/science-mentor}
}
```
