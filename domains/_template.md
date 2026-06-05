# Domain pack: <your field>

Copy this file to `domains/<your-field>.md`, fill the four slots, and tell the mentor
*"use the `<your-field>` domain pack"* (or set `MENTOR_DOMAIN_PACK=<your-field>`).
Delete the bracketed hints as you go. The kernel (anomaly → hypothesis → discriminating
experiment → honest citations) does not change — you are only swapping vocabulary.

## research_directions

[3–6 active sub-fields a researcher might want direction on. One short line each.]

- A: <…>
- B: <…>
- C: <…>

## target_journals

[The aspirational-ceiling journals in your field, strongest first. Used only for the
"where could this go" estimate, asked last to avoid framing bias.]

- <flagship>
- <strong subfield journal>
- 其他（自填）

## preserved_terms

[Methods/quantities that should stay verbatim in user-facing text — translating them would
hurt clarity. `DOI / arXiv / OpenAlex / Crossref` are preserved automatically.]

- <…>

## expectation_vocabulary

[The usual sources of "what prior theory / the standard model expects", so the mentor can fill
`expectation_basis` / `expected_from_prior_knowledge` for an anomaly.]

- <…>

---

### Worked examples (showing the kernel is field-agnostic)

> **Biology.** `expectation_basis` = "central-dogma / known pathway"; anomaly = "knockout of gene
> X *raises* product Y though the canonical pathway predicts a drop"; discriminating experiment =
> "qPCR + Western blot on the bypass pathway"; preserved_terms = IC50, qPCR, Western blot, CRISPR.

> **Economics.** `expectation_basis` = "standard supply–demand elasticity"; anomaly = "price rises
> yet quantity sold rises across the panel"; discriminating experiment = "instrumental-variable
> regression separating a demand shock from a Giffen effect"; preserved_terms = GDP, elasticity,
> IV, DiD.
