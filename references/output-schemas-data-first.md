# Output JSON schemas — data-first (mode 0)

These schemas extend `output-schemas.md` (which covers the publication modes). Mode 0 produces JSON first; `verifier.py` dispatches to `verify_mode_0`, then Step H renders Markdown per `SKILL.md`.

## `data_brief.json` — Step A output

Produced by `anomaly_brief.py` scanner half + mentor LLM half (see SKILL.md Step 0a/0b). The mentor's structured detection fills `observed_trend` and `expected_source_type` so anomaly classification is not entirely subjective.

```json
{
  "files_found": [
    {"path": "notes.txt", "type": "txt", "tokens": 1240}
  ],
  "central_claims": [
    {
      "claim_text": "dopant series shows monotonic decrease in property X",
      "source_file": "notes.txt",
      "quote_line": 12,
      "quote_verbatim": "property X drops 25% across 0/2/4/6 mol% series"
    }
  ],
  "performance_numbers": [
    {
      "what": "property_X @ RT",
      "value": "1.2",
      "units": "a.u.",
      "source": "notes.txt",
      "quote_verbatim": "..."
    }
  ],
  "candidate_anomalies": [
    {
      "anomaly_id": "A1",
      "observation_short": "defect signal monotonically decreases with dopant content",
      "observed_trend": "monotonic_decrease",
      "expected_source_type": "defect-chemistry textbook",
      "quote_verbatim": "XPS+EPR 0/2/4/6% signal decreases monotonically",
      "quote_source": "notes.txt:7",
      "quote_hash": "sha256:...",
      "expected_textbook_short": "aliovalent substitution should net-increase defects",
      "mentor_inference": "self-compensation only explains 'no increase', not 'baseline decrease'",
      "surprise_score": "high"
    }
  ],
  "materials_system": "doped oxide series",
  "manuscript_stage": "draft|plan|data-only|mixed",
  "data_brief_hash": "sha256:...",
  "scanner_manifest": {
    "cwd": "/path/to/manuscript/dir",
    "files_glob_pattern": "**/*.{txt,md,docx,pdf,csv,xlsx}",
    "file_hashes": {"notes.txt": "sha256:..."},
    "scanner_version": "0.1.3",
    "timestamp": "2026-05-25T10:32:00Z"
  },
  "audit_log_id": "20260525-103200-xyz789"
}
```

Field notes:

- `observed_trend` ∈ {`monotonic_increase`, `monotonic_decrease`, `non_monotonic`, `unknown`} — filled by `summarize_csv` deterministic detection where possible (CSV numeric column), not by LLM. Controls `false_anomaly_rate`.
- `expected_source_type` — explicit label for what textbook / consensus the observation appears to contradict (e.g. `defect-chemistry textbook`, `Shannon radii`, `phonon-defect scaling`, `user-provided`).
- `quote_hash` — `sha256` of `quote_verbatim` byte sequence. Lets downstream stages detect LLM rewrites of the original quote (anti-drift).
- `data_brief_hash` — sha256 of canonical-serialized brief (sans the hash field itself). Used by acceptance runs to lock reproducibility across N repeats.
- `scanner_manifest.file_hashes` — per-file sha256 to freeze the exact inputs the brief was generated from.

Design rationale: `observed_trend` / `expected_source_type` / `quote_hash` / `data_brief_hash` / `scanner_manifest` are all designed for false-anomaly control + acceptance reproducibility.

Anti-drift rule: `candidate_anomalies` items take precedence over `central_claims` in dedupe (same source_file + line/para). Avoids a single sentence appearing in two lists.

## Anomaly 6-field schema — Step B output

Promoted from `candidate_anomalies` by mentor reasoning at the start of mode 0 Step B.

