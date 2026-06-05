"""Release-facing smoke tests for documented entry points."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_verifier_module_entrypoint_imports_as_package():
    """The editable package should support python -m scripts.verifier."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.verifier", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    assert "payload_file" in result.stdout


def test_mode_0_walkthrough_does_not_mark_demo_notes_missing():
    """The documented walkthrough should not flag its own demo note as missing."""
    result = subprocess.run(
        [sys.executable, "docs/notebooks/01_mode_0_walkthrough.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    assert "来源文件未找到" not in result.stdout
    assert "citation_validity_rate: 1.0" in result.stdout
