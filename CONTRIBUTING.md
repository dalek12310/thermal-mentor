# Contributing to thermal-mentor

First — thanks for considering a contribution. Below are the conventions this project follows.

## Quick start

1. Fork the repo + clone your fork
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Install dev deps: `pip install -e ".[test]"`
4. Make your changes
5. Run tests: `pytest tests/ -v`
6. Commit + push + open a PR

## Design philosophy

thermal-mentor is opinionated:

1. **Anti-empiricism in citations** — every reference must be verifiable via DOI or local citekey. The `verifier_error` vs `not_found` distinction is deliberate; don't merge them.
2. **人话 hard rule** — user-facing strings (AskUserQuestion, Markdown) are plain language. Internal codenames (`mode_0`, `anomaly_brief`, `L1/L3`) belong in code/comments only.
3. **Reflective routing** — the skill scans data BEFORE asking intent. If you add a new mode, follow the Step 0/0.5/1 pattern.
4. **Non-discriminatory attribution** — multi-reviewer outputs never discriminate by reviewer identity. (Technically: the merge uses first-wins ordering when the same DOI is introduced by multiple reviewers — no reviewer is flagged "high risk" by default.) See `references/cross-review-protocol.md`.

## Code conventions

- **Python 3.10+** — use modern type hints (`list[X]`, `dict[K, V]`, `X | None`)
- **No emojis in code or docs** (unless explicitly part of user-visible Markdown rendering)
- **No `print()` for debug** — use `logging` or remove before commit
- **No comments restating WHAT the code does** — comments explain WHY
- **Module docstring** must reference relevant spec section if applicable

## Test conventions

- New scripts/modules must come with unit tests in `tests/`
- Tests should NOT require live network — use `monkeypatch` on `httpx` calls
- Tests should NOT require a corpus (the public release doesn't ship one)
- Fixture data goes in `tests/fixtures/sample_dataset/` (generic synthetic)
- Test naming: `test_<function_name>_<scenario>.py`

## Pull request checklist

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] New code is tested
- [ ] Touched modules' docstrings updated
- [ ] Relevant `references/*.md` updated if behavior changes user-facing flow
- [ ] `CHANGELOG.md` updated under "Unreleased" section
- [ ] No regressions on existing tests
- [ ] No `print` debug statements or commented-out code

## Adding a new DOI verification source

1. Add wrapper function `<source>_lookup(doi, timeout) -> SourceLookupResult` in `scripts/doi_verify_multisource.py`
2. Register in `_build_chain()` with appropriate `is_authoritative_for_existence` flag
3. Add monkeypatched unit test (see `test_openalex_lookup_found` for reference)
4. Document in `docs/MANUAL.md` Section 9 + `references/cross-review-protocol.md`

## Adding a new mode 0 metric

1. Add pure function `compute_<metric>(payload) -> float` in `scripts/eval_runner.py`
2. Add unit test in `tests/test_mode_0_metrics.py`
3. Document the metric semantic in `docs/MANUAL.md` Section 6

## Reporting issues

Use the issue templates in `.github/ISSUE_TEMPLATE/`. Include:
- OS + Python version
- Steps to reproduce
- Full traceback (not just the last line)
- Env var values (sanitize emails/keys)

## Asking design questions

Open a GitHub Discussion. Tag with `design`. Reference the relevant `references/*.md` design doc you're questioning.

## License

By contributing, you agree your code is released under MIT (the project license).
