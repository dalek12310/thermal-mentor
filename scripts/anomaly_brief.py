"""anomaly_brief — cwd scanner + CSV structured preprocessing + LLM anomaly extract.

Spec ref: 2026-05-25-thermal-mentor-v0.1.3 Section 2.2

Extends manuscript_brief.py read path with CSV/table structured detection +
anomaly enumeration prompt. Outputs data_brief.json for mode 0 pipeline.

Reproducibility note (Section 3.3.1):
  data_brief_hash is computed via _compute_data_brief_hash, which hashes ONLY
  the scanner-determined invariant subset (HASH_PAYLOAD_KEYS): files_found,
  scanner_manifest, csv_summaries, text_files_content. LLM-enriched fields
  (central_claims / performance_numbers / candidate_anomalies / materials_system
  / manuscript_stage) are non-deterministic given the same input and are NOT
  hashed here -- model-side reproducibility is captured separately via
  reproducibility.model_id and system_prompt_hash. This ensures that
  build_data_brief (full pipeline) and build_data_brief_scaffold (scanner-only)
  produce the SAME data_brief_hash for the same cwd snapshot, satisfying the
  v0.1.3 spec lock that "same scanner inputs -> same hash".
"""
from __future__ import annotations

import csv as csv_module
import hashlib
import json
from pathlib import Path
from typing import Any

SUPPORTED_EXTENSIONS = {".docx", ".pdf", ".md", ".txt", ".csv", ".xlsx"}

# Scanner-determined invariant fields used to compute data_brief_hash.
# LLM-enriched fields are intentionally excluded; see module docstring.
HASH_PAYLOAD_KEYS = ("files_found", "scanner_manifest", "csv_summaries", "text_files_content")


def _canonical_hash_payload(brief: dict) -> dict:
    """Extract scanner-determined invariant subset for data_brief_hash computation.

    LLM-enriched fields (central_claims, candidate_anomalies, materials_system,
    manuscript_stage) are excluded -- they're non-deterministic given the same
    input and are tracked via reproducibility.model_id / system_prompt_hash
    separately.

    Spec ref: Section 3.3.1 reproducibility lock -- data_brief_hash MUST be
    deterministic given cwd snapshot, regardless of which code path (CLI
    scaffold or mentor session full pipeline) produced the brief.
    """
    return {k: brief.get(k) for k in HASH_PAYLOAD_KEYS if k in brief}


def _stringify_keys(obj):
    """Recursively coerce non-str dict keys to str. Real-world CSVs can produce
    None keys via DictReader when the header row has empty fields, which breaks
    json.dumps(sort_keys=True). Stringifying preserves the invariant.
    """
    if isinstance(obj, dict):
        return {(str(k) if k is not None else ""): _stringify_keys(v)
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_keys(x) for x in obj]
    return obj


