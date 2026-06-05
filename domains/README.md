# Domain packs

The mentor's **kernel** (scan → anomaly → hypothesis → discriminating experiment → honest
citation verification → cross-review) carries no domain logic. Everything field-specific —
the research-direction menu, the target-journal ceiling list, the preserved technical-term
whitelist, and the example vocabulary for "what the textbook/prior theory expects" — lives
here, in a swappable **domain pack**.

## How it works

- The active pack defaults to [`thermal.md`](thermal.md) (condensed-matter / materials science —
  the project's original and best-validated field).
- To work in another field, copy [`_template.md`](_template.md) to `domains/<your-field>.md`,
  fill in the four slots, and tell the mentor *"use the `<your-field>` domain pack"* at the start
  of the session (or set `MENTOR_DOMAIN_PACK=<your-field>` in your shell before launching).
- If no pack matches, the mentor falls back to domain-neutral phrasing (the template's
  placeholders) — the discovery + verification kernel still runs unchanged.

## What a pack provides

| Slot | Used by | Example (thermal) |
|---|---|---|
| `research_directions` | publication "direction" mode (`references/ask-first-prompts.md` Level-2) | DFT phonon + ML potentials; thermoelectric; … |
| `target_journals` | novelty/highlight/revision "ceiling" question | Nat Mater; Nature Communications; Adv Mater; … |
| `preserved_terms` | plain-language rule (`references/user-facing-language.md`) — terms kept verbatim | DFT, EXAFS, phonon, ZT, Kröger-Vink, … |
| `expectation_vocabulary` | seeds the anomaly `expectation_basis` / `expected_from_prior_knowledge` fields | defect-chemistry textbook; Shannon radii; phonon-defect scaling |

A pack is **data, not logic** — swapping it never touches `scripts/`. The shipped JSON-schema
examples in `references/output-schemas-data-first.md` use the thermal pack's vocabulary purely as
illustration; the field *names* are domain-neutral.
