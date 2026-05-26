# %% [markdown]
# # thermal-mentor Mode 0 Walkthrough
#
# This script demonstrates the full mode 0 pipeline on the synthetic LLZO dataset.
# Run with:
# ```bash
# python docs/notebooks/01_mode_0_walkthrough.py
# ```
# On Windows, set `PYTHONIOENCODING=utf-8` first — the rendered Markdown
# contains UTF-8 punctuation that the default gbk console codec rejects.
#
# Or step through cells in Jupyter / VS Code with the Python extension
# (the `# %%` markers turn this into a cell-based notebook view).

# %% Encoding setup (Windows GBK terminal compatibility)
import sys
if hasattr(sys.stdout, "reconfigure"):
    # Ensures Unicode (•, 💬, ⚠️) in rendered Markdown doesn't crash on Windows cp936/GBK consoles
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# %% Setup
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# %% [markdown]
# ## Step 1 — Scan the demo dataset
#
# `build_data_brief_scaffold` walks the cwd, hashes every supported file,
# runs per-column monotonic trend detection on CSVs, and extracts text from
# `.md / .docx / .pdf / .txt`. The resulting scaffold has a deterministic
# `data_brief_hash` over the scanner-determined fields (LLM-enriched
# fields are excluded so multiple runs against the same cwd hash equal).

# %% Step 1 — Scan
from anomaly_brief import build_data_brief_scaffold

scaffold = build_data_brief_scaffold(
    REPO_ROOT / "examples" / "demo_dataset",
    include_text=True,
)
print(f"Scanned {len(scaffold['files_found'])} files")
print(f"data_brief_hash: {scaffold['data_brief_hash'][:16]}...")
print()
print("CSV trends detected:")
for path, summary in scaffold["csv_summaries"].items():
    print(f"  {Path(path).name}")
    for col, info in summary.get("columns", {}).items():
        if info.get("numeric"):
            print(
                f"    {col}: {info['trend']} "
                f"(range {info.get('min', '?')} → {info.get('max', '?')})"
            )

# %% [markdown]
# ## Step 2 — Construct mode 0 payload
#
# In production, this is the Claude session doing the work via SKILL.md.
# Here we hand-construct the enriched payload to show what mode 0 expects
# as input to the verifier.

# %% Step 2 — Mode 0 payload
payload = {
    "mode": "data_first",
    "scanner_manifest": {
        "manifest_hash": scaffold["scanner_manifest"]["manifest_hash"],
    },
    "anomalies": [
        {
            "anomaly_id": "A1",
            "observation": (
                "Lattice contraction yet ionic conductivity rises 4x "
                "and E_a drops 26%"
            ),
            "expected_textbook": (
                "Smaller lattice = tighter channel = higher migration "
                "barrier (standard hopping model)"
            ),
            "surprise_score": "high",
            "data_evidence": [
                {
                    "source": "notes.md",
                    "quote_text": "Lattice parameter decreases monotonically",
                    "line_or_para": "structural",
                },
            ],
            "mentor_inference": (
                "Self-compensation via local Ta-Zr disorder opens "
                "percolation paths decoupled from average lattice"
            ),
            "context_questions_to_user": [
                "Did you measure PDF? Carrier concentration vs Ta?",
            ],
        }
    ],
    "hypotheses": [
        {
            "hypothesis_id": "H1a",
            "anomaly_id": "A1",
            "mechanism_text": (
                "Local Ta5+-induced distortion creates new percolation paths"
            ),
            "data_support": "Conductivity up + E_a down both observed",
            "data_contradict": "None in current data",
            "supporting_refs": [],
            "predicts_observable": [
                "PDF broader peaks at high Ta",
                "NMR T1 differences",
            ],
        }
    ],
    "experiments": [
        {
            "experiment_id": "E1",
            "anomaly_id": "A1",
            "discriminates_between": ["H1a"],
            "experiment_text": (
                "Hall effect to measure carrier concentration vs Ta"
            ),
            "answerable_by": "new_experiment",
            "if_new_experiment": "4-point Hall, 30 min/sample",
            "expected_outcome": {
                "H1a": (
                    "n flat = percolation, n increases = carrier-density"
                ),
            },
        }
    ],
    "open_questions_data_alone_cannot_answer": [
        "Hall data not in current dataset",
        "Frequency-dispersion impedance for bulk vs GB separation",
    ],
    "audit_log_id": "",
}

