# Changelog

All notable changes to science-mentor are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-06-02

### Changed — distillation & repositioning (formerly `thermal-mentor`)
- **Renamed `thermal-mentor` → `science-mentor`.** The backend has no domain logic; the name
  now matches the real product: a domain-general, code-enforced scientific-method engine.
  Skill `name`, package, repo URLs, badges, and User-Agent updated. Trigger keywords "thermal
  mentor" / "热学导师" retained as legacy aliases. *(GitHub repo-slug and `~/.claude/skills/`
  directory rename are manual user steps.)*
- **Env var `THERMAL_MENTOR_CORPUS` → `SCIENCE_MENTOR_CORPUS`**, old name kept as a deprecated
  fallback for one release (`verifier.py`, `live_search.py`).
- **Generalized mode-0 schema vocabulary** (kernel unchanged): `expected_textbook` →
  `expected_from_prior_knowledge`, `expected_source_type` → `expectation_basis`,
  `materials_system` → `study_system`, and `answerable_by` enum `dft` → `computation`
  (covers DFT/MD/any simulation). Old field names still read for backward compatibility.
- **Extracted swappable domain packs** (`domains/`): research directions, target journals,
  preserved-term whitelist, and expectation vocabulary now live in a pluggable pack;
  `thermal.md` is the default reference pack, `_template.md` is a neutral starter with worked
  biology/economics examples.

### Fixed — honesty
- Gated the never-shipped `hybrid_retrieve.py` / `build_vector_index.py` behind
  corpus-existence checks (they previously appeared as unconditional commands in `SKILL.md`).
- Mirrored the guarded `hybrid_retrieve.py` wording into both manuals and corrected the DOI
  absence explanation in blog/protocol docs so Crossref misses are not described as terminal.
- Replaced the "materials-science-domain-agnostic" / "all science" over-promise with the honest
  scope: *physics/materials-first, mechanism-general; other fields need a domain pack*.
- Rewrote both READMEs value-first (problem → value → worked example), no codename-first jargon.
- Corrected test-count drift (docs said 64; suite has 77).

### Fixed — pre-release blind audit (Codex + DeepSeek V4 + Opus, all verified against source)
- **DOI chain correctness**: `doi.org HEAD` is now the *sole* authority for absence — a Crossref
  miss no longer yields a false `not_found` for DataCite/Zenodo/mEDRA DOIs; and a transient
  doi.org status (429/5xx/403) now raises → `verifier_error` instead of a cached false `not_found`.
- **Mode-0 evidence**: `data_evidence.source` of the documented `file.ext:7` form (and
  manifest-`cwd`-relative paths) now resolves correctly (was always `not_found`); the renderer
  flags evidence whose source file is missing and now shows hypothesis refs + their status.
- **Cross-review**: `verifier_error` refs are retained in an `unverifiable_refs` bucket (not
  deleted) and rendered — honoring the "network failure ≠ not verified" principle.
- **Acceptance**: `save_run` now verifies the payload before persisting (previously persisted the
  raw, unverified payload), and seeds the generated `audit_log_id` into the payload so the JSON
  and the audit record share one lineage id. A verifier crash now aborts persistence instead of
  writing a raw payload.
- **Robustness**: bare-string `supporting_refs` are coerced (no crash); arXiv refs →
  `external_unverified` (not falsely `not_found`); `summarize_csv` computes trend/row_count over
  ALL rows (was capped at ~20); `live_search` errors go to stderr (no longer corrupt JSON stdout);
  `SKILL.md` Python blocks import `Path` before use; `manuscript_brief.py` gained the documented CLI;
  script modules now support both direct script execution and `python -m scripts.<tool>`.
- **Honesty/CLI**: `verifier.py --json` emits the verified payload; the stub content sanity-check
  no longer raises a false "overlap low" warning on every claim; README softened from blanket
  "code-enforced" to distinguish code-verified citations from skill-rule invariants; "6 sources" →
  "up to 6 (4 always-on, +2 with keys)"; `LICENSE` copyright renamed to science-mentor; the
  mode-0 walkthrough now carries `scanner_manifest.cwd` so its own demo evidence verifies.

### Version
- Bumped `0.1.3` → `0.2.0` in the canonical current-version spots: `pyproject.toml`, README
  badges + BibTeX citations, the `User-Agent` strings, `run_acceptance` `pipeline_version`, the
  MANUAL headers/footers, and the issue template.
- **`scanner_version` deliberately kept at `0.1.3`** — it is a data-format version that feeds
  `data_brief_hash`; bumping it would silently change every reproducibility hash. Historical
  "added in v0.1.3" notes and dated spec-filename references are also left intact.

## [0.1.3] - 2026-05-26

