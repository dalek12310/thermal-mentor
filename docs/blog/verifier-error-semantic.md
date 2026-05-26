# Your DOI Checker Is Lying To You: The Case For `verifier_error` ≠ `not_found`

Here's a question. Your tool checks 50 references in a manuscript draft. It reports 47 verified, 3 invalid. You feel good about it.

But during the check, OpenAlex was returning HTTP 503 for half the requests, and your tool — like most DOI checkers — silently fell back to "unknown" status, which got bucketed as "external_unverified" in the final report, which got displayed as a quiet warning the user ignored.

How many of the "47 verified" were actually verified? You don't know. The number is poisoned by infrastructure failures it doesn't acknowledge.

This is the catastrophic failure mode of conflating two completely different facts: *the DOI doesn't exist* vs *I couldn't reach the service that would tell me if it exists*. Most citation-checking tools treat them the same. They are not the same.

## The three states

A DOI verifier should return one of three things, never two:

- **`verified`** — at least one authoritative source confirmed this DOI resolves to a real publication.
- **`not_found`** — Crossref or DOI.org HEAD (the authoritative existence sources) explicitly said this DOI does not exist. The citation is wrong.
- **`verifier_error`** — the verifier could not reach any authoritative source. Network down, rate-limited, timeout, malformed JSON response, whatever. We do not know if the DOI is valid or not.

The third state is the one that gets erased. And erasing it is what breaks the integrity metric.

## Why most tools collapse the third state

I've poked at half a dozen citation checkers in the past year. Almost every one collapses `verifier_error` into either `verified` (false positive — looks like checked OK) or `unknown` (gets bucketed as "didn't fail" — same effect). The reasons are predictable:

1. **The UI is binary.** A green checkmark vs a red X. Three states need a third color, and product design didn't budget for it.
2. **The metric is `validity_rate = verified / total`.** Adding a third state forces you to decide whether `verifier_error` goes in the numerator, the denominator, or neither. Most authors just put it in `verified` to avoid scaring users.
3. **Network errors feel transient.** "We'll retry later" becomes "we'll just call it verified for now."

These are all reasonable engineering choices in isolation. They combine into a tool that lies to its users in soft, plausible-sounding ways.

## How `thermal-mentor` handles it

In `thermal-mentor`, the verifier returns a `DoiCheckResult` with one of the three states. The aggregate `citation_validity_rate` is computed as:

```python
validity_rate = verified_count / (verified_count + not_found_count)
# verifier_error refs are excluded from BOTH numerator and denominator
```

This means:
- A 50-ref draft where 47 verified, 0 not_found, and 3 verifier_error reports `citation_validity_rate = 47 / 47 = 1.0` with a footnote that *3 refs could not be checked due to verifier errors*.
- The same 50-ref draft where 47 verified and 3 not_found reports `citation_validity_rate = 47 / 50 = 0.94`.
- A 50-ref draft where 0 verified, 0 not_found, and 50 verifier_error reports `citation_validity_rate = undefined`, with a loud warning that *no reference could be checked*. The user sees this and re-runs when their network is up.

The third case is the important one. In a tool that maps `verifier_error → verified`, that same draft would report `validity_rate = 1.0` and the user would ship a manuscript without anyone noticing the verifier never worked.

## Implementation: multi-source chain

`scripts/doi_verify_multisource.py` builds a chain with 4 always-on sources + 2 env-gated sources:

Always-on:
1. **OpenAlex** — fast, free, authoritative for indexed publications
2. **Crossref** — authoritative for existence (registers all DOIs)
3. **Semantic Scholar** — useful for citation graph but rate-limited
4. **DOI.org HEAD request** — last-resort existence check

Env-gated (silently skipped when token missing):
- **Lens.org** — joins chain if `LENS_API_TOKEN` is set
- **Web of Science** — joins chain if `WOS_API_KEY` is set

Each source returns a `SourceLookupResult` with `status` ∈ `{found, not_found, error}`. The chain logic is:

- If *any* source returns `found` → result is `verified`.
- If *any* `is_authoritative_for_existence=True` source returns `not_found` → result is `not_found`. (Crossref and DOI.org HEAD have this flag.)
- Otherwise (all sources returned `error` or non-authoritative `not_found`) → result is `verifier_error`.

This is enforced by `_build_chain()` and the `is_authoritative_for_existence` flag. The flag is the thing that prevents Semantic Scholar's rate-limit-induced `not_found` from being treated as a real `not_found`.

Cache: 24h disk cache keyed by `(source, doi)`. Means a re-run against the same refs costs zero network calls if nothing was a verifier_error last time. Verifier_errors are NOT cached, so a network outage doesn't poison future runs.

## The metadata side-channel

There's one more subtle bit. In the publication-strategy mode of `thermal-mentor`, when a ref hits `verifier_error`, the verifier attaches `verifier_error_metadata` (last error, sources tried, timestamp) and the Markdown renderer adds a ⚠️ flag next to that citation. The user sees the flag in their browser and can manually re-check.

Without that side-channel, the user has to dig into the JSON to find out which refs were unverified. With it, the UI surfaces the uncertainty at the point of decision.

## What this costs

Adding the third state cost about 200 lines of Python and one extra column in the test matrix. The annoying part wasn't writing the code; it was carefully reading every existing call site for the old `verified | external_unverified` enum and deciding which ones meant "really verified" vs "couldn't tell." There were three places where the old code was returning `external_unverified` for what should have been `verifier_error`, and those were silent FPs in the validity rate. The cross-review process caught them.

That's the cost of being honest about uncertainty. It's small. The cost of *not* being honest is occasionally giving researchers false confidence that their references are real when they haven't been checked. I think that's a lot worse.

## The general principle

This is one specific case of a broader principle: **never silently fall back to a default value for something a user might depend on knowing accurately.**

Other places this comes up:

- Test results: `failed` ≠ `errored` (a test that crashed in setup is different from a test that ran and got a wrong answer).
- API status codes: `4xx` ≠ `5xx` (your bug vs their bug).
- Build status: `failed` ≠ `timed out` (your code is broken vs the runner died).

Every time you collapse a "we don't know" state into a "things are fine" or "things are broken" default, you're making a UX trade-off that the user usually doesn't get to opt into. Sometimes that's the right call (binary CI status is mostly fine). But for tools that participate in research integrity — citations, code review, security scanning — the cost of pretending to know something you don't is high enough that the third state earns its keep.

That's the whole argument. `verifier_error` is a bigger deal than it looks.

---

See `scripts/doi_verify_multisource.py` and `tests/test_doi_verify_multisource.py` in [github.com/dalek12310/thermal-mentor](https://github.com/dalek12310/thermal-mentor) for the implementation, including the monkeypatched tests that verify each chain branch (found / not_found / error) lands in the right bucket.
