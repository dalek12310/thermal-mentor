"""Tests for mode 0 evaluation metrics."""
from __future__ import annotations

import sys
from pathlib import Path

# Make scripts/ importable (flattened release layout)
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_anomaly_recall_rate():
    """Recall = mentor surfaced anomalies ∩ ground truth / ground truth."""
    from eval_runner import compute_anomaly_recall_rate
    surfaced = ["defect_signal monotonic decrease", "dual-site occupation",
                "kappa decrease emissivity increase coupled"]
    ground_truth = ["defect_signal monotonic decrease reverse textbook",
                    "dopant dual-site reverse radius",
                    "kappa decrease emissivity increase (not specific dual-site)",
                    "mechanical properties unchanged"]
    rate = compute_anomaly_recall_rate(surfaced, ground_truth, threshold=0.5)
    # 3/4 ground truth matched (S1, S2, S3); S4 not surfaced
    assert 0.74 < rate < 0.76


def test_hypothesis_completeness_mean():
    """Mean candidate mechanisms per anomaly."""
    from eval_runner import compute_hypothesis_completeness
    payload = {
        "anomalies": [{"anomaly_id": "A1"}, {"anomaly_id": "A2"}],
        "hypotheses": [
            {"hypothesis_id": "H1a", "anomaly_id": "A1"},
            {"hypothesis_id": "H1b", "anomaly_id": "A1"},
            {"hypothesis_id": "H1c", "anomaly_id": "A1"},
            {"hypothesis_id": "H2a", "anomaly_id": "A2"},
        ],
    }
    mean = compute_hypothesis_completeness(payload)
    assert mean == 2.0  # (3 + 1) / 2


def test_existing_data_answerable_rate():
    """Fraction of experiments marked answerable_by=existing_data."""
    from eval_runner import compute_existing_data_answerable_rate
    payload = {
        "experiments": [
            {"experiment_id": "E1", "answerable_by": "existing_data"},
            {"experiment_id": "E2", "answerable_by": "new_experiment"},
            {"experiment_id": "E3", "answerable_by": "existing_data"},
            {"experiment_id": "E4", "answerable_by": "dft"},
        ],
    }
    rate = compute_existing_data_answerable_rate(payload)
    assert rate == 0.5  # 2/4
