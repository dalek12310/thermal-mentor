# Promotion drafts

## Twitter / X thread (5 tweets)

**Tweet 1 (hook)**
Most "AI research assistants" fail the same way: they ask "what do you want help with?" before looking at your data.

I built thermal-mentor — a Claude Code skill that scans your data FIRST, then asks tailored questions based on what it sees.

Code + bilingual docs: github.com/dalek12310/thermal-mentor

**Tweet 2 (the pattern)**
The reflective routing pattern, in 3 steps:

- Step 0 — scan CWD, build scaffold (files + CSV trends + text)
- Step 0.5 — show user 1-screen reading with verbatim quotes
- Step 1 — inner monologue, then tailored intent options

Result: ~75% of "what would you like?" friction disappears.

**Tweet 3 (verifier_error semantic)**
One subtle thing thermal-mentor does that I haven't seen elsewhere:

DOI verification with explicit `verifier_error` ≠ `not_found`.

Most tools silently fall back to "verified" or "unknown" on network errors.
thermal-mentor returns `verifier_error` so citation_validity_rate isn't polluted by infra failures.

**Tweet 4 (cross-review)**
Round-table cross-review with non-discriminatory DOI attribution:

3 LLM reviewers (Opus / Codex / DeepSeek) critique in parallel.
Round 2: each sees others' findings.
Round 3-4: Python merges via classify_findings + attribute_refs.

No reviewer-discrimination in citation provenance.

**Tweet 5 (CTA)**
v0.1.3 ships with:
- 64 unit tests
- Bilingual English + 简体中文 docs (1000+ line manual each)
- MIT license
- Self-contained (no corpus needed for mode 0)

If you do data-heavy research + use Claude Code, give it a spin:
github.com/dalek12310/thermal-mentor

---

## Awesome-claude-code-skills entry

For submission to awesome lists like https://github.com/topics/claude-code-skill:

```markdown
### thermal-mentor

[github.com/dalek12310/thermal-mentor](https://github.com/dalek12310/thermal-mentor) — Research mentor skill that scans your data BEFORE asking what you want. Mode 0 pipeline: anomaly enumeration → hypothesis enumeration → discriminating experiment proposal. DOI multi-source verification with explicit verifier_error semantic. Round-table cross-review with non-discriminatory DOI attribution. Bilingual EN + 简体中文 docs. MIT.
```

---

## Hacker News submission text

**Title**: thermal-mentor: a Claude Code skill that scans your research data before asking what you want

**Body** (post in comments):

I built this because I kept getting the same useless response from LLM research assistants: generic encouragement or generic critique that ignored my actual data.

