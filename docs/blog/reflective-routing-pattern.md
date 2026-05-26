# Reflective Routing: A Design Pattern for AI Research Assistants That Actually Read Your Data

You've seen this scene before. You open a chat with whatever-AI-research-assistant-of-the-week, type "I'm working on a manuscript about Ta-doped LLZO, the conductivity goes up but the lattice contracts, can you help me think through this?" — and you get back a generic five-paragraph essay about ionic conductivity in garnets, followed by "Let me know if you'd like me to elaborate on any of these points."

You did not get the help you wanted.

The assistant didn't open your CSV. It didn't read your notes. It didn't notice that the activation energy column is doing something interesting. It just routed your text-string to a textbook response. You close the tab.

This essay is about a small architectural change that fixes the most common form of this failure. It's the pattern I built into `thermal-mentor`, a Claude Code skill for data-first mentor sessions on scientific manuscripts. I think it generalizes well beyond science, so it's worth describing on its own.

## The default failure mode: ask-then-act

Most "AI assistant" interfaces follow this loop:

1. User states intent.
2. Assistant clarifies intent (asks "what would you like to focus on?").
3. Assistant produces output based on stated + clarified intent.

This loop is fine when the user has a *small* intent ("rewrite this paragraph more formally") and the input is *complete in the prompt itself*. It's catastrophically wrong when the user's actual ask is "engage with my specific data" — because the assistant never looked at the data before asking.

The clarifying question becomes useless friction. The user has to summarize their own data back to the assistant. They lie a little, because summarizing accurately would take ten minutes. The assistant then gives advice based on the lie, not the data.

This is why so many "AI research assistant" demos work great on toy examples and fall apart on real manuscripts. The toy examples are self-contained in the prompt. Real manuscripts live in `data.csv` and `notes.md` files that the assistant never opened.

## The pattern: scan-then-ask

The fix is structurally trivial and is what `thermal-mentor` calls **reflective routing**. The loop becomes:

1. Assistant scans the data first (without asking permission, because permission to read the visible CWD was already implied by invocation).
2. Assistant presents a one-screen reading: "Here's what I see. These columns are doing X. This paragraph says Y. Did I get it right?"
3. Assistant *infers* probable intent from the data, then asks targeted questions with the inferred-intent options pre-populated.
4. User picks an option (or interrupts and redirects).
5. Assistant produces output based on data + user-confirmed intent.

The user's first interaction is no longer "tell me what you want" — it's "here's what I noticed; is one of these the thing you came to me about?"

In practice, the user's response shifts from a 200-word summary of their own work to a single click. Friction collapses.

## Implementation sketch

In `thermal-mentor`, this is three discrete steps in `SKILL.md`:

**Step 0** — scan the current working directory into a JSON scaffold:

```python
from anomaly_brief import build_data_brief_scaffold
scaffold = build_data_brief_scaffold(cwd, include_text=True)
# scaffold.files_found       — sha256'd file inventory
# scaffold.csv_summaries     — per-column trend detection (monotonic_increase / etc)
# scaffold.text_files_content — verbatim notes.md / pdf-extracted text
```

The scanner is dumb on purpose. It does not call an LLM. It does file hashes, CSV column trend detection (`monotonic_increase`, `monotonic_decrease`, `non_monotonic`), and text extraction. This is the **invariant** part of the brief — the same CWD always produces the same `data_brief_hash`, which we need for reproducibility.

**Step 0.5** — the mentor session (the LLM) reads the scaffold and produces a one-screen reading: detected files, key claims with source citations, and *candidate anomalies* with verbatim quotes pulled directly from the data. Every claim cites a source. Users can interrupt at this point and say "no, that's not what I meant by `LLZO_Ta6`" — and the model corrects course before any analysis starts.

**Step 1** — the inferred-intent ask. Based on what was detected in Step 0, the model presents 2-4 tailored options:

```
I noticed your activation energy drops 26% while the lattice contracts 0.4%.
That's counterintuitive — usually tighter channel = higher barrier.

What brings you here?
  A) Help me figure out WHY (mode 0 — anomaly + hypothesis + discriminating experiment)
  B) Help me figure out where to PUBLISH this (publication strategy mode)
  C) Both — A first, then B as a handover
  D) Something else (free text)
```