```json
{
  "anomaly_id": "A1",
  "observation": "Across 0/2/4/6 mol% dopant series, the defect signal (XPS O1s + EPR) decreases monotonically",
  "expected_textbook": "Aliovalent substitution textbook: trivalent dopant on tetravalent site should net-increase defects to maintain charge balance",
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

Field notes:

- `observation` — 1-2 line plain text; verbatim quote lives in `data_evidence`.
- `expected_textbook` — explicit prediction the anomaly violates. The mentor must name a textbook / defect chemistry / scaling law — not "literature says".
- `surprise_score` ∈ {`high`, `medium`, `low`} — mentor subjective; high means reverses textbook prediction.
- `data_evidence` — at least 1 verbatim quote with file+line/para pointer.
- `context_questions_to_user` — mentor's reflexive questions ("things the user knows but didn't write in the manuscript"). User can answer inline; mentor merges before Step C.

## Hypothesis schema — Step E output

```json
{
  "hypothesis_id": "H1a",
  "anomaly_id": "A1",
  "mechanism_text": "Dual-site self-compensation: dopant occupies both A and B sublattices",
  "data_support": [
    "Raman shift at 4 mol% consistent with B-site occupancy (notes.txt:14)"
  ],
  "data_contradict": [
    "..."
  ],
  "supporting_refs": [
    {
      "ref_id": "R001",
      "ref_type": "doi",
      "value": "10.1038/...",
      "authors_text": "...",
      "year": 2024,
      "verification_status": "unset (filled by verify_mode_0)"
    }
  ],
  "predicts_observable": [
    "A-site:B-site occupation ratio ~ 1:1 if purely charge-compensated",
    "EXAFS coordination number = mean of (CN_A, CN_B)",
    "Raman should show modes from both A-site and B-site dopant"
  ]
}
```

Field notes:

- `mechanism_text` — physically explicit mechanism; not "defect chemistry" but the specific mechanism (e.g. "dual-site self-compensation").
- `data_support` / `data_contradict` — each entry is a `(quote, source)` pair from the user's data, not literature.
- `supporting_refs` — only populated if Step C user picked "search literature". DOIs go through `verify_doi_multisource` in Step G.
- `predicts_observable` — **CRITICAL**. For each candidate mechanism, list what else should be visible in the data if mechanism is true. Lets the user self-verify without trusting mentor.

## Experiment schema — Step F output

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

Field notes:

- `discriminates_between` — list of hypothesis_ids the experiment can distinguish.
- `answerable_by` ∈ {`existing_data`, `new_experiment`, `dft`}. Prefer `existing_data` — actively look for user's existing assets that haven't been mined.
- `if_new_experiment` — only filled when `answerable_by="new_experiment"`. Mentor estimates rough effort / cost; not authoritative, user should sanity-check.
- `expected_outcome` — predicted readout under each hypothesis. Lets the user pre-judge whether the experiment is worth doing before running it.

## `both` mode handover schema

When Step 1 user picks `both`, mode 0 final payload carries a top-level `mode_0_handover` field that publication mode reads to pre-fill its Level-2 `AskUserQuestion` option descriptions.

| handover field | mode 0 source | publication mode consumer |
|---|---|---|
| `anomalies[*].observation` | Step B 6-field schema | novelty `claim_text` candidate (user can revise in Level-2) |
| `hypotheses[*].mechanism_text` | Step E | novelty `mechanism claim` candidate |
| `experiments[*].discriminates_between` | Step F | highlight `selling point` candidate (mechanism / performance / methodology) |
| `experiments[*].answerable_by == "existing_data"` | Step F | highlight "user's unique asset" candidate |
| `materials_system` | Step A | `corpus_query` system filter |
| `data_brief_hash` | Step A | publication `audit_log.linked_data_brief_hash` (lineage) |

Concrete JSON shape:

```json
{
  "mode": "data_first",
  "anomalies": [...],
  "hypotheses": [...],
  "experiments": [...],
  "mode_0_handover": {
    "central_claim_candidates": [
      "Defect signal monotonically decreases with dopant content, against textbook prediction"
    ],
    "mechanism_claim_candidates": [
      "Dual-site self-compensation"
    ],
    "selling_point_candidates": [
      "mechanism — coupling of dual-site occupation with monotonic defect-signal decrease"
    ],
    "existing_data_assets": [
      "3+ vs 4+ speciation via XPS at 4 mol% dopant"
    ],
    "materials_system": "doped oxide series",
    "data_brief_hash": "sha256:..."
  },
  "audit_log_id": "20260525-103200-xyz789"
}
```

Publication mode reads `mode_0_handover`, **does not blindly accept** — Level-2 still uses `AskUserQuestion` so the user can confirm / revise each candidate. The handover only pre-fills option descriptions, eliminating "system forgot what we just discussed" friction.
