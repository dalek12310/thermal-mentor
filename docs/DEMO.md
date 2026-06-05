# Tutorial: science-mentor on a Solid-State Electrolyte Doping Study

This demo runs science-mentor's mode 0 pipeline on a synthetic but plausible dataset:
**Ta-doped LLZO garnet electrolyte**, looking for the anomaly that
**smaller lattice + tighter ion channel = LOWER activation energy** (counter to textbook).

Dataset at `examples/demo_dataset/`:
- `notes.md` — researcher's working notes
- `data.csv` — 4-row experimental matrix (Ta 0/2/4/6 mol%)

> **Note**: This is a fictitious dataset for illustration. Real LLZO doping studies
> typically show monotonic conductivity increase, but the specific magnitudes and
> mechanical-invariance pattern shown here are simplified for tutorial clarity.

## Step 1 — Scan the data dir into a scaffold

```bash
cd science-mentor
python scripts/anomaly_brief.py examples/demo_dataset --out tmp/demo_brief.json --include-text
```

Expected output:
```
[saved] tmp/demo_brief.json (scaffold: 2 files scanned, data_brief_hash=<hash>..., include_text=True)
[note] mentor session must enrich LLM fields before using as complete data_brief
```

Inspect `tmp/demo_brief.json` — you'll see `files_found`, `csv_summaries`
(with monotonic trend detection on each column), and `text_files_content` (notes.md text).

The `csv_summaries` should show:
- `lattice_param_A` → `monotonic_decrease`
- `sigma_RT_Scm` → `monotonic_increase`
- `E_act_eV` → `monotonic_decrease`
- `YoungsModulus_GPa` → `monotonic_increase` (very small range)
- `hardness_GPa` → mixed (`non_monotonic`)

## Step 2 — Enrich (this is where mentor reasoning happens)

In production, this is the Claude session doing the work via SKILL.md. For this demo,
we'll hand-construct the enriched payload to show what mode 0 expects:

