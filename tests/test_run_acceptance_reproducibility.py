"""Tests for run_acceptance.py reproducibility additions (Task 18).

Spec ref: v0.1.3 plan Section 3.3.1 reproducibility 锁定.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make scripts/ importable (flattened release layout)
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_save_run_includes_model_params(tmp_path, monkeypatch):
    """save_run JSON must include model_id/version/temperature/prompt_hash/data_brief_hash."""
    import run_acceptance
    import audit_log

    # Prevent test pollution of real audit_log JSONL file. save_run does
    # `import audit_log` inside its body — patching the module here is
    # sufficient because sys.modules caches the (now patched) reference.
    monkeypatch.setattr(audit_log, "append", lambda record: "test-aid")

    monkeypatch.setenv("CLAUDE_MODEL_ID", "claude-opus-4.7")
    monkeypatch.setenv("CLAUDE_MODEL_VERSION", "20260520")

    payload = {
        "mode": "data_first",
        "anomalies": [],
        "hypotheses": [],
        "experiments": [],
        "audit_log_id": "test-repro-001",
    }
    json_path, md_path = run_acceptance.save_run(
        payload,
        run_name="test_v0.1.3_dataonly_20260525_run1",
        out_dir=tmp_path,
        data_brief_hash="abc123def456",
        system_prompt_hash="prompt_hash_xyz",
    )
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["reproducibility"]["model_id"] == "claude-opus-4.7"
    assert data["reproducibility"]["model_version"] == "20260520"
    assert data["reproducibility"]["data_brief_hash"] == "abc123def456"
    assert data["reproducibility"]["system_prompt_hash"] == "prompt_hash_xyz"


def test_save_run_writes_separate_files_per_repeat(tmp_path, monkeypatch):
    """N=3 repeat -> 3 distinct run JSON files."""
    import run_acceptance
    import audit_log

    monkeypatch.setattr(audit_log, "append", lambda record: "test-aid")

    payload = {
        "mode": "data_first",
        "anomalies": [],
        "hypotheses": [],
        "experiments": [],
        "audit_log_id": "test-N3",
    }
    paths = []
    for i in range(1, 4):
        json_path, _ = run_acceptance.save_run(
            payload,
            run_name=f"test_v0.1.3_dataonly_20260525_run{i}",
            out_dir=tmp_path,
            data_brief_hash="same",
            system_prompt_hash="same",
        )
        paths.append(json_path)
    assert len(set(paths)) == 3, "Each repeat must produce distinct file"
    for p in paths:
        assert p.exists()


def test_read_json_file_accepts_utf8_bom(tmp_path):
    """PowerShell-written JSON may include a UTF-8 BOM."""
    import run_acceptance

    payload = tmp_path / "payload.json"
    payload.write_text('\ufeff{"mode": "data_first"}', encoding="utf-8")

    assert run_acceptance._read_json_file(payload)["mode"] == "data_first"


def test_cli_fails_gracefully_on_malformed_reproducibility_manifest(tmp_path):
    """Malformed --reproducibility-manifest -> exit 2 with clear error message."""
    import subprocess
    import sys
    from pathlib import Path

    # Create a malformed JSON
    bad_brief = tmp_path / "bad_brief.json"
    bad_brief.write_text("{this is not json", encoding="utf-8")

    # Create a minimal valid payload
    payload = tmp_path / "payload.json"
    payload.write_text(
        '{"mode": "data_first", "anomalies": [], "hypotheses": [], '
        '"experiments": [], "audit_log_id": "t"}',
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[1] / "scripts" / "run_acceptance.py"

    result = subprocess.run(
        [sys.executable, str(script), str(payload),
         "--reproducibility-manifest", str(bad_brief),
         "--run-name", "test_d2_bad"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 2, f"expected exit code 2, got {result.returncode}"
    assert "is not valid JSON" in result.stderr or "not valid JSON" in result.stderr
    assert "bad_brief.json" in result.stderr


def test_cli_fails_gracefully_on_malformed_payload(tmp_path):
    """Malformed payload_json -> exit 2 with clear error message."""
    import subprocess
    import sys
    from pathlib import Path

    bad_payload = tmp_path / "bad_payload.json"
    bad_payload.write_text("{not json either", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "scripts" / "run_acceptance.py"

    result = subprocess.run(
        [sys.executable, str(script), str(bad_payload),
         "--run-name", "test_d2_payload"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 2
    assert "not valid JSON" in result.stderr
    assert "bad_payload.json" in result.stderr
