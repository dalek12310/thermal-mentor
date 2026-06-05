# science-mentor — distillation & repositioning design

> Status: approved (2026-06-02). Supersedes the "thermal-mentor" framing.
> Decisions: new name **science-mentor**; execution **staged full transformation** with a checkpoint after each stage.

## 1. Problem

The project is published as `thermal-mentor`, but its backend has **zero domain logic**
(`grep thermal/phonon/perovskite` over `scripts/` hits only a User-Agent string and a report
title). The real product is a domain-general engine; the thermal name, half-shipped
publication-corpus machinery, and an internals-first README hide that and overstate scope.

Four owner-stated concerns:
1. After distillation it should read as a **methodological general solution (通解)**.
2. The name **"thermal" doesn't fit**.
3. The **README is unclear** and does not convey research value.
4. **Doubts about the SKILL approach** (reliability / value).

## 2. The distilled kernel (what we are actually shipping)

A **code-enforced, anti-fabrication "single-turn scientific method" engine**:

> observe deterministically (scan data before the LLM speaks) → externalize observations
> with verbatim quotes → infer user intent → enumerate anomalies (data vs. prior expectation)
> → force every mechanism to carry a falsifiable `predicts_observable` → propose a
> discriminating experiment (prefer ones answerable from existing data) → adversarial
> multi-model cross-review → multi-source citation verification (never fabricate) →
> reproducibility lock.

Non-negotiable invariants (the actual value): no verbatim quote → no conclusion; no
falsifiable prediction → not a mechanism; no multi-source check → no citation; deterministic
scan precedes any LLM interpretation and is hashed separately from model provenance.

## 3. General kernel vs. thermal residue

**General (keep as-is — this is the kernel):** `anomaly_brief.py` scanner + trend detection;
anomaly→hypothesis→experiment schema *structure* + `predicts_observable` invariant; 3-step
reflective routing + "every option carries verbatim quote + inference"; cross-review round-table
+ consensus-graded confidence; multi-source DOI verifier + `verifier_error` side-channel;
`data_brief_hash` provenance split; plain-language boundary rule; the four eval metrics.

**Thermal/materials residue (make pluggable as a "domain pack", thermal = first reference pack):**
hardcoded research directions + journal list + anchor registry + corpus/retraction in
`references/ask-first-prompts.md` and the preserved-terms whitelist in
`references/user-facing-language.md`; materials-coded schema field names and the `dft` enum.

## 4. Confirmed defects to fix (adversarially verified)

| sev | defect | file |
|---|---|---|
| high | `hybrid_retrieve.py` called unconditionally but absent from `scripts/` | SKILL.md:197 |
| high | `build_vector_index.py` referenced but absent | SKILL.md:347 |
| high | "materials-science-domain-agnostic" / "all science" over-promise vs materials-bound schema | SKILL.md:8; output-schemas-data-first.md |
| high | README internals-first, no worked example, violates own no-codename rule | README.md, README_zh-CN.md |
| med | materials-coded field names (`expected_textbook`, `expected_source_type`, `materials_system`); `answerable_by` enum `dft` | references/output-schemas-data-first.md, verifier.py, tests |
| med | thermal domain content hardcoded in prompts vs. pluggable | references/ask-first-prompts.md |
| low/doc | test-count drift (says 64, is 67); per-machine-only reproducibility hash | README*, MANUAL* |

**Rejected (do NOT act on):** audit claimed `codex:codex-rescue` / `deepseek-code-reviewer`
"don't exist" — false positive; they are valid Agent `subagent_type`s (audit checked the
*skills* registry, not agent types). Leave cross-review reviewer names unchanged.

## 5. Staged plan (checkpoint = run tests + show diff after each)

- **Stage 1 — honesty + README (pure docs, zero code risk).** Gate the two non-existent
  scripts behind corpus-existence checks reusing SKILL.md:308 wording; replace
  "domain-agnostic/all science" with "physics/materials-first, mechanism general"; rewrite
  both READMEs (problem → value → worked example → skill quick-start → two modes →
  "how we keep it honest" → advanced/library → install → internals → project info); fix
  64→67 drift. Reposition copy under the chosen name **science-mentor** even though rename
  lands in Stage 4.
- **Stage 2 — schema generalization (vocabulary only, kernel unchanged).**
  `expected_textbook`→`expected_from_prior_knowledge`, `expected_source_type`→`expectation_basis`,
  `materials_system`→`study_system`, `answerable_by` enum `{existing_data,new_experiment,dft}`
  →`{existing_data,new_observation,computation}`; neutral placeholders in schema docs + one
  example per domain; update verifier/render/tests accordingly; `pytest` green.
- **Stage 3 — extract a swappable "domain pack".** Move hardcoded research directions, journal
  list, preserved-terms whitelist into a config structure; thermal becomes the first reference
  pack; architecture already degrades gracefully via the corpus env var.
- **Stage 4 — rename thermal→science (largest surface, last).** skill `name:`, package name,
  env `THERMAL_MENTOR_CORPUS`→`SCIENCE_MENTOR_CORPUS` (old name kept one release as deprecated
  fallback), BibTeX key/title/url, badges, repo URLs, User-Agent, tests/fixtures; `pytest`
  (67, no network) green. Physical repo-dir + GitHub-slug + `~/.claude/skills/` rename are noted
  as manual user steps (they touch the git remote / local install).
  - **Version bump deferred (decided during execution).** `0.1.3` is shared by ~30 strings mixing
    current-version spots with historical spec-filename refs and the reproducibility
    `scanner_version` (which feeds `data_brief_hash`). A mechanical bump would corrupt historical
    refs / shift the hash, and the bump is orthogonal to the four concerns. Documented the rename
    in CHANGELOG `[Unreleased]` instead; a clean `0.2.0` bump is recommended at actual release.

## 6. Verification

`pytest tests/ -q` (no network, no corpus) must stay green after every stage. Mode-0 render +
`run_acceptance --repeat` re-run on the demo dataset after Stage 2 and Stage 4.

## 7. Out of scope / honest caveats

- Cross-machine reproducibility (absolute paths in `scanner_manifest`) — noted, not fixed here.
- `content_sanity_check` is a stub (similarity always 0.0); we will stop describing it as a
  working "sanity check" rather than pretend it computes similarity.
- The publication-strategy corpus stays thermal/condensed-matter flavored — that is honest;
  we only stop *claiming* it is general.
