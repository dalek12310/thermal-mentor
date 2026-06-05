# Domain pack: thermal / condensed-matter / materials science

The project's original and best-validated field. This is the **default** active pack.
It supplies the four field-specific slots the kernel asks for.

## research_directions

Used by the publication "direction" mode (Level-2 Q1 in `references/ask-first-prompts.md`):

- A: DFT phonon + ML potentials
- B: thermoelectric
- C: interface + 2D
- D: topological / chiral phonon
- E: phonon-induced superconductivity

## target_journals

Used as the "ceiling estimate" option in novelty / highlight / revision modes (asked **last**,
to avoid framing bias):

- Nat Mater
- Nature Communications
- Advanced Materials
- JACS / ACS Nano / Nano Lett
- 其他（自填）

## preserved_terms

Standard physics / characterization terms kept verbatim in user-facing text (translating them
would harm clarity; the mentor uses a Chinese connector when needed, e.g. "EXAFS 看配位数"):

- DFT / DFPT / AIMD / MLIP / TDEP / SCPH
- XAFS / EXAFS / XANES / XPS / EPR / Raman / TEM / STEM / TDTR
- phonon / Phonon Hall / electron-phonon / e-ph
- κ (thermal conductivity) / κ_lat / κ_e / ε (permittivity / Seebeck) / ZT / TBC
- Kröger-Vink / Shannon radii / Wigner / Boltzmann

(`DOI / arXiv / OpenAlex / Crossref / Semantic Scholar / WoS` are preserved in every pack —
they are infrastructure terms, not domain terms.)

## expectation_vocabulary

Typical sources of the "what prior theory / the textbook expects" baseline — these seed the
anomaly `expectation_basis` and `expected_from_prior_knowledge` fields:

- defect-chemistry textbook (e.g. aliovalent substitution → charge-compensating defects)
- Shannon ionic radii (size mismatch → lattice parameter trend)
- phonon-defect scaling (mass/strain disorder → κ_lat reduction)
- Kröger-Vink defect equilibria
- Boltzmann transport / Wigner formalism expectations

## optional local corpus

This pack pairs with the optional citation corpus loaded via `SCIENCE_MENTOR_CORPUS`
(`distillation_corpus_v2.csv` + `retraction_blacklist.yaml` + the ~48-researcher anchor
registry). Those data files are genuinely thermal and ship with the corpus bundle, not the
public skill — keeping them thermal is honest and intended.