The options are not generic. They're seeded by what was actually found in the data.

## The verifier_error semantic — sub-pattern

While we're talking about reflective routing, one related decision in `thermal-mentor` deserves a callout because most tools get it wrong: **the distinction between "the DOI doesn't exist" and "I couldn't reach the verification service."**

These are completely different facts. The first means the citation is wrong. The second means the network is down. If you map them to the same status code (which most DOI checkers do), you get a silent false positive: citations that *look* verified actually slipped through because OpenAlex returned a 503.

`thermal-mentor` returns three states from `verify_doi_multisource`:

- `verified` — found in at least one authoritative source
- `not_found` — checked authoritative sources, doesn't exist anywhere (Crossref or DOI.org HEAD says so)
- `verifier_error` — couldn't reach the sources due to network/HTTP/timeout errors

The `verifier_error` state is *not* counted in the `citation_validity_rate` denominator. The metric tells you only what fraction of actually-checkable references were valid. Network problems don't lie about your work.

This is the same shape as the reflective routing pattern, applied to one specific decision: be explicit about what you don't know, instead of papering over uncertainty with a default value.

## Where else this generalizes

The reflective routing pattern works anywhere the user's actual intent depends on the contents of files they expect you to have read:

- **Code review assistants** — scan the diff first, then ask "I see this PR adds caching to the auth endpoint, and the cache key includes the user-agent. Did you mean to vary by user-agent, or is that a leftover from debugging?"
- **PR review bots** — same shape: read the diff, summarize, then ask one targeted question instead of asking the contributor to summarize their own PR.
- **Customer support triage** — scan the user's account / recent errors first, then ask "I see you have three failed payments in the last hour. Is this the payment issue or something else?"
- **Bug-report assistants** — scan the stack trace first, then ask "this looks like a connection-pool exhaustion. Did you change the pool size recently, or is the load up?"

The common thread: any interaction where the user *expects* the assistant to have looked at the obvious context before asking what they want.

> **A note on what generalizes vs what's specialized.**
>
> The **pattern** (scan-then-ask reflective routing + `verifier_error` distinct status) is general — it applies to any workflow where the user has a corpus of artifacts and uncertain intent.
>
> The **shipped implementation** is specialized for research manuscripts: `SUPPORTED_EXTENSIONS` hardcodes `.docx/.pdf/.md/.txt/.csv/.xlsx`; the `data_brief` schema embeds `materials_system` and `manuscript_stage`; the verifier has Chinese citation regex + materials-science retraction blacklist. Porting to code review or customer support would require schema extensions and scanner adjustments — possible in a v0.2 fork, but not v0.1.3 functionality.

## A short defense against the obvious objection

"But this is just chain-of-thought prompting!" Yes and no. CoT is about getting better answers by writing intermediate reasoning. Reflective routing is about the *ordering of the user-facing protocol* — scan before ask. A model can have brilliant CoT and still ruin the conversation by asking "what would you like help with?" before reading the data. Reflective routing is the part of the protocol the user sees.

The other obvious objection: "what if scanning the data is expensive?" In `thermal-mentor`'s case, Step 0 is pure Python and finishes in under a second on typical research dirs. There's no token cost. The mentor LLM only sees the *scaffold* — file hashes + CSV trends + text content — not the raw bytes of every PDF. The expensive part (LLM reasoning) happens once, on the compressed scaffold, before the first user prompt.

## Try it

`thermal-mentor` v0.1.3 is MIT-licensed and ships with:

- 64 unit tests passing on Python 3.10-3.13 across Ubuntu + Windows
- Bilingual English + 简体中文 docs (1000+ line manual each)
- A synthetic LLZO demo dataset and a 5-step walkthrough
- The reflective routing pattern wired in as Steps 0 / 0.5 / 1 of `SKILL.md`

[github.com/dalek12310/thermal-mentor](https://github.com/dalek12310/thermal-mentor)

If you build an AI research assistant — or really any tool where the user expects you to have read their files before asking what they want — try the scan-then-ask order. It's not a deep idea, but it's the difference between "useful collaborator" and "another tab to close."