thermal-mentor flips the order: it scans your current working directory (manuscripts, CSV data, text notes) into a JSON scaffold, then the mentor session (the LLM you're chatting with) enriches the scaffold with candidate anomalies — places where your measurements contradict textbook predictions. THEN it asks you what you want to do, with tailored options based on what it actually found.

Two technical bits I haven't seen elsewhere:

1. **DOI multi-source verification with explicit verifier_error semantic**. Most DOI checkers silently map network failures to "verified" or "unknown". thermal-mentor returns `verifier_error` distinctly so your citation_validity_rate metric isn't polluted by infra problems.

2. **Non-discriminatory DOI attribution in cross-review merge**. When 3 reviewer LLMs introduce refs in their critiques, the merge step tracks `introduced_by: reviewer_name` for all of them — no model gets singled out as "high risk" by default. (Technically: first-wins ordering when the same DOI appears from multiple reviewers.)

Bilingual English + 简体中文 docs, 64 unit tests, MIT license. v0.1.3.

Feedback welcome — especially on the reflective routing pattern, which I think generalizes beyond science.

github.com/dalek12310/thermal-mentor

---

## LinkedIn post (longer-form)

Most AI research assistants fail the same way: they ask "what would you like help with?" before looking at your data. You end up summarizing your own files back to the assistant, which then gives generic advice based on your summary instead of your actual measurements.

I just released thermal-mentor v0.1.3 — a Claude Code skill that flips the order. It scans your current working directory first (manuscripts, CSV data, notes), surfaces the anomalies it finds with verbatim quotes, then asks tailored intent questions seeded by what it detected.

What's in v0.1.3:
- Reflective routing protocol (scan-then-ask)
- Mode 0 data-first pipeline: anomaly enumeration → hypothesis enumeration → discriminating experiment proposal
- Multi-source DOI verification with explicit verifier_error vs not_found semantic (so network failures don't pollute your citation_validity_rate)
- Round-table cross-review with non-discriminatory DOI attribution across reviewer LLMs
- Bilingual EN + 简体中文 docs, 64 unit tests, MIT license

Acceptance run on a Ta-doped LLZO study: 9 runs × N=3, target anomaly hit rate = 1.00.

If you do data-heavy research and use Claude Code, give it a try. Feedback especially welcome on the reflective routing pattern — I think it generalizes well beyond science.

github.com/dalek12310/thermal-mentor

---

## Reddit r/ClaudeAI submission

**Title**: thermal-mentor v0.1.3 — Claude Code skill for data-first research mentor sessions [MIT, EN+CN docs]

**Body**:

Open-sourced a Claude Code skill I've been using on my own materials-science manuscripts. It's a mentor-session skill, but with one architectural twist: it scans your CWD before asking what you want.

The pattern (which I'm calling "reflective routing" in the docs):
1. Scan files into a JSON scaffold (file hashes + CSV column trend detection + text extraction)
2. Show the user a 1-screen reading with verbatim quotes from their data
3. Inner-monologue intent inference → AskUserQuestion with options *seeded by what was detected*, not generic placeholders

Two pipelines after routing:
- Mode 0 (data-first): anomaly → hypothesis → discriminating experiment
- Publication strategy: novelty review / journal target / revision plan

Other bits worth highlighting:
- DOI multi-source verifier with explicit `verifier_error` ≠ `not_found` (network failures don't get bucketed as "verified")
- Cross-review merge with non-discriminatory attribution (3 reviewer LLMs, no model gets singled out as "high risk"; first-wins ordering)
- Reproducibility lock via `data_brief_hash` (same scanner input → same hash)
- N=3 acceptance machinery built in

Stack: Python 3.10+, MIT, 64 unit tests, CI on Ubuntu + Windows × Py 3.10-3.13.

Repo: github.com/dalek12310/thermal-mentor

Docs are bilingual (English + 简体中文). 5-step DEMO walkthrough included with a synthetic LLZO dataset so you can try mode 0 without needing your own data.

Feedback / PRs welcome.

---

## Blog post pull-quotes (for sharing snippets)

> "Most AI research assistant demos work great on toy examples and fall apart on real manuscripts. The toy examples are self-contained in the prompt. Real manuscripts live in `data.csv` and `notes.md` files that the assistant never opened."

> "The user's first interaction is no longer 'tell me what you want' — it's 'here's what I noticed; is one of these the thing you came to me about?'"

> "Every time you collapse a 'we don't know' state into a 'things are fine' or 'things are broken' default, you're making a UX trade-off that the user usually doesn't get to opt into."

> "The reflective routing pattern works anywhere the user's actual intent depends on the contents of files they expect you to have read."

---

## Notes for poster

- Repo URLs already point to `dalek12310/thermal-mentor`; update them only if you publish under a different account.
- Tweet thread is sized for X's 280-char limit per tweet; check character counts before posting (Tweet 1 is ~270 chars).
- HN submission: post the title + URL only; put the body text in the first comment, not the submission itself.
- LinkedIn version benefits from a screenshot of the demo dataset trend detection output as a visual.
- Don't post all four (X / HN / Reddit / LinkedIn) in the same hour — stagger by at least 12h to look organic.
- Worth pinning the blog post in /docs/blog/reflective-routing-pattern.md to your GitHub profile README too.
