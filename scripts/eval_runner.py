"""eval_runner — Mode 0 (data-first) metric helpers.

Public release stub. The full v0.1.3 eval harness is corpus-dependent (loads
golden_set/queries.yaml and runs hybrid_retrieve + live_search). That harness
is omitted from the public release because it requires user-specific corpus
data that is not redistributable.

The four pure helper functions below are corpus-agnostic and are used by the
mode 0 metrics tests:

- compute_anomaly_recall_rate
- compute_hypothesis_completeness
- compute_existing_data_answerable_rate
- compute_false_anomaly_rate
"""
from __future__ import annotations


def compute_anomaly_recall_rate(
    surfaced: list[str],
    ground_truth: list[str],
    threshold: float = 0.5,
) -> float:
    """Fraction of ground_truth anomalies surfaced by mentor (fuzzy text match).

    Uses symmetric keyword overlap normalized by ``min(|gt|, |s|)`` so that
    a short surfaced phrase can match a longer ground-truth description when
    the short phrase is a high-coverage subset.
    """
    if not ground_truth:
        return 1.0
    matched = 0
    for gt in ground_truth:
        gt_keywords = set(gt.lower().split())
        for s in surfaced:
            s_keywords = set(s.lower().split())
            denom = max(min(len(gt_keywords), len(s_keywords)), 1)
            overlap = len(gt_keywords & s_keywords) / denom
            if overlap >= threshold:
                matched += 1
                break
    return round(matched / len(ground_truth), 3)


def compute_hypothesis_completeness(payload: dict) -> float:
    """Mean candidate hypothesis count per anomaly."""
    anomalies = payload.get("anomalies", [])
    if not anomalies:
        return 0.0
    counts: dict[str, int] = {a["anomaly_id"]: 0 for a in anomalies}
    for h in payload.get("hypotheses", []):
        aid = h.get("anomaly_id", "")
        if aid in counts:
            counts[aid] += 1
    return round(sum(counts.values()) / len(counts), 3)


def compute_existing_data_answerable_rate(payload: dict) -> float:
    """Fraction of experiments answerable by existing data (no new exp/DFT needed)."""
    exps = payload.get("experiments", [])
    if not exps:
        return 0.0
    n_existing = sum(1 for e in exps if e.get("answerable_by") == "existing_data")
    return round(n_existing / len(exps), 3)


def compute_false_anomaly_rate(
    surfaced: list[str],
    known_phenomena: list[str],
    threshold: float = 0.5,
) -> float:
    """Fraction of surfaced anomalies that match known (non-surprising) phenomena.

    Symmetric to ``compute_anomaly_recall_rate`` — normalizes by
    ``min(|known|, |surfaced|)``.
    """
    if not surfaced:
        return 0.0
    n_false = 0
    for s in surfaced:
        s_keywords = set(s.lower().split())
        for k in known_phenomena:
            k_keywords = set(k.lower().split())
            denom = max(min(len(k_keywords), len(s_keywords)), 1)
            overlap = len(k_keywords & s_keywords) / denom
            if overlap >= threshold:
                n_false += 1
                break
    return round(n_false / len(surfaced), 3)
