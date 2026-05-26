# data-first prompts — Step 1 reflective ask

This file documents the inner-monologue rubric the mentor runs **silently** before rendering the Step 1 `AskUserQuestion`. It is *not* hardcoded — the mentor does this reasoning on the fly. Treat the rubric as the contract the model must satisfy each invocation.

## Inputs the mentor reads before reasoning

1. `trigger_prompt` — the user's original message that invoked the skill.
2. `tmp/data_brief.json` — Step 0 deterministic scan + LLM extraction output (files_found / central_claims / candidate_anomalies / materials_system / manuscript_stage).

## Inner monologue rubric — 4 archetypes

The mentor classifies the user's `underlying question` into one of four archetypes (A/B/C/D). The classification is **not exposed to the user**; it is used to bias the candidate intent options in Step 1.

### case A — phenomenon-first

User wants to know what anomalies live in the data. Trigger prompt is open-ended ("看看我数据里有什么意外的", "deep dive 一下这批样品").

- Likely mode: `data-first`.
- Step 1 option framing: lead with the most surprising candidate anomaly + verbatim quote + mentor inference (two-column display).

### case B — idea-critique

User already has an explicit hypothesis claim in the trigger prompt and wants to know whether the data supports or refutes it. Example: "我认为 mechanism X 是观测到的现象的主因, 帮我验一下".

- Likely mode: `data-first` (with `idea_critique_subbranch=True`).
- Step 1 option framing: see Section "case B subbranch" below.

> Anti-drift rationale: the word "idea" in "思考我目前数据的 idea" is ambiguous — it can mean "the idea that emerged from the data" *or* "the user's pre-existing idea applied to the data". The rubric must cover the second reading; otherwise `idea-critique` collapses into phenomenon-first and the user's explicit hypothesis gets silently ignored.

### case C — publication-readiness

User wants to know where the work can be submitted. Trigger prompt mentions journals, novelty, "能投哪", "卖点", reviewer concerns, revision targets.

- Likely mode: `publication-strategy`.
- Step 1 option framing: lead with the publication question, but **still preface with data observations** so the novelty judgment is grounded in the data and not in journal framing.

### case D — corpus query / methodology / other

User wants to query the local corpus (anchor researcher, citekey, DOI), ask about a method, or is using the skill for an unrelated purpose.

- Likely mode: `corpus_query` / `direction` / `other`.
- Step 1 option framing: surface the query as-is, no anomaly framing required.

## Candidate intent count constraint

Step 1 `AskUserQuestion` has a hard upper bound of 4 options. The mentor's option budget:

- **Default**: 2 candidate intents (mentor's top-ranked archetypes) + 1 mentor 主动建议 ("active suggestion": surface the most surprising data point that the trigger prompt did not cover) + 1 "其他" fallback = **4 options**.
- **Trigger极明确** (mentor confident on a single archetype): degrade to 1-2 candidates + 1 mentor 主动建议 + 1 "其他" = **3 options**.
- **Hard floor**: never fewer than 3 options. Even on极明确 triggers, keep the "mentor 主动建议" + "其他" pair to preserve the reflective-ask design intent.
- **Hard ceiling**: never more than 4 options (AskUserQuestion limit).

## case B (idea-critique) subbranch detail

Trigger condition: trigger prompt contains an **explicit hypothesis claim** the user attributes to themselves (not "the literature says" or "the textbook predicts" — those are textbook claims).

When case B fires, the Step 1 option that maps to `data-first` is reframed:

```
Option (case B): 检验你的 <mechanism> 主因假设

我从你的 trigger prompt 看到你认为 "<user's hypothesis>"。我可以:
  - 列出你这个 hypothesis 的可观测预测 (predicts_observable)
  - 在你数据里找支持和反驳的证据
  - 提出能 falsify 这个 hypothesis 的 discriminating experiment

→ mode 0 (idea-critique 子分支, 仍在 data-first pipeline)
trade-off: 焦点在你这个 hypothesis, 不挖其他 anomaly
```

Implementation hook: when the user picks this option, the mentor sets `idea_critique_subbranch=True` on the payload. Mode 0 Step B (anomaly enumeration) is **skipped** and the pipeline jumps directly to Step E (hypothesis enumeration), with `hypotheses[0]` = the user's claim (annotated `mentor_inference="user-provided"`) and `hypotheses[1..n]` = mentor-proposed alternatives.

This keeps the "one skill, one entrance" hard constraint — idea-critique is a sub-branch of mode 0, not a new top-level mode.

## "其他" fallback trigger conditions

Surface "其他" as a Step 1 option whenever:

1. Mentor's top-ranked archetype confidence is `low` (no single archetype dominates).
2. Trigger prompt is empty / single-word / pure greeting.
3. `data_brief.json` is empty (0 files scanned) — combined with `manuscript_stage="unknown"` this means mentor has no grounding to propose tailored options.
4. User has already interrupted ≥3 times this session (mentor's reading is clearly off; offer escape hatch).

If user picks "其他", AskUserQuestion **again** with the generic 4-mode menu:

```
- data-first       — 让我深挖数据 anomaly
- publication-strategy — 评估投稿策略 (创新性 / 找亮点 / 改论文 / 方向建议)
- both             — 先 data-first 再 publication
- corpus-query 或 其他 — 文献查询、方法咨询、自由文本
```

This is the lowest-friction fallback if the inner monologue mis-inferred user intent.

## Hard rule: verbatim quote + inference in every option description

Two-column display:

```
Option N: <one-line summary>

【数据原文】 (source_file:line)
"verbatim quote from data_brief.json"

【mentor 解读】
mentor's inference / framing

→ mode (data-first / publication-strategy / both / other)
trade-off: ...
```

If the mentor cannot identify a verbatim quote that backs a proposed option, the option **must not** be rendered. This is the self-correcting design — the user can challenge the quote OR the inference separately.
