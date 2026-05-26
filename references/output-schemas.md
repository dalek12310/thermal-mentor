# Output JSON schemas

Per mode. Every mode produces JSON first; `verifier.py` renders Markdown.

## novelty_review

```json
{
  "mode": "novelty_review",
  "verdict": {
    "one_line": "string",
    "confidence": "low | medium | high"
  },
  "claims": [
    {
      "claim_id": "C001",
      "claim_text": "string",
      "claim_type": "novelty | method | mechanism | performance | citation | limitation",
      "language": "zh | en | mixed",
      "supporting_refs": [
        {
          "ref_id": "R001",
          "ref_type": "local_citekey | doi | openalex | user_manuscript",
          "value": "citekey or DOI or 'manuscript:p3'",
          "authors_text": "Wolverton et al.",
          "year": 2024,
          "verification_status": "unset (filled by verifier)"
        }
      ],
      "novelty_flag": "novel | not_novel | incremental | uncertain",
      "closest_baseline_refs": ["R005"],
      "evidence_span": "exact quote or null",
      "confidence": "low | medium | high"
    }
  ],
  "prior_art_coverage": {
    "queries_used": ["..."],
    "sources_hit": ["OpenAlex", "Semantic Scholar", "arXiv"],
    "date_range": "2018-2026",
    "total_external_hits": 47,
    "hits_from_last_12mo": 9,
    "closest_baseline": {"doi": "10.x/y", "year": 2024}
  },
  "what_would_change_my_mind": ["if X is measured at >Y..."],
  "audit_log_id": "20260523-153012-abc123"
}
```

## highlight_mining

Same shape; `mode = "highlight_mining"`; claims focus on `claim_type = novelty | performance | mechanism`; verdict.one_line = the proposed headline.

## revision

`mode = "revision"`; claims become per-paragraph edit suggestions with `claim_type = "edit_suggestion"`; `evidence_span` is the original text; verdict.one_line summarises edit theme.

## direction_guidance

`mode = "direction_guidance"`; claims are proposed sub-questions; `claim_type = "research_proposal"`; `closest_baseline_refs` show what work would block / inspire each direction.

## corpus_query

`mode = "corpus_query"`; minimal — just `claims` listing matching papers + 1-line summary each.