`tmp/demo_payload.json`:
```json
{
  "mode": "data_first",
  "scanner_manifest": { "cwd": "examples/demo_dataset", "manifest_hash": "<copy from demo_brief>" },
  "anomalies": [
    {
      "anomaly_id": "A1",
      "observation": "Lattice parameter DECREASES with Ta doping (0.4% across 0-6 mol%) yet ionic conductivity INCREASES 4-fold, and activation energy E_a DROPS from 0.42 to 0.31 eV.",
      "expected_from_prior_knowledge": "In standard ion-hopping models, lattice contraction reduces interstitial channel width, RAISING the migration barrier. Conductivity should decrease unless carrier concentration grows fast enough to compensate.",
      "surprise_score": "high",
      "data_evidence": [
        {"source": "notes.md", "quote_text": "Lattice parameter decreases monotonically by 0.4%", "line_or_para": "structural"},
        {"source": "data.csv", "quote_text": "E_act_eV column: 0.42→0.31 eV monotonic", "line_or_para": "all rows"}
      ],
      "mentor_inference": "Self-compensation by structural disorder: Ta5+/Zr4+ mixing introduces local distortions that open new percolation paths — net effect is decoupling from average lattice geometry.",
      "context_questions_to_user": [
        "Did you measure pair-distribution-function (PDF) on these samples? It would distinguish average lattice contraction from local environment opening.",
        "What's the carrier concentration vs Ta — calculated from Nernst-Einstein on sigma + diffusion data, or assumed?"
      ]
    },
    {
      "anomaly_id": "A2",
      "observation": "Mechanical properties (E, H) effectively constant (<2% change) while ionic transport changes by 4x and E_a drops 26%.",
      "expected_from_prior_knowledge": "Standard elastic-decoupling story: lattice changes that affect transport usually also affect modulus. A 0.4% lattice contraction with no modulus change suggests the disorder is local, not bulk.",
      "surprise_score": "medium",
      "data_evidence": [
        {"source": "data.csv", "quote_text": "YoungsModulus_GPa: 150.2 → 151.5 across Ta0-Ta6 (less than 1%)", "line_or_para": "performance section"}
      ],
      "mentor_inference": "Confirms A1's picture: changes are LOCAL (point-defect-scale) not GLOBAL (lattice-scale).",
      "context_questions_to_user": [
        "Any DFT formation energy calculations on Ta substitution at different sites? Would distinguish Zr-only vs partial Li-site occupation."
      ]
    }
  ],
  "hypotheses": [
    {
      "hypothesis_id": "H1a",
      "anomaly_id": "A1",
      "mechanism_text": "Ta5+-induced local distortion creates new ion percolation paths that bypass the average lattice contraction.",
      "data_support": "Lattice contraction (avg) + conductivity increase = decoupling",
      "data_contradict": "None in current data",
      "supporting_refs": [],
      "predicts_observable": [
        "PDF should show broader peaks at Ta6 vs Ta0 (more local disorder)",
        "Raman should show new modes / broadening from Ta-O vs Zr-O environments",
        "NMR 7Li T1 should differ at Ta6 vs Ta0 (different local environments)"
      ]
    },
    {
      "hypothesis_id": "H1b",
      "anomaly_id": "A1",
      "mechanism_text": "Carrier concentration increases faster than geometric penalty (Ta5+ donates electron to Li sublattice OR creates Li vacancies).",
      "data_support": "Conductivity 4x while E_a drops 26% -> mostly carrier-concentration story",
      "data_contradict": "If true, Hall measurement should show n increase",
      "supporting_refs": [],
      "predicts_observable": [
        "Hall effect: carrier concentration n(Ta) should be measurable",
        "Wagner polarization at sub-electrolyte voltage should show electronic conductivity > 0"
      ]
    }
  ],
  "experiments": [
    {
      "experiment_id": "E1",
      "anomaly_id": "A1",
      "discriminates_between": ["H1a", "H1b"],
      "experiment_text": "Run Hall effect on the same 4 samples to measure carrier concentration vs Ta content.",
      "answerable_by": "new_experiment",
      "if_new_experiment": "Standard 4-point Hall apparatus, 30 min/sample",
      "expected_outcome": {
        "H1a_carrier_const": "n flat -> confirms percolation hypothesis",
        "H1b_carrier_increase": "n increases 4x -> confirms carrier-density hypothesis"
      }
    }
  ],
  "open_questions_data_alone_cannot_answer": [
    "Whether the carrier concentration genuinely increases requires Hall (not in current dataset)",
    "Whether the disorder is bulk or grain-boundary dominated requires impedance frequency dispersion analysis"
  ],
  "audit_log_id": ""
}
```

## Step 3 — Verify the payload

```bash
python scripts/verifier.py tmp/demo_payload.json
```

Output: rendered Markdown that walks through anomalies → hypotheses → experiments,
with the always-available 召唤 footer at the bottom.

## Step 4 — Persist as an acceptance run

```bash
python scripts/run_acceptance.py tmp/demo_payload.json \
    --run-name "llzo_ta_doping_v0.1_dataonly_run1" \
    --reproducibility-manifest tmp/demo_brief.json \
    --repeat 1
```

Output JSON+MD lands in `acceptance_runs/` (gitignored by default).
The `reproducibility` block records `data_brief_hash`, `model_id`, `system_prompt_hash`.

## Step 5 (optional) — Cross-review

Have 2-3 reviewer LLMs critique the output, save their JSON to `tmp/round1_*.json`,
then:

```bash
python scripts/cross_review_merge.py tmp/round1_*.json --out tmp/cross_review_final.json
```

Output: classified findings (consensus/majority/singleton), non-discriminatory DOI attribution,
verified vs deleted refs.

---

## What you've seen

- mode 0 turns 6 columns + 1 markdown file into 2 anomalies + 3 hypotheses + 1 experiment
- The verifier flags any DOI ref through the 4 always-on + 2 env-gated source chain
- The reproducibility block locks scanner-determined invariants
- Cross-review (if invoked) classifies findings without favoring any one reviewer

## What the demo skipped

- Real LLM-driven enrichment (the demo hand-constructed Step 2)
- Live DOI verification (no external network calls)
- The `paper-pdf-acquisition` cross-session handoff (separate skill)
- The full publication-strategy pipeline (requires corpus, see Section 7 of `docs/MANUAL.md`)

## Try it on your own data

Replace `examples/demo_dataset/` with a folder containing your own manuscripts + CSVs,
run Step 1, then invoke `/science-mentor` in Claude Code to do Step 2 interactively.