def _compute_data_brief_hash(brief: dict) -> str:
    """sha256 of canonical JSON over the hash-payload subset.

    None-keyed dicts from malformed CSVs are stringified to "" so sort_keys
    doesn't crash on TypeError. default=str handles non-JSON-native values
    (Path objects, NaN etc). Determinism: scan_cwd uses sorted rglob.
    """
    canonical = json.dumps(
        _stringify_keys(_canonical_hash_payload(brief)),
        sort_keys=True, ensure_ascii=False, default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_cwd(cwd: Path) -> list[dict]:
    """Scan cwd for supported files. Returns list of {path, type, sha256, size_bytes}."""
    cwd = Path(cwd).resolve()
    out: list[dict] = []
    for p in sorted(cwd.rglob("*")):
        # Skip Word/PowerPoint/Excel lock files (~$... created when doc is open in Office)
        if p.name.startswith("~$"):
            continue
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            out.append({
                "path": str(p),
                "type": p.suffix.lower().lstrip("."),
                "sha256": _sha256(p),
                "size_bytes": p.stat().st_size,
            })
    return out


def build_scanner_manifest(cwd: Path) -> dict:
    """Build reproducibility manifest for cwd scan.

    Manifest hash = sha256 of sorted (path, sha256) tuples.
    """
    cwd = Path(cwd).resolve()
    files = scan_cwd(cwd)
    pairs = sorted([(f["path"], f["sha256"]) for f in files])
    manifest_hash = hashlib.sha256(
        json.dumps(pairs, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "cwd": str(cwd),
        "files": files,
        "manifest_hash": manifest_hash,
        "scanner_version": "0.1.3",
    }


def detect_monotonic_trend(values: list[float]) -> str:
    """Detect monotonic trend in a sequence of numeric values.

    Returns: 'monotonic_increase' / 'monotonic_decrease' / 'non_monotonic' / 'constant'
    """
    if len(values) < 2:
        return "constant"
    diffs = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    if all(d > 0 for d in diffs):
        return "monotonic_increase"
    if all(d < 0 for d in diffs):
        return "monotonic_decrease"
    if all(d == 0 for d in diffs):
        return "constant"
    return "non_monotonic"


def summarize_csv(csv_path: Path, max_rows: int = 20) -> dict:
    """Structured preprocessing of a CSV file.

    For each numeric column, compute monotonic trend.
    Returns capped table summary suitable for LLM input (first max_rows + statistics).

    Spec ref: Section 2.2 — observed_trend filled by structured detection,
    not LLM, to control false_anomaly_rate.
    """
    rows: list[dict[str, str]] = []
    # Try UTF-8 (with BOM), then GB18030 (Chinese Windows default), then latin-1 fallback.
    # Real-world scientific CSVs from Excel on Chinese Windows are often GB18030.
    for enc in ("utf-8-sig", "gb18030", "latin-1"):
        try:
            with csv_path.open(encoding=enc, newline="") as f:
                reader = csv_module.DictReader(f)
                rows = []
                for row in reader:
                    rows.append(row)
                    if len(rows) >= max_rows + 1:
                        break
            break  # successfully read
        except UnicodeDecodeError:
            continue
    if not rows:
        return {"columns": {}, "row_count": 0, "first_rows": []}

    columns_info: dict[str, dict[str, Any]] = {}
    for col in rows[0].keys():
        raw_vals = [r.get(col, "") for r in rows[:max_rows]]
        numeric_vals: list[float] = []
        for v in raw_vals:
            try:
                numeric_vals.append(float(v))
            except (ValueError, TypeError):
                continue
        info: dict[str, Any] = {"raw_sample": raw_vals[:5]}
        if len(numeric_vals) == len(raw_vals) and len(numeric_vals) >= 2:
            info["numeric"] = True
            info["trend"] = detect_monotonic_trend(numeric_vals)
            info["min"] = min(numeric_vals)
            info["max"] = max(numeric_vals)
            info["range_ratio"] = (
                (info["max"] - info["min"]) / abs(info["min"])
                if info["min"] != 0 else None
            )
        else:
            info["numeric"] = False
        columns_info[col] = info

    return {
        "columns": columns_info,
        "row_count": len(rows),
        "first_rows": rows[:max_rows],
    }


import sys

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from manuscript_brief import read_text  # noqa: E402


def dedupe_candidates(
    central_claims: list[dict],
    candidate_anomalies: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Dedupe across central_claims and candidate_anomalies.

    Dedup key: (source_file + quote_line) for central;
               (quote_source) for anomalies (already 'file:line' form).

    Anomaly优先 — if same quote appears in both, drop central, keep anomaly.

    Spec ref: Section 2.2 Step A.5
    """
    anomaly_keys = set()
    for a in candidate_anomalies:
        key = a.get("quote_source", "")
        if key:
            anomaly_keys.add(key)

    central_out = []
    for c in central_claims:
        src = c.get("source_file", "")
        line = c.get("quote_line", "")
        key = f"{src}:{line}"
        if key in anomaly_keys:
            continue  # 同一 quote 已在 anomaly, drop central
        central_out.append(c)

    return central_out, candidate_anomalies


def _llm_extract_anomalies(
    cwd: Path,
    scanner_manifest: dict,
    csv_summaries: dict[str, dict],
    text_files_content: dict[str, str],
) -> dict:
    """Call LLM (Claude) to extract anomalies from capped CSV summary + text content.

    In production: this is invoked via Claude Code Skill subagent (no direct API).
    In tests: monkeypatched.

    Returns dict with: central_claims, performance_numbers, candidate_anomalies,
                       materials_system, manuscript_stage.
    """
    raise NotImplementedError(
        "_llm_extract_anomalies is called by SKILL.md mentor session, "
        "not directly from Python. Tests monkeypatch this."
    )


def build_data_brief(cwd: Path) -> dict:
    """Build complete data_brief.json for mode 0.

    Pipeline:
    1. scan_cwd + build scanner_manifest (file hashes)
    2. For .csv/.xlsx: structured preprocessing (summarize_csv)
    3. For text: read_text from manuscript_brief.py
    4. LLM extracts anomalies (via _llm_extract_anomalies)
    5. Dedupe across central_claims vs candidate_anomalies
    6. Compute data_brief_hash via _compute_data_brief_hash
       (scanner-determined invariant subset only; see HASH_PAYLOAD_KEYS).

    Output brief includes csv_summaries + text_files_content alongside the
    LLM-enriched fields so the persisted JSON is fully self-describing and the
    hash matches what build_data_brief_scaffold produces for the same cwd
    (D6/F7 reproducibility lock, Section 3.3.1).
    """
    cwd = Path(cwd).resolve()
    scanner_manifest = build_scanner_manifest(cwd)

    csv_summaries: dict[str, dict] = {}
    text_files_content: dict[str, str] = {}
    for f in scanner_manifest["files"]:
        p = Path(f["path"])
        if f["type"] in ("csv",):
            csv_summaries[f["path"]] = summarize_csv(p)
        elif f["type"] in ("xlsx",):
            csv_summaries[f["path"]] = {"_note": "xlsx parsing TBD via pandas in production"}
        elif f["type"] in ("docx", "pdf", "md", "txt"):
            try:
                text_files_content[f["path"]] = read_text(p)
            except Exception:
                # Real-world data may contain corrupt PDFs, password-locked docx,
                # encoding mismatches, etc. Don't crash the whole brief — log empty.
                text_files_content[f["path"]] = ""

    llm_out = _llm_extract_anomalies(cwd, scanner_manifest, csv_summaries, text_files_content)

    central_out, anomalies_out = dedupe_candidates(
        llm_out.get("central_claims", []),
        llm_out.get("candidate_anomalies", []),
    )

    brief = {
        "files_found": scanner_manifest["files"],
        "csv_summaries": csv_summaries,
        "text_files_content": text_files_content,
        "central_claims": central_out,
        "performance_numbers": llm_out.get("performance_numbers", []),
        "candidate_anomalies": anomalies_out,
        "materials_system": llm_out.get("materials_system", ""),
        "manuscript_stage": llm_out.get("manuscript_stage", ""),
        "scanner_manifest": scanner_manifest,
    }

    brief["data_brief_hash"] = _compute_data_brief_hash(brief)
    return brief


def build_data_brief_scaffold(cwd: Path, include_text: bool = False) -> dict:
    """Build a scanner-only scaffold for data_brief.json.

    Mentor session must enrich this with LLM-extracted fields before using
    as a complete data_brief. Spec ref: §Task 14 SKILL.md Step 0 architecture.

    include_text only controls JSON output verbosity (whether text content is
    written to the persisted scaffold file). The data_brief_hash is ALWAYS
    computed over the fully-populated scanner snapshot (including text files)
    so that scaffold-with-include-text=False and scaffold-with-include-text=True
    produce IDENTICAL hashes for the same cwd, AND so the scaffold hash matches
    the hash that build_data_brief produces for the same cwd.

    D6/F7 reproducibility lock, Section 3.3.1.
    """
    cwd = Path(cwd).resolve()
    scanner_manifest = build_scanner_manifest(cwd)

    csv_summaries: dict[str, dict] = {}
    text_files_content: dict[str, str] = {}
    for f in scanner_manifest["files"]:
        p = Path(f["path"])
        if f["type"] == "csv":
            csv_summaries[f["path"]] = summarize_csv(p)
        elif f["type"] == "xlsx":
            csv_summaries[f["path"]] = {"_note": "xlsx parsing TBD via pandas in production"}
        elif f["type"] in ("docx", "pdf", "md", "txt"):
            # Always read for hash consistency; the include_text flag only
            # governs whether the content lands in the output JSON.
            try:
                text_files_content[f["path"]] = read_text(p)
            except Exception:
                # Real-world data may contain corrupt PDFs, password-locked docx,
                # encoding mismatches, etc. Don't crash the whole brief — log empty.
                text_files_content[f["path"]] = ""

    # Compute hash over the fully-populated scanner snapshot (invariant w.r.t.
    # include_text and w.r.t. whether downstream LLM enrichment has happened).
    hash_input = {
        "files_found": scanner_manifest["files"],
        "csv_summaries": csv_summaries,
        "text_files_content": text_files_content,
        "scanner_manifest": scanner_manifest,
    }
    data_brief_hash = _compute_data_brief_hash(hash_input)

    scaffold = {
        "_note": (
            "scanner-only scaffold; LLM-extracted fields "
            "(central_claims/performance_numbers/candidate_anomalies/"
            "materials_system/manuscript_stage) must be filled by mentor "
            "session reasoning before treating as complete data_brief."
        ),
        "files_found": scanner_manifest["files"],
        "csv_summaries": csv_summaries,
        "text_files_content": text_files_content if include_text else {},
        "central_claims": [],
        "performance_numbers": [],
        "candidate_anomalies": [],
        "materials_system": "",
        "manuscript_stage": "",
        "scanner_manifest": scanner_manifest,
        "data_brief_hash": data_brief_hash,
    }
    return scaffold


def main() -> None:
    """CLI: python anomaly_brief.py <cwd> --out <data_brief.json> [--include-text]

    Produces scanner-only scaffold; mentor session must enrich LLM fields.
    """
    import argparse
    p = argparse.ArgumentParser(
        description="Scan cwd, produce data_brief.json scaffold for mentor session enrichment."
    )
    p.add_argument("cwd", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--include-text", action="store_true",
                   help="Include text_files_content (.docx/.pdf/.md/.txt). "
                        "Skipped by default to keep scaffold small.")
    args = p.parse_args()

    scaffold = build_data_brief_scaffold(args.cwd, include_text=args.include_text)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(scaffold, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(
        f"[saved] {args.out} "
        f"(scaffold: {len(scaffold['files_found'])} files scanned, "
        f"data_brief_hash={scaffold['data_brief_hash'][:16]}..., "
        f"include_text={args.include_text})"
    )
    print("[note] mentor session must enrich LLM fields before using as complete data_brief")


if __name__ == "__main__":
    main()
