"""Tests for anomaly_brief.py cwd scanner + structured CSV preprocessing."""
from __future__ import annotations

import sys
from pathlib import Path

# Make scripts/ importable (flattened release layout)
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import pytest


def test_scan_cwd_finds_supported_files(sample_dataset_dir):
    from anomaly_brief import scan_cwd
    files = scan_cwd(sample_dataset_dir)
    paths = [f["path"] for f in files]
    assert any("notes.txt" in p for p in paths)
    assert any("data.csv" in p for p in paths)


def test_scan_cwd_filters_by_extension(tmp_path):
    """Scanner should ignore non-supported extensions (.pyc / .log / etc)."""
    (tmp_path / "good.txt").write_text("text content", encoding="utf-8")
    (tmp_path / "bad.pyc").write_bytes(b"\x00\x00")
    (tmp_path / "bad.log").write_text("log lines", encoding="utf-8")
    from anomaly_brief import scan_cwd
    files = scan_cwd(tmp_path)
    paths = [f["path"] for f in files]
    assert any("good.txt" in p for p in paths)
    assert not any("bad.pyc" in p for p in paths)
    assert not any("bad.log" in p for p in paths)


def test_scan_cwd_includes_file_hash(sample_dataset_dir):
    """Each file entry must include sha256 hash for reproducibility."""
    from anomaly_brief import scan_cwd
    files = scan_cwd(sample_dataset_dir)
    for f in files:
        assert "sha256" in f
        assert len(f["sha256"]) == 64


def test_build_scanner_manifest_stable_across_calls(sample_dataset_dir):
    """Same cwd + same files -> identical scanner_manifest hash."""
    from anomaly_brief import build_scanner_manifest
    m1 = build_scanner_manifest(sample_dataset_dir)
    m2 = build_scanner_manifest(sample_dataset_dir)
    assert m1["manifest_hash"] == m2["manifest_hash"]
    assert m1["cwd"] == str(sample_dataset_dir.resolve())


def test_detect_monotonic_trend_decreasing():
    from anomaly_brief import detect_monotonic_trend
    assert detect_monotonic_trend([1.0, 0.78, 0.55, 0.35]) == "monotonic_decrease"


def test_detect_monotonic_trend_increasing():
    from anomaly_brief import detect_monotonic_trend
    assert detect_monotonic_trend([0.71, 0.74, 0.78, 0.83]) == "monotonic_increase"


def test_detect_monotonic_trend_non_monotonic():
    from anomaly_brief import detect_monotonic_trend
    assert detect_monotonic_trend([6.95, 6.92, 6.85, 6.81]) == "monotonic_decrease"
    assert detect_monotonic_trend([1.0, 1.2, 0.9, 1.1]) == "non_monotonic"


def test_summarize_csv_returns_capped_summary(sample_dataset_dir):
    from anomaly_brief import summarize_csv
    csv_path = sample_dataset_dir / "data.csv"
    summary = summarize_csv(csv_path)
    assert "columns" in summary
    assert "property_X" in summary["columns"]
    assert summary["columns"]["property_X"]["trend"] == "monotonic_decrease"
    assert summary["columns"]["property_Y"]["trend"] == "monotonic_increase"
    assert summary["columns"]["property_Z"]["trend"] == "monotonic_decrease"


def test_dedupe_candidate_anomalies():
    from anomaly_brief import dedupe_candidates
    raw_central = [
        {"claim_text": "X 单调下降", "source_file": "notes.txt", "quote_line": 4},
    ]
    raw_anomalies = [
        {"anomaly_id": "A1", "observation_short": "X 单调下降",
         "quote_source": "notes.txt:4", "quote_verbatim": "..."},
    ]
    central_out, anomalies_out = dedupe_candidates(raw_central, raw_anomalies)
    # Same quote in both lists, anomaly wins, central dropped
    assert len(central_out) == 0
    assert len(anomalies_out) == 1


def test_build_data_brief_includes_hash(sample_dataset_dir, monkeypatch):
    """build_data_brief output must include data_brief_hash for reproducibility."""
    def fake_llm_extract(cwd, scanner_manifest, csv_summaries, text_files_content):
        return {
            "central_claims": [],
            "performance_numbers": [
                {"what": "property_X", "value": "0.35-1.00", "units": "a.u.",
                 "source": "data.csv", "quote_verbatim": "0.35-1.00"}
            ],
            "candidate_anomalies": [
                {
                    "anomaly_id": "A1",
                    "observation_short": "X monotonic decrease",
                    "observed_trend": "monotonic_decrease",
                    "expected_source_type": "textbook baseline",
                    "quote_verbatim": "property X 0/2/4/6% monotonic decrease",
                    "quote_source": "notes.txt:4",
                    "quote_hash": "sha256:" + "0" * 64,
                    "expected_textbook_short": "self-compensation predicts flat",
                    "mentor_inference": "self-compensation only explains 'no increase'",
                    "surprise_score": "high",
                }
            ],
            "materials_system": "doped-test-system",
            "manuscript_stage": "draft+data",
        }

    from anomaly_brief import build_data_brief
    monkeypatch.setattr("anomaly_brief._llm_extract_anomalies", fake_llm_extract)

    brief = build_data_brief(sample_dataset_dir)
    assert "data_brief_hash" in brief
    assert "scanner_manifest" in brief
    assert "candidate_anomalies" in brief
    assert brief["candidate_anomalies"][0]["anomaly_id"] == "A1"