### Added
- **Reflective routing protocol** (`SKILL.md` Step 0/0.5/1) — scans CWD before asking user intent, presents tailored options based on detected anomalies
- **Mode 0 (data-first) pipeline** — anomaly enumeration → hypothesis enumeration → discriminating experiment proposal → optional cross-review → verifier → audit log
- **DOI multi-source verification** (`scripts/doi_verify_multisource.py`) — 4 always-on sources (OpenAlex / Crossref / Semantic Scholar / DOI.org HEAD) + 2 env-gated sources (Lens.org via `LENS_API_TOKEN`, WoS via `WOS_API_KEY`) with 24h cache
- **Explicit `verifier_error` vs `not_found` semantic** — network failures NOT silently mapped to `verified`
- **Round-table cross-review merge** (`scripts/cross_review_merge.py`) — non-discriminatory DOI attribution (first-wins ordering, no reviewer singled out as "high risk"), finding classification (consensus / majority / singleton)
- **paper-pdf-acquisition handoff** (`scripts/paper_pdf_handoff.py`) — CSV manifest for cross-session collaboration
- **Reproducibility lock** — `data_brief_hash` computed over scanner-determined invariants only (LLM-enriched fields excluded)
- **N-repeat acceptance machinery** — `run_acceptance.py --repeat N` for stability testing
- **L5 mode 0 metrics** — `anomaly_recall_rate`, `hypothesis_completeness`, `existing_data_answerable_rate`, `false_anomaly_rate`
- **Bilingual docs** — English README + 简体中文 README + 1000+ line manuals in both languages
- **Lens.org + WoS source wrappers** — env-gated, integrated into async fan-out via `asyncio.to_thread`
- **Always-available 召唤 footer** — every Markdown output ends with a clickable "ask second opinion" trigger
- **人话 hard rule** — user-facing strings use plain language, no internal codenames

### Changed
- `verifier.py` `check_doi` now delegates to `verify_doi_multisource` via LegacyDoiAdapter (fixes silent FP bug from v0.1 where HTTP errors mapped to `external_unverified`)
- `verifier.py` `verify_payload` (publication mode) now propagates `verifier_error_metadata` side-channel through to Markdown render (⚠️ flag)
- `live_search.py` async orchestrator now uses `build_l3_sources()` instead of hardcoded 3-source list
- `_compute_validity` skip-clause now excludes refs with `verifier_error_metadata` from citation_validity_rate denominator
- `anomaly_brief.py` real-world robustness: GB18030 CSV fallback, Office lock-file (`~$...`) skip, corrupt PDF tolerance, None-keyed dict hashing

### Fixed
- Silent FP bug in `check_doi` (audit §5.4 #6) — was returning `external_unverified` for valid OpenAlex hits
- `cross_review_merge.py` lacked `main()` CLI despite SKILL.md Step F.5 invoking it as a script
- `data_brief_hash` invariant broken between `build_data_brief_scaffold` (CLI) and `build_data_brief` (mentor session) — both paths now produce same hash for same cwd
- `run_acceptance.py` `JSONDecodeError` on malformed `--reproducibility-manifest` or payload — now exits with code 2 + clear error
- `anomaly_brief.py main()` was a footgun (always crashed via `NotImplementedError`) — now produces scanner-only scaffold

### Acceptance
- HfO2-GdNbO4 system, 9-run × N=3 acceptance:
  - **S1+S2 hit rate = 1.00** (acceptance threshold: ≥ 0.66)
  - All 4 target anomalies (S1 V_O monotonic decrease, S2 dual-site, S3 κ-ε coupling, S4 mech unchanged) surfaced reliably across all 9 runs
  - Cross-mode convergence: Run-C 3/3 picked Nature Communications as top target (medium confidence)

### Cross-review (Round-table)
- Round 1: 11 findings (1 Critical, 6 High, 4 Medium/Low)
- Round 2: All Critical/High consensus findings fixed (F1 cross_review_merge CLI, F2 verifier_error_metadata propagation, F3+D1 live_search wiring + error boundaries, D2 JSON safety, F5 anomaly_brief footgun, D6/F7 hash invariant)
- Round 3: Opus verdict = ready_to_release

## [0.1.0] - 2026-05-23 (private)

Initial private version with publication-strategy-only routing. Not released publicly.

---

## Roadmap (planned for v0.1.4+)

- `audit_log.py` `pipeline_version` field
- DataCite + mEDRA DOI source extensions
- Reproducibility block: Python version + dep hashes + random seed
- SKILL.md mirror drift pre-commit hook
- Defensive invariants for `verifier_error_metadata` propagation
- Generalize fixtures beyond materials science (chemistry, biology examples)

[0.2.0]: https://github.com/dalek12310/science-mentor/releases/tag/v0.2.0
[0.1.3]: https://github.com/dalek12310/science-mentor/releases/tag/v0.1.3