# %% [markdown]
# ## Step 3 — Run the verifier
#
# `run_pipeline` dispatches on `payload['mode']`. For `data_first`, it runs
# `verify_mode_0` + `render_markdown_mode_0` and computes the mode 0
# citation_validity_rate (fraction of data_evidence sources that exist
# on disk relative to the scanner_manifest).

# %% Step 3 — Verify
from verifier import run_pipeline

result = run_pipeline(json.dumps(payload), run_sanity=False)
if "error" in result:
    print(f"Verifier error: {result['error']}")
    if "details" in result:
        print("Schema violations:")
        for d in result["details"]:
            print(f"  - {d}")
else:
    print("Verifier output:")
    print(result.get("markdown", ""))
    print()
    print(
        f"citation_validity_rate: "
        f"{result.get('citation_validity_rate', '?')}"
    )

# %% [markdown]
# ## Step 4 — Cross-review merge example
#
# Two reviewer LLMs critiqued the output in parallel. The merge step
# classifies their findings (consensus / majority / singleton) and
# attributes any introduced DOI refs non-discriminatorily
# (first-wins ordering, no reviewer singled out as "high risk").
#
# Here we use mocked reviewers with no `introduced_refs` so the merge
# step doesn't make network calls.

# %% Step 4 — Cross-review merge
from cross_review_merge import merge_reviews, render_merge_markdown

reviews = {
    "opus": {
        "findings": [
            {
                "id": "O1",
                "text": (
                    "Anomaly framing is clean; missing: stiffness/"
                    "conductivity comparison with undoped reference"
                ),
                "severity": "medium",
            },
            {
                "id": "O2",
                "text": (
                    "H1a predicts_observable could include EXAFS Ta-O "
                    "coordination"
                ),
                "severity": "low",
            },
        ],
        "introduced_refs": [],
    },
    "ds": {
        "findings": [
            {
                "id": "D1",
                "text": (
                    "Anomaly framing is clean; missing: stiffness/"
                    "conductivity comparison"
                ),
                "severity": "medium",
            },
            {
                "id": "D2",
                "text": (
                    "E1 Hall experiment should specify temperature; "
                    "conductivity changes 4x across Ta but Hall may saturate"
                ),
                "severity": "medium",
            },
        ],
        "introduced_refs": [],
    },
}

merged = merge_reviews(reviews)
print(render_merge_markdown(merged))
print()
print(f"Reviewers used: {merged['reviewers_used']}")
print(f"Findings classified: {len(merged['findings'])}")
print(f"Surviving refs (post-verification): {len(merged['surviving_refs'])}")
print(f"Deleted refs: {len(merged['deleted_refs'])}")

# %% [markdown]
# ## What you've seen
#
# - Step 1 — deterministic scanner produces `data_brief_hash` + monotonic
#   trend annotations.
# - Step 2 — the mode 0 payload schema (anomalies × hypotheses × experiments
#   × open_questions).
# - Step 3 — `run_pipeline` dispatches on `mode`, validates the schema,
#   renders Markdown with the 召唤 footer, computes `citation_validity_rate`.
# - Step 4 — `merge_reviews` classifies findings; non-discriminatory DOI attribution
#   tracks `introduced_by: reviewer_name` for every ref (first-wins ordering).
#
# ## What's not shown here
#
# - Live LLM enrichment (Step 2 was hand-constructed).
# - Live DOI verification (Step 4 used empty `introduced_refs` to avoid network).
# - The publication-strategy pipeline (requires corpus; see `docs/MANUAL.md`).
# - The `paper-pdf-acquisition` cross-session handoff (separate skill).
#
# ## Try with your own data
#
# Replace `examples/demo_dataset/` with a folder of your own manuscripts +
# CSVs, then invoke `/thermal-mentor` in Claude Code for an interactive run.