def test_data_brief_hash_stable_for_same_input(sample_dataset_dir, monkeypatch):
    """Same cwd + same LLM output -> same data_brief_hash."""
    def fake_llm(*args, **kwargs):
        return {
            "central_claims": [], "performance_numbers": [],
            "candidate_anomalies": [{"anomaly_id": "A1", "observation_short": "stable"}],
            "materials_system": "test", "manuscript_stage": "test",
        }
    from anomaly_brief import build_data_brief
    monkeypatch.setattr("anomaly_brief._llm_extract_anomalies", fake_llm)
    b1 = build_data_brief(sample_dataset_dir)
    b2 = build_data_brief(sample_dataset_dir)
    assert b1["data_brief_hash"] == b2["data_brief_hash"]


def test_build_data_brief_scaffold_no_llm_call(sample_dataset_dir):
    """Scaffold builder does NOT call _llm_extract_anomalies."""
    from anomaly_brief import build_data_brief_scaffold
    scaffold = build_data_brief_scaffold(sample_dataset_dir)

    # Has scaffold marker
    assert "_note" in scaffold
    assert "scanner-only scaffold" in scaffold["_note"]

    # Scanner fields populated
    assert len(scaffold["files_found"]) >= 2  # notes.txt + data.csv
    assert "scanner_manifest" in scaffold
    assert "data_brief_hash" in scaffold
    assert "csv_summaries" in scaffold
    assert any("data.csv" in p for p in scaffold["csv_summaries"].keys())

    # LLM fields empty (mentor fills later)
    assert scaffold["central_claims"] == []
    assert scaffold["performance_numbers"] == []
    assert scaffold["candidate_anomalies"] == []
    assert scaffold["materials_system"] == ""
    assert scaffold["manuscript_stage"] == ""

    # text_files_content empty by default (no --include-text)
    assert scaffold["text_files_content"] == {}


def test_cli_scaffold_writes_scanner_only_brief(tmp_path):
    """CLI smoke test: produces scaffold JSON without LLM crash."""
    import json
    import subprocess
    import sys
    from pathlib import Path

    # Create a small fixture dir with one .csv
    fix = tmp_path / "datadir"
    fix.mkdir()
    (fix / "data.csv").write_text("col1,col2\n1,2\n3,4\n", encoding="utf-8")

    out = tmp_path / "brief.json"
    script = Path(__file__).resolve().parents[1] / "scripts" / "anomaly_brief.py"

    result = subprocess.run(
        [sys.executable, str(script), str(fix), "--out", str(out)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, f"CLI failed: stderr={result.stderr}"
    assert out.exists()

    data = json.loads(out.read_text(encoding="utf-8"))
    assert "_note" in data
    assert data["central_claims"] == []
    assert "data_brief_hash" in data


# ---------------------------------------------------------------------------
# data_brief_hash invariant across code paths (round 2 review fix)
# ---------------------------------------------------------------------------

def test_scaffold_and_full_brief_have_same_hash_for_same_cwd(sample_dataset_dir, monkeypatch):
    """build_data_brief_scaffold and build_data_brief produce same data_brief_hash
    for the same cwd, regardless of LLM-enriched field differences."""
    def fake_llm(*args, **kwargs):
        return {
            "central_claims": [{"a": "non-empty"}],
            "performance_numbers": [{"x": 1}],
            "candidate_anomalies": [{"anomaly_id": "A1"}],
            "materials_system": "test_system",
            "manuscript_stage": "draft",
        }

    from anomaly_brief import build_data_brief, build_data_brief_scaffold
    monkeypatch.setattr("anomaly_brief._llm_extract_anomalies", fake_llm)

    full = build_data_brief(sample_dataset_dir)
    scaffold = build_data_brief_scaffold(sample_dataset_dir)

    assert full["data_brief_hash"] == scaffold["data_brief_hash"], (
        f"Scaffold hash {scaffold['data_brief_hash'][:16]} != "
        f"full hash {full['data_brief_hash'][:16]} - reproducibility broken"
    )


def test_scaffold_hash_independent_of_include_text_flag(sample_dataset_dir):
    """Hash should be deterministic for the cwd regardless of --include-text flag,
    which only controls JSON output verbosity."""
    from anomaly_brief import build_data_brief_scaffold
    s1 = build_data_brief_scaffold(sample_dataset_dir, include_text=False)
    s2 = build_data_brief_scaffold(sample_dataset_dir, include_text=True)
    assert s1["data_brief_hash"] == s2["data_brief_hash"]


def test_hash_excludes_llm_enriched_fields(sample_dataset_dir, monkeypatch):
    """Different LLM outputs for the same cwd should still produce the same hash."""
    from anomaly_brief import build_data_brief

    def fake_llm_a(*a, **kw):
        return {
            "central_claims": [{"claim_text": "claim A", "source_file": "x", "quote_line": 1}],
            "performance_numbers": [],
            "candidate_anomalies": [{"anomaly_id": "A1", "quote_source": "x:99"}],
            "materials_system": "sys_A", "manuscript_stage": "draft",
        }

    def fake_llm_b(*a, **kw):
        return {
            "central_claims": [{"claim_text": "claim B different", "source_file": "y", "quote_line": 2}],
            "performance_numbers": [{"x": 99}],
            "candidate_anomalies": [{"anomaly_id": "B1", "quote_source": "y:88"}],
            "materials_system": "sys_B", "manuscript_stage": "review",
        }

    monkeypatch.setattr("anomaly_brief._llm_extract_anomalies", fake_llm_a)
    brief_a = build_data_brief(sample_dataset_dir)

    monkeypatch.setattr("anomaly_brief._llm_extract_anomalies", fake_llm_b)
    brief_b = build_data_brief(sample_dataset_dir)

    # Same cwd, different LLM output -> SAME hash
    assert brief_a["data_brief_hash"] == brief_b["data_brief_hash"]
    # But the LLM fields differ
    assert brief_a["central_claims"] != brief_b["central_claims"]
