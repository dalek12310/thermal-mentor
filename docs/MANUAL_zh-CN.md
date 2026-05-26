# thermal-mentor — 使用手册

> thermal-mentor v0.1.3 完整中文手册。
> 快速概览见 [README_zh-CN.md](../README_zh-CN.md)。English version: [MANUAL.md](MANUAL.md)。

## 目录

1. [概念总览](#1-概念总览)
2. [安装和准备](#2-安装和准备)
3. [配置: 环境变量](#3-配置-环境变量)
4. [当 Claude Code skill 用](#4-当-claude-code-skill-用)
5. [当 CLI 工具用](#5-当-cli-工具用)
6. [Mode 0 工作流 (数据优先)](#6-mode-0-工作流-数据优先)
7. [投稿策略工作流](#7-投稿策略工作流)
8. [圆桌审稿协议](#8-圆桌审稿协议)
9. [DOI 多源核验](#9-doi-多源核验)
10. [paper-pdf-acquisition 联动](#10-paper-pdf-acquisition-联动)
11. [可复现性 + acceptance 跑](#11-可复现性--acceptance-跑)
12. [输出 schema](#12-输出-schema)
13. [常见故障](#13-常见故障)
14. [扩展开发](#14-扩展开发)

---

## 1. 概念总览

`thermal-mentor` 是一个**装在盒子里的科研导师**。它针对一个非常具体的时刻设计:

- 你手里有原始实验数据和一份草稿。
- 你不确定数据撑得起 Nature Materials, 还是只能投个普通刊。
- 你想要的不是套话, 而是真的钻进你数据里的第二意见。

绝大多数 LLM "科研助手"都有两种 failure mode:

- **空泛鼓励** ("看起来是一篇很好的论文!") —— 没用。
- **空泛批评** ("引用要更全, discussion 要更紧") —— 也没用。

`thermal-mentor` 想干的是另一件事: **从你的数据出发**, 找到你测出来的东西和教科书预测冲突的位置, 然后从那里往前推。

### 1.1 反思式路由模式

绝大多数 skill 一上来就问"你想让我干啥"—— 但用户嘴上说的问题, 经常错过了数据里最反直觉的那一点。`thermal-mentor` 是先扫数据, 基于看到的东西生成几个推断意图选项, **然后才问** —— 给你确认或纠正的机会。

这个 rubric 在 `references/data-first-prompts.md` 里 (Step 1 inner-monologue rubric)。

### 1.2 双模式架构

```
                    +------------------+
                    |  /thermal-mentor |
                    +--------+---------+
                             |
                +------------+------------+
                | Step 0/0.5/1 反思式路由 |
                |        protocol         |
                +------------+------------+
                             |
              +--------------+--------------+
              |              |              |
        +-----v-----+ +------v------+ +----v-----+
        |  Mode 0   | |    Both     | | Publication|
        |data-first | |  (handover) | | -strategy  |
        +-----------+ +-------------+ +-----------+
```

- **Mode 0 (data-first)**: anomaly 枚举 -> hypothesis 枚举 -> 区分实验。Materials-science-domain-agnostic。
- **Publication-strategy**: novelty / highlight / revision / direction / corpus query。V0.1 原 pipeline。
- **Both**: 先 mode 0, 然后 publication 模式读 mode 0 payload 的 `mode_0_handover` 字段, 自动预填 Level-2 问句。

### 1.3 五条硬规则

每次调用强制执行 (在 `SKILL.md` 里):

1. **永远不跳过 three-level ask gate。** 哪怕用户请求看起来很明确, 也要先跑 Step 0/0.5/1。
2. **永远不编造引用。** 任何 `supporting_refs` 都必须是可验证的 citekey / DOI / arXiv ID / manuscript-chunk reference。Verifier 会抓出来。
3. **诚实评估。** 永远不要为了哄用户而虚抬 novelty。Corpus 显示 X 已发表就直说。
4. **第一性原理 + 中文输出。** 用中文回答 (专业术语 English OK)。论证必须给机制, 不能说"文献都这么讲"。
5. **用户面文案必须人话。** 内部 codename (`mode 0`, `L1/L3`, `anomaly_brief`, `supporting_refs`) 不能漏到 AskUserQuestion 选项或渲染 Markdown 里。

### 1.4 设计决策都在哪

| 文件 | 文档内容 |
|---|---|
| `SKILL.md` | 编排, 硬规则, Step 0/0.5/1, Mode 0 pipeline Step A-I, publication pipeline Step A-H |
| `references/ask-first-prompts.md` | Level 1/2/3 问题库 |
| `references/data-first-prompts.md` | Step 1 inner-monologue rubric (case A/B/C/D) |
| `references/output-schemas.md` | Publication-mode JSON schemas |
| `references/output-schemas-data-first.md` | Mode 0 JSON schemas (`data_brief.json`, anomaly 6字段, hypothesis, experiment, handover) |
| `references/cross-review-protocol.md` | Round 1-4 round-table, 召唤关键词, attribution 表 |
| `references/pdf-acquisition-handoff.md` | T1/T2/T3 trigger, manifest CSV, resume instruction |
| `references/user-facing-language.md` | 人话 hard rule (codename -> 人话 翻译表) |

---

## 2. 安装和准备

### 2.1 装成 Claude Code skill

skill 直接 clone 到 Claude skills 目录:

```bash
# Linux / macOS
git clone https://github.com/dalek12310/thermal-mentor.git ~/.claude/skills/thermal-mentor

# Windows (PowerShell)
git clone https://github.com/dalek12310/thermal-mentor.git $env:USERPROFILE\.claude\skills\thermal-mentor
```

重启 Claude Code; 调 `/thermal-mentor` 时 skill 自动激活。

验证安装:

```bash
ls ~/.claude/skills/thermal-mentor/SKILL.md  # 应该存在
```

### 2.2 当 Python 库用

跑 CLI 或单测的话, editable 装:

```bash
git clone https://github.com/dalek12310/thermal-mentor.git
cd thermal-mentor
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

依赖 (写在 `pyproject.toml`): `httpx`, `python-docx`, `pdfplumber`, `pyyaml`, `pytest` (test extras)。

要求 Python >= 3.10。在 3.10 / 3.11 / 3.12 / 3.13 上测过。

### 2.3 验证安装

```bash
pytest tests/ -v
```

期望: `64 passed in <time>`。

如果挂了:

- 检查 Python 版本 (`python --version`)。
- 检查 `pip install -e .` 是否成功 (没有 warning)。
- 确认没有环境变量从别的项目串过来; 特别是 `unset THERMAL_MENTOR_CORPUS` 如果它指向不存在的目录。
- 确认 `tests/` 和 `scripts/` 都在 `sys.path` 上。`conftest.py` 帮你处理了 pytest 场景, 但 ad-hoc Python 调用要手动加 `scripts/`。

---

## 3. 配置 (环境变量)

所有变量都是可选; 不设置时工具会优雅降级。

### 3.1 `OPENALEX_MAILTO`

OpenAlex 和 Crossref 都有 "polite pool", 你通过 `mailto` 参数或 User-Agent 标识自己后会获得更高的 rate limit。设置为你的邮箱:

```bash
export OPENALEX_MAILTO="you@example.com"
```

不设置时, 请求走匿名池: 更慢, 更多 429, 偶尔有冷启动延迟。Skill 仍然能跑, 但 DOI 核验每条 ref 会多花几秒。

### 3.2 `THERMAL_MENTOR_CORPUS`

本地引文 corpus 目录路径。Corpus 目录至少需要:

- `distillation_corpus_v2.csv` —— bibliographic CSV, 至少含 `citekey` 和 `doi` 两列。
- `retraction_blacklist.yaml` —— 撤稿 citekey/DOI 列表, verifier 拒绝核验。

```bash
export THERMAL_MENTOR_CORPUS="/path/to/your/local/corpus"
```

不设置时: publication-mode 本地 citekey 查询返回 `not_found`; verifier fallback 到 DOI multi-source。Mode 0 不用 corpus (它是数据驱动, 不是引用驱动), 所以不受影响。

### 3.3 `LENS_API_TOKEN`

Lens.org Scholarly API token。设置后, 多源 DOI 核验链会加上 Lens 作为二次 metadata 源。

```bash
export LENS_API_TOKEN="your_token_here"
```

不设置: `_build_chain` 静默跳过 Lens (见 `scripts/doi_verify_multisource.py:151`)。

### 3.4 `WOS_API_KEY`

Web of Science Starter API key。设置时插在核验链第 2 位 (在 Crossref 之后, Semantic Scholar 之前)。

### 3.5 `CLAUDE_MODEL_ID`, `CLAUDE_MODEL_VERSION`, `CLAUDE_TEMPERATURE`

`run_acceptance.save_run` 用来填 acceptance payload 的 `reproducibility` 块 (见 §11)。不设置时记为 `"unknown"`。

### 3.6 `.env` 文件约定

仓库的 `.gitignore` 已排除 `.env`。可以在仓库根目录写开发用的 `.env`:

```bash
# .env
OPENALEX_MAILTO=you@example.com
LENS_API_TOKEN=lens_xxxxx
WOS_API_KEY=wos_xxxxx
```

然后 source (`set -a; . ./.env; set +a` in bash) 再跑 CLI。Skill 本身不自动 load `.env` —— 在父 shell 里 export 让 Claude Code 继承。

---

## 4. 当 Claude Code skill 用

### 4.1 调用方式

在任意 Claude Code session 里输入:

```
/thermal-mentor
```

Skill 激活, 立刻跑 Step 0 (扫当前工作目录)。

如果 CWD 里一个支持的文件都没有, skill 回落到 Level-3 input source `AskUserQuestion`:

- `folder` —— 项目文件夹路径 (mentor 去扫)
- `question + text` —— 我直接告诉你数据描述 (打字)
- `manuscript` —— 单个 manuscript 文件路径
- `from-corpus` —— 已在本地 corpus 里 (citekey)
- `review-pdf` —— 一篇外部 PDF 文件路径

### 4.2 一次会话走查

典型会话长这样:

```
你: /thermal-mentor

Mentor: [静默扫]
        基于以上数据, 你想让我做什么?
        
        Option 1: 深挖你 X-ray 数据里的奇怪现象
                  【数据原文】(notes.txt:7) "XPS+EPR 0/2/4/6% signal decreases monotonically"
                  【mentor 解读】掺杂应该 net-increase defects, 但这里反而降, 像是 self-compensation 没解释完
                  -> 深挖数据 (这是你数据里最反直觉的点)
                  trade-off: 可能没时间评估投稿方向
        
        Option 2: 评估这篇论文能投哪
                  【数据原文】(draft.docx:p1) "We report a novel synthesis route..."
                  【mentor 解读】方法 novelty 是卖点, 但需要先 anchor 一下机制
                  -> 评估投稿策略
                  trade-off: 不会深挖数据 anomaly
        
        Option 3: 先深挖数据, 再评估投稿
                  -> 两条 pipeline 串起来
                  trade-off: 时间最长
        
        Option 4: 其他

你: [挑 Option 1 或 Option 3]
```

### 4.3 这个 skill 不做的事

- 不在 session 里跑 pip / 装依赖。
- 不修改你的 manuscript 文件。
- 不把你的数据上传到任何服务器 (DOI 核验只发 DOI 字符串, 不发你的数据)。
- 不编造 DOI 填 `supporting_refs`。Mentor 找不到 ground 时直接 omit。

### 4.4 打断 mentor

如果 Step 0.5 surfaced 的 claim 或 anomaly 你不同意, 可以自然打断:

```
你: 等等, 这个 trend 是上升不是下降, 你看错了
Mentor: [重读 data_brief.json 里的 quote_verbatim, 重新渲染 reading]
```

Skill 计打断次数 (设计上每 session max 5)。打断超过 5 次, skill 建议重启, 因为 data brief 显然偏了。

### 4.5 召唤关键词 footer

每次最终 Markdown 末尾都有:

```
---
💬 觉得这次判断不靠谱? 回复 "叫 codex 审" / "叫 opus 审" / "叫 ds 审"
   我会重启刚才的判断, 用第二意见挑刺。
```

回复任一关键词, skill 读 `tmp/payload.json` 直接进 Step F.5 cross-review —— **不**重跑 Step A-F。这是"懒人第二意见"通道。

关键词匹配是 fuzzy 的。变体如 "叫 codex 来审", "codex review", "再 opus 审一次" 都能识别。歧义回复触发 `AskUserQuestion` 让用户挑。

---

## 5. 当 CLI 工具用

`scripts/` 下 10 个脚本都可以从命令行用。下面是完整 reference; 每个脚本也支持 `--help`。

### 5.1 `scripts/anomaly_brief.py`

扫描目录, 输出 `data_brief.json` scaffold。

```bash
python scripts/anomaly_brief.py /path/to/data --out tmp/data_brief.json --include-text
```

- `cwd` (positional) —— 递归扫描的目录。
- `--out` —— 输出 JSON 路径。默认 `tmp/data_brief.json`。
- `--include-text` —— 把 `.docx` / `.pdf` / `.md` / `.txt` 提取的文本一起包进去 (CLI scaffold 路径; 完整的 anomaly 提取在 mentor session 做)。

CLI mode 写出来的是 *scaffold* —— `central_claims`, `candidate_anomalies`, `materials_system`, `manuscript_stage` 都留空给 mentor (LLM) 填。`data_brief_hash` 只对扫描器决定的不变量做哈希, 所以同一输入下 scaffold 和 mentor 增强版 brief 共享同一个 hash。

### 5.2 `scripts/verifier.py`

在 payload JSON 上跑 DOI / citekey 核验。

```bash
python scripts/verifier.py tmp/payload.json
```

按 `payload["mode"]` 分发:

- `data_first` -> `verify_mode_0`: 检查每条 anomaly 的 `data_evidence` 源文件存在性 + 每条 hypothesis ref 的 DOI 多源核验。
- `novelty_review` / `highlight_mining` / `revision` / `direction_guidance` / `corpus_query` -> `verify_payload`: 完整的 publication-mode verifier, 包括本地 citekey 查询, 撤稿黑名单, 锚点 registry 交叉检查。

核验后 payload JSON 输出到 stdout。重定向到文件:

```bash
python scripts/verifier.py tmp/payload.json > tmp/payload.verified.json
```

Markdown 渲染 (`verifier.render_markdown` / `verifier.render_markdown_mode_0`) 既暴露为 Python API, 也被 `run_acceptance.save_run` 内部调用。

### 5.3 `scripts/run_acceptance.py`

落盘 verified payload (JSON + Markdown), 追加 audit-log 记录, 可选 N 次重复跑做稳定性测试。

```bash
python scripts/run_acceptance.py tmp/payload.json \
    --run-name "myproject_v0.1.3_data_first_20260525" \
    --reproducibility-manifest tmp/data_brief.json \
    --repeat 3
```

- `payload_json` (positional) —— verified payload 路径。
- `--run-name` (required) —— 唯一 run name; 约定 `<task>_<release>_<mode>_<date>`。
- `--reproducibility-manifest` (optional) —— `data_brief.json` 路径; `data_brief_hash` 从这里读。
- `--repeat N` (default 1) —— 写 N 个独立 run, 每个 run_name 加 `_run<i>` 后缀。

N=1 时, 输出文件名 `<run_name>_<YYYYMMDD>.json` / `.md`。N>1 时, `<run_name>_run<i>_<YYYYMMDD>.json` / `.md`。

`save_run` 在写 JSON 前会注入 `reproducibility` 块:

```json
{
  "reproducibility": {
    "model_id": "<from $CLAUDE_MODEL_ID>",
    "model_version": "<from $CLAUDE_MODEL_VERSION>",
    "sampler_temperature": "<from $CLAUDE_TEMPERATURE>",
    "data_brief_hash": "<from --reproducibility-manifest>",
    "system_prompt_hash": "<sha256(SKILL.md)[:16]>",
    "pipeline_version": "0.1.3",
    "run_name": "<--run-name>"
  }
}
```

### 5.4 `scripts/cross_review_merge.py`

把多个 cross-review 审稿人 JSON 合并成单个分类 finding bundle, 带对称 DOI 归属。

```bash
python scripts/cross_review_merge.py \
    tmp/round1_opus.json tmp/round1_codex.json tmp/round1_ds.json \
    --out tmp/cross_review_final.json
```

输入: 任意数量的审稿人 JSON 文件 (Round 1 或 Round 2 格式)。
输出: 合并 JSON, 含:

- `round_table_summary` —— findings 按 confidence (`high` / `medium` / `low`) 分类。
- `deleted_refs` —— DOI 核验失败被删除的 refs。
- `attribution_per_ref` —— 每条 ref 哪个审稿人引入。
- `reviewers_used` —— 审稿人标签列表。

合并 JSON 可以折回 `payload.json` 的 `cross_review` 字段。

### 5.5 `scripts/live_search.py`

多源在线学术搜索。

```bash
python scripts/live_search.py "<query>" --since 2018-01-01 --top-k 10
```

来源: OpenAlex, Semantic Scholar, arXiv (always); Lens.org 和 Web of Science 在对应 API token 设置时加进来。返回去重的 top-K 结果, 按时间/相关性排序。

### 5.6 `scripts/paper_pdf_handoff.py`

程序化 API (无 CLI)。生成 manifest CSV + resume instruction Markdown 块:

```python
from scripts.paper_pdf_handoff import write_manifest, render_resume_instruction

rows = [
    {
        "doi": "10.1038/s41563-024-xxxx",
        "citekey": "Author2024Title",
        "why_needed": "验证 hypothesis H1a, 需要原文 Method 段落",
        "expected_section": "methods",
        "resume_token": "20260525-103200-xyz789",
    },
]
write_manifest("tmp/pdf_handoff_20260525-103200-xyz789.csv", rows)

instruction = render_resume_instruction(
    "tmp/pdf_handoff_20260525-103200-xyz789.csv",
    "20260525-103200-xyz789",
    [r["doi"] for r in rows],
)
print(instruction)  # 贴到 Markdown 末尾
```

每个 manifest 最多 5 行 (`MAX_DOI_PER_MANIFEST = 5`); 超出函数 raise `ValueError`。

### 5.7 其他脚本

- `manuscript_brief.py` —— `.docx` / `.pdf` / `.md` / `.txt` 文本提取。被 `anomaly_brief.py --include-text` 路径调用。
- `doi_verify_multisource.py` —— 暴露 `verify_doi_multisource(doi)` 供 ad-hoc 核验。
- `audit_log.py` —— 暴露 `audit_log.append(record)` 写月度 JSONL 日志。
- `eval_runner.py` —— 4 个纯函数 helper: `compute_anomaly_recall_rate`, `compute_hypothesis_completeness`, `compute_existing_data_answerable_rate`, `compute_false_anomaly_rate`。

---

## 6. Mode 0 工作流 (数据优先)

Mode 0 是 Step 1 用户挑 `data-first` 或 `both` 后跑的数据优先 pipeline。9 个子步骤 (A - I)。

### 6.1 Step A —— data_brief.json 已存在

Mentor 读 `tmp/data_brief.json` (Step 0 生成的, 不重扫不重建)。

### 6.2 Step B —— anomaly enumeration

把 `data_brief.json` 里的 `candidate_anomalies` 提升成正式 6 字段 schema:

```json
{
  "anomaly_id": "A1",
  "observation": "0/2/4/6 mol% 掺杂系列里, 缺陷信号 (XPS O1s + EPR) 单调下降",
  "expected_textbook": "异价取代教科书: 三价掺到四价位置应该 net-increase defects 来维持电荷平衡",
  "surprise_score": "high",
  "data_evidence": [
    {
      "source": "notes.txt:7",
      "quote_text": "XPS+EPR 0/2/4/6% defect signal decreases monotonically",
      "line_or_para": "p2"
    }
  ],
  "context_questions_to_user": [
    "你有 XPS 测过 3+ vs 4+ 的 speciation 吗?",
    "烧结的氧分压是多少?",
    "有没有 EXAFS 给掺杂占位的 coordination 证据?"
  ]
}
```

如果 `idea_critique_subbranch=True` (case B), 跳过 Step B —— 直接到 Step E, 把用户的 hypothesis 作为 `hypotheses[0]`。

### 6.3 Step C —— 用户门控 1: 要不要查文献?

弹 `AskUserQuestion`:

- `让我凭物理直觉先想机制` —— mentor 仅基于数据提 2-4 个候选机制。
- `先帮我查文献再想机制` —— Step E 之前先跑 Step D。
- `两阶段并行` —— 先跑 Step E (不查文献), 再跑 Step D, 然后跑一遍 Step E2 enrichment pass。
- `先停一下让我消化 / 别的`

注意选项标签: **不带"推荐"标签**, 只给中性 trade-off。这是 deliberate 的 anti-bias 规则。

### 6.4 Step D (可选) —— L1 + L3 检索

只在 Step C 用户挑 "先帮我查文献" 或 "两阶段并行" 时跑。

```bash
# L1 (本地 corpus hybrid retrieve) —— 仅在 THERMAL_MENTOR_CORPUS 设置时
python ~/.claude/skills/thermal-mentor/scripts/hybrid_retrieve.py "<anomaly observation>" --top-k 5

# L3 (在线学术搜索)
python ~/.claude/skills/thermal-mentor/scripts/live_search.py "<anomaly observation>" --since 2018-01-01 --top-k 10
```

给每条 anomaly 标 `prior_art_hits`。

### 6.5 Step E —— hypothesis enumeration

每条 anomaly 提 2-4 个候选机制:

```json
{
  "hypothesis_id": "H1a",
  "anomaly_id": "A1",
  "mechanism_text": "双位自补偿: 掺杂同时占 A 位和 B 位",
  "data_support": ["4 mol% Raman shift 跟 B 位占位一致 (notes.txt:14)"],
  "data_contradict": ["..."],
  "supporting_refs": [...],
  "predicts_observable": [
    "如果纯电荷补偿, A:B 占位比应该约 1:1",
    "EXAFS 配位数应该等于 (CN_A, CN_B) 的均值",
    "Raman 应该同时出现 A 位和 B 位掺杂的模式"
  ]
}
```

`predicts_observable` **至关重要**。每个机制都列出"如果机制成立, 数据里还应该看到什么"。用户可以自己回去查数据验证 —— 不用信 mentor。

### 6.6 Step F —— 区分实验

每条 anomaly 提 1-2 个能区分候选机制的实验:

```json
{
  "experiment_id": "E1",
  "anomaly_id": "A1",
  "discriminates_between": ["H1a", "H1b"],
  "experiment_text": "在 4 mol% 掺杂下用 XPS 测 3+ vs 4+ speciation",
  "answerable_by": "existing_data",
  "if_new_experiment": {"effort": "low", "rough_cost": "现有 XPS 一天"},
  "expected_outcome": {
    "H1a_predicts": "全是 4+ 态",
    "H1b_predicts": "肩峰出现 3+ 态"
  }
}
```

`answerable_by=existing_data` **优先** —— 主动找用户已有但还没挖到的数据资产。

### 6.7 Step F.5 —— 圆桌审稿 gate (可选, 默认 OFF)

弹 `AskUserQuestion`:

- `不用` (默认; 跳过 Round 1-4)。
- `叫 Codex` / `叫 Opus` / `叫 DS` / `叫全员` / `自己挑`。

用户挑 reviewer 后, mentor 用 `Agent` tool 并行 spawn。完整协议见 §8。

### 6.8 Step G —— verifier

```bash
python ~/.claude/skills/thermal-mentor/scripts/verifier.py tmp/payload.json
```

Mode 0 verifier 检查:

- 每条 anomaly 的 `data_evidence` 源文件存在。
- 每条 hypothesis 的 `supporting_refs` DOI 通过多源核验 (§9)。
- `render_markdown_mode_0` 渲染。

### 6.9 Step H —— 渲染 + audit log + acceptance save

```bash
python ~/.claude/skills/thermal-mentor/scripts/run_acceptance.py \
    tmp/payload.json --mode data_first \
    --reproducibility-manifest tmp/data_brief.json \
    --run-name "<task>_v0.1.3_data_first_<date>_runN"
```

落盘 JSON+MD, 追加 audit_log 记录, 注入 reproducibility 块。一定带召唤 footer。

### 6.10 Step I (仅 "both" 模式) —— 投稿 gate

Mode 0 在 "both" 模式跑完后, mentor 问:

- `要不要叠投稿策略评估?`
- Yes -> 进 publication pipeline Level-2, `mode_0_handover` 自动预填选项。
- No -> 结束。

---

## 7. 投稿策略工作流

V0.1 原 pipeline。5 个 mode, 结构相似。

### 7.1 Level-1 模式选择

`AskUserQuestion`:

1. `novelty` —— 评估创新性 / 是否已被发表。
2. `highlight` —— 找亮点 / 包装一句话 narrative。
3. `revision` —— 改论文。
4. `direction` —— 方向建议。
5. `corpus_query` —— 查本地 corpus。

### 7.2 Level-2 每个 mode 的 clarifier

Mode-specific。比如 `novelty`:

- Q1: novelty 定义 —— 第一次提出 / 第一次用方法 / 第一次在你的材料体系上 demonstrate。
- Q2: 失败容忍度 —— 不容忍 / 容忍 5% / 容忍 10%。
- Q3: 目标期刊 —— Nat Mater / Nat Commun / Adv Mater / JACS-ACS Nano-Nano Lett / 其他 (**放最后**, 避免被 framing 带偏 ceiling estimate)。

其他 mode 见 `references/ask-first-prompts.md`。

### 7.3 Level-3 输入源

`AskUserQuestion`:

1. `folder` —— 项目文件夹路径。
2. `question + text` —— 内联描述。
3. `manuscript` —— manuscript 文件路径。
4. `from-corpus` —— 已有 citekey。
5. `review-pdf` —— 外部 PDF 文件路径。

### 7.4 Pipeline Step A-H

| Step | 操作 |
|---|---|
| A | Ingest input -> manuscript brief if applicable (`manuscript_brief.py`) |
| B | Retrieve from local corpus L1 (`hybrid_retrieve.py`, 仅 corpus 配置时) |
| C | Live external search L3 (`live_search.py`) |
| D | Pull anchor registry context (仅 corpus 配置时) |
| E | Reason and produce JSON per `references/output-schemas.md` |
| F | Verify via `verifier.py` |
| G | Persist run (acceptance + audit log) via `run_acceptance.save_run` |
| H | 把渲染好的 Markdown 给用户 |

---

## 8. 圆桌审稿协议

完整协议在 `references/cross-review-protocol.md`。下面是操作摘要。

### 8.1 什么时候触发 cross-review

- 用户在 Step F.5 gate 挑 reviewer (mode 0 / both)。
- 用户在 v0.1 publication gate 挑 reviewer。
- 用户在最终 Markdown 后回 召唤 关键词。

Cross-review **永不默认开启**。跑 30-90 分钟, 多数 invocation 不需要这点延迟。

### 8.2 Round 1 —— 并行独立 critique

Mentor 用 `Agent` tool 在单条消息里并行 spawn 每个选中的 reviewer。Reviewer (Opus 4.7 subagent / Codex GPT-5 xhigh / DeepSeek V4 Pro) 收同样输入 (payload JSON + brief context), 返回 JSON:

```json
{
  "reviewer": "opus|codex|ds",
  "findings": [
    {"text": "...", "severity": "critical|major|minor", "evidence": "...",
     "introduced_refs": [{"value": "doi/citekey", ...}]}
  ],
  "introduced_refs": [{"value": "doi or arxiv id", ...}],
  "round": 1
}
```

存 `tmp/cross_review_round1_<reviewer>.json`。

### 8.3 Round 2 —— 看完彼此 critique 后表态

Mentor 把所有 Round 1 critiques 合成 bundle 发给每个 reviewer。Reviewer 可以:

- **Endorse** 另一个 reviewer 的 finding (提高 confidence)。
- **Refute** 给反证。
- **Supplement** 补充细节。
- **Pass** 没证据加。

存 `tmp/cross_review_round2_<reviewer>.json`。

### 8.4 Round 3 —— DOI 多源核验

任何 reviewer 引入的 DOI 都过 `cross_review_merge.merge_reviews` -> `doi_verify_multisource.verify_doi_multisource`。

- 核验通过的 refs: 保留; 标注来源 attribution。
- `not_found` 的 refs: **删除 ref 但保留 finding 文本** (论点跟引用解耦)。记到 `cross_review.deleted_refs` 供 audit 透明。
- `verifier_error` 的 refs: 保留, Markdown 里标"校验器报错 (网络问题, 非引用错误)"。

### 8.5 Round 4 —— 合并进最终 payload

`cross_review_merge.classify_findings` 按 30 字符前缀相似度归组, 分 confidence:

- `high` —— 所有 reviewer 都同意。
- `medium` —— 多数同意 (>= ceil(N/2)+1)。
- `low` —— 单独。

`cross_review_merge.attribute_refs` 给每条 reviewer 引入的 ref 分配**对称归属**。Runtime Markdown 里不给任何 reviewer 打"高风险"标签。

### 8.6 反歧视规则

按 spec Section 4.4.3:

1. 每条 reviewer 引入的 DOI 都有 `Attribution` 列条目, 不管哪个 reviewer 引入。
2. DeepSeek 历史 fabrication signal (~75% 在 audit 2026-05-25 测出) 写在项目级的 `CROSS_MODEL_REVIEW_SOP.md` 里, **不**进 runtime Markdown。理由: 在每份用户报告里 re-litigate reviewer 可靠性会视觉上压低 DS 的架构级 critique, 而 audit 发现这些在高层确实有用。
3. 所有 reviewer DOI 都过同一个多源核验链。没有任何 reviewer 走特殊链。
4. 如果 DOI 核验失败: ref 删, finding 文本留, `cross_review.deleted_refs` 记 `(value, reason, introduced_by)`。用户看到 `attribution = "<reviewer> 引入 -> 自动剔除, 论点保留"`。

### 8.7 召唤关键词表

| 用户关键词 (case-insensitive, fuzzy) | 召唤的 Reviewer | subagent_type |
|---|---|---|
| `叫 codex 审` / `codex 来审` / `codex review` | Codex GPT-5 xhigh | `codex:codex-rescue` |
| `叫 opus 审` / `opus subagent` / `再 opus 审一次` | Opus 4.7 subagent | `general-purpose` (model=opus) |
| `叫 ds 审` / `deepseek 审` / `v4 来审` | DeepSeek V4 Pro | `deepseek-code-reviewer` |
| `叫全员审` / `三方审` / `roundtable` | 三个全要 | 三个 `Agent` 并行调用 |
| 不明确 | mentor 用 `AskUserQuestion` 让用户挑 | — |

---

## 9. DOI 多源核验

### 9.1 链

**4 个常驻源** (OpenAlex / Crossref / Semantic Scholar / DOI.org HEAD) **+ 2 个 env-gated 源** (Lens.org 需 `LENS_API_TOKEN`, Web of Science 需 `WOS_API_KEY`):

```
OpenAlex (qps=10)  -> Crossref (qps=50, 权威)  -> Semantic Scholar (qps=1)
                   -> [Lens.org if LENS_API_TOKEN]      -> [WoS if WOS_API_KEY]
                   -> DOI.org HEAD (权威)
```

源顺序固定; `_build_chain` 只根据环境变量条件性插入 Lens / WoS。

### 9.2 语义

- **非权威源 `not_found`**: 继续 fallback (可能是 metadata 索引 gap)。
- **权威源 (Crossref 或 DOI.org HEAD) `not_found`**: 确认不存在; 链终止, `status=not_found`。
- **任何源 `verified`**: 立刻返回, 该源作为 attribution。
- **所有源 raise HTTPError / TimeoutException**: 返回 `status=verifier_error`, `error_detail.all_sources_failed` 装积累的错误列表。

`verifier_error` 状态显式区分于 `verified` 和 `not_found`。它是一个**副信道**, 用户面 Markdown 渲染成"校验器报错 (网络问题, 非引用错误)"。

### 9.3 缓存

- 24 小时磁盘缓存 `cache/doi_verify/<hash>.json`。
- `verified` 和 `not_found` 缓存; `verifier_error` **不**缓存 (transient)。
- 缓存 key 是 sha256(normalized_doi)[:24]。
- Cache miss -> 全链跑。

### 9.4 DOI 归一化

`normalize_doi` 剥 `https?://(dx\.)?doi\.org/` 和 `doi:` 前缀 (case-insensitive), 然后小写化。任何 DOI 入链都过这一步, 防止缓存碎片化。

### 9.5 LegacyDoiAdapter

Publication-mode 的 `verifier.py` 有个 `LegacyDoiAdapter`, 把 `verify_doi_multisource` 包装成 v0.1 `check_doi` 接口。这样旧的 Step-F verifier 代码可以透明调用新多源链, 不用动 business logic。

---

## 10. paper-pdf-acquisition 联动

### 10.1 为什么独立成 skill

`paper-pdf-acquisition` 是 Edge / CARSI / Shibboleth 交互式 skill —— 不能当 Python API 调。它执行 5 条不可变硬规则:

1. 不用 Sci-Hub。
2. 不绕 Cloudflare。
3. 用干净 Edge profile (CARSI / Shibboleth 登录)。
4. 没有用户明确授权前不写 Zotero SQLite。
5. 每个 PDF 都做 header check。

规则 2-3 需要 Chrome DevTools Protocol session 控一个用户已登录的真实 Edge profile。把这个嵌进 thermal-mentor 要么绕过用户认证 (违规), 要么每次调用阻塞 30-60s setup。决定: 按需懒调, **跨 session manifest 联动**。

### 10.2 T1 / T2 / T3 触发条件

| Trigger | 触发方 | Mentor 行为 |
|---|---|---|
| **T1 —— 用户显式请求** | 用户: "我想看这篇 [DOI]" / "深挖 [citekey]" | Mentor 调 `write_manifest` + `render_resume_instruction`, 追加到当前 Markdown |
| **T2 —— mentor 主动推荐** | Mode 0 Step E 识别某篇 paper 对 hypothesis 验证关键 | Mentor **不打断 pipeline**。推荐进**最终** Markdown 末尾 (Step H 之后) |
| **T3 —— verifier_error fallback** | 多源链对某 reviewer 坚持的 DOI 返回 `verifier_error` | Markdown 加: "可调 paper-pdf-acquisition 物理验证 DOI 存在性" |

T2 设计上 **不打断**。打断 session flow 让用户中途启 CARSI 的代价, 超过内联 PDF retrieval 的价值。

### 10.3 Manifest CSV schema

`paper_pdf_handoff.write_manifest` 写到 `tmp/pdf_handoff_<audit_log_id>.csv`:

| 列 | 说明 |
|---|---|
| `doi` | DOI 字符串。如果没 citekey 必填。 |
| `citekey` | 本地 corpus citekey。如果没 DOI 必填。 |
| `why_needed` | 纯文本理由: "验证 H1a hypothesis 的关键证据" / "用户 trigger 显式要求深挖" |
| `expected_section` | 全文到了之后 mentor 读哪段: `methods` / `results` / `discussion` / `full` |
| `resume_token` | 当前 mentor run 的 `audit_log_id`。用于用户回来时重新关联 fulltext。 |

每个 manifest 最多 5 行 (`MAX_DOI_PER_MANIFEST = 5`)。更大请求拆成多个 handoff。这个上限防止误触发"把 L3 结果所有 paper 都拉下来"。

### 10.4 Resume instruction 模板

`render_resume_instruction` 输出 Markdown 块:

```
我需要这些 paper 的全文才能验证当前 hypothesis (audit_log_id=<id>):

  - <DOI 1>
  - <DOI 2>
  - ...

请在**新会话**跑:
  /paper-pdf-acquisition 用 tmp/pdf_handoff_<id>.csv

完成后回到本 session 跟我说 "PDF 拿好了, 继续 <audit_log_id>",
我会读 04_fulltext/ 下提取的文本进行 hypothesis 验证。

(paper-pdf-acquisition 走你机构 CARSI/Shibboleth 合法路径, 不绕 Cloudflare,
不用 Sci-Hub。如果 CARSI 没机构订阅, 该 paper 会被 paper-pdf-acquisition
显式 mark 为 unresolved, 不会假装下载成功。)
```

"PDF 拿好了, 继续 <audit_log_id>" 回复模板是原 session 恢复的**唯一**途径。

### 10.5 跨 session flow

1. **Mentor session (原)**: 写 manifest CSV, 追加 resume instruction, payload state 存 `tmp/payload.json`。
2. **用户开新 session**: 跑 `/paper-pdf-acquisition <CSV path>`。paper-pdf-acquisition 走 OA / CARSI / Shibboleth / arXiv 下。
3. **用户回 mentor session** 说 `PDF 拿好了, 继续 <audit_log_id>`。Mentor 读 `04_fulltext/<citekey>.txt`, 带新全文进 Step E 再推一次。

如果有 DOI 返回 `unresolved`, mentor 基于部分全文调整 hypothesis + 在新 Markdown 里 flag 这些 unresolved DOI。

---

## 11. 可复现性 + acceptance 跑

### 11.1 `data_brief_hash` 不变式

`data_brief_hash` 是 `data_brief.json` **hash-payload 子集**的 canonical 序列化 sha256:

```python
HASH_PAYLOAD_KEYS = ("files_found", "scanner_manifest", "csv_summaries", "text_files_content")
```

LLM 加工的字段 (`central_claims`, `performance_numbers`, `candidate_anomalies`, `materials_system`, `manuscript_stage`) **不算**入哈希。这些字段在相同输入下是非确定性的, 模型侧 reproducibility 通过 `reproducibility.model_id` / `system_prompt_hash` 单独捕捉。

为什么重要: 这个保证让 CLI scaffold 路径 (`build_data_brief_scaffold`, 确定性) 和 mentor session 完整 pipeline (`build_data_brief`, 含 LLM 加工) 在同一 cwd snapshot 下产出相同的 `data_brief_hash`。同一份数据上跑多次 acceptance 锁得齐整。

> **Caveat: 这是单机 reproducibility。** `scanner_manifest` 含**绝对**文件路径,同一份数据集换台机器(或换 mount point)跑出来的 hash 就不一样。要真做到跨机器 reproducibility,底层 scan 路径要相对化 — v0.2 规划项。当前 hash 对「同一数据集、同一机器、多次 LLM 跑」(v0.1.3 acceptance 用例)够用,但不能 claim 成 universal。

### 11.2 `reproducibility` 块

`run_acceptance.save_run` 注入到落盘 payload:

```json
{
  "reproducibility": {
    "model_id": "<from $CLAUDE_MODEL_ID, default 'unknown'>",
    "model_version": "<from $CLAUDE_MODEL_VERSION, default 'unknown'>",
    "sampler_temperature": "<from $CLAUDE_TEMPERATURE, default 'default'>",
    "data_brief_hash": "<from --reproducibility-manifest>",
    "system_prompt_hash": "<sha256(SKILL.md)[:16]>",
    "pipeline_version": "0.1.3",
    "run_name": "<--run-name>"
  }
}
```

`system_prompt_hash` 从 `SKILL.md` 算 (仓库内或装在 `~/.claude/skills/thermal-mentor/SKILL.md`)。Fallback sentinel: `"skill_md_not_found"`。

### 11.3 N=3 稳定性测试

`--repeat 3` 从同一份 payload 写 3 份独立 acceptance run, 各打 `_run1` / `_run2` / `_run3`。V0.1.3 release validation 用:

```bash
python scripts/run_acceptance.py tmp/payload.json \
    --run-name "myproject_v0.1.3_data_first_20260525" \
    --reproducibility-manifest tmp/data_brief.json \
    --repeat 3
```

同 JSON payload + 同 SKILL.md = 同 `data_brief_hash` + 同 `system_prompt_hash`。N=3 之间渲染 Markdown 有任何差异, 都隔离到 verifier 或 renderer 的非确定性。

### 11.4 Audit log

`audit_log.py` 提供 JSONL append-only log, 在 `audit_log/<YYYY-MM>.jsonl`。每次 acceptance 追加摘要记录:

```json
{
  "type": "acceptance_run",
  "run_name": "...",
  "audit_log_id": "20260525-103200-xyz789",
  "mode": "data_first",
  "claims_count": 0,
  "json_path": "...",
  "md_path": "...",
  "timestamp": "2026-05-25T10:32:00"
}
```

`audit_log_id` 格式 `<YYYYMMDD>-<HHMMSS>-<6字符 alnum>`, 是 manifest CSV / resume instruction / 下游 lineage 的 canonical 标识。

---

## 12. 输出 schema

完整 schema 在 `references/output-schemas.md` (publication mode) 和 `references/output-schemas-data-first.md` (mode 0)。要点如下。

### 12.1 `data_brief.json`

```json
{
  "files_found": [{"path": "notes.txt", "type": "txt", "tokens": 1240}],
  "central_claims": [
    {"claim_text": "...", "source_file": "notes.txt",
     "quote_line": 12, "quote_verbatim": "..."}
  ],
  "performance_numbers": [...],
  "candidate_anomalies": [
    {"anomaly_id": "A1", "observation_short": "...",
     "observed_trend": "monotonic_decrease|monotonic_increase|non_monotonic|unknown",
     "expected_source_type": "defect-chemistry textbook|Shannon radii|...",
     "quote_verbatim": "...", "quote_source": "notes.txt:7",
     "quote_hash": "sha256:...",
     "expected_textbook_short": "...",
     "mentor_inference": "...",
     "surprise_score": "high|medium|low"}
  ],
  "materials_system": "doped oxide series",
  "manuscript_stage": "draft|plan|data-only|mixed",
  "data_brief_hash": "sha256:...",
  "scanner_manifest": {
    "cwd": "...",
    "files_glob_pattern": "**/*.{txt,md,docx,pdf,csv,xlsx}",
    "file_hashes": {"notes.txt": "sha256:..."},
    "scanner_version": "0.1.3",
    "timestamp": "2026-05-25T10:32:00Z"
  },
  "audit_log_id": "..."
}
```

### 12.2 Mode 0 payload

```json
{
  "mode": "data_first",
  "anomalies": [...6-field schema...],
  "hypotheses": [...含 predicts_observable...],
  "experiments": [...含 discriminates_between + answerable_by...],
  "cross_review": {...if Round 1-4 ran...},
  "mode_0_handover": {...if 'both' mode...},
  "reproducibility": {...},
  "audit_log_id": "..."
}
```

### 12.3 Publication payload

```json
{
  "mode": "novelty_review|highlight_mining|revision|direction_guidance|corpus_query",
  "verdict": {"one_line": "...", "confidence": "low|medium|high"},
  "claims": [
    {"claim_id": "C001", "claim_text": "...",
     "claim_type": "novelty|method|mechanism|performance|citation|limitation",
     "supporting_refs": [
       {"ref_id": "R001", "ref_type": "local_citekey|doi|openalex|user_manuscript",
        "value": "...", "verification_status": "verified|not_found|verifier_error"}
     ],
     "novelty_flag": "novel|not_novel|incremental|uncertain",
     "evidence_span": "exact quote or null",
     "confidence": "low|medium|high"}
  ],
  "prior_art_coverage": {...},
  "what_would_change_my_mind": [...],
  "audit_log_id": "..."
}
```

### 12.4 Mode-0 -> publication handover

Mode 0 在 `both` 模式跑完时, payload 顶层带 `mode_0_handover` 字段:

```json
{
  "mode_0_handover": {
    "central_claim_candidates": ["..."],
    "mechanism_claim_candidates": ["..."],
    "selling_point_candidates": ["..."],
    "existing_data_assets": ["..."],
    "materials_system": "...",
    "data_brief_hash": "sha256:..."
  }
}
```

Publication mode 读它, 预填 Level-2 `AskUserQuestion` 选项描述。用户仍能修改每个候选 —— handover 只是消除"系统忘了刚才聊啥"的摩擦。

---

## 13. 常见故障

### 13.1 测试挂了

- `ModuleNotFoundError: doi_verify_multisource` —— 确认 `scripts/` 在 `sys.path` 上 (pytest 由 `conftest.py` 处理)。Ad-hoc Python 调用要 `sys.path.insert(0, "scripts")`。
- `httpx.ConnectError` —— 网络断了或被限流。设 `OPENALEX_MAILTO` 走 polite pool。
- CSV 报 `UnicodeDecodeError` —— 文件是 GB18030 或其他非 UTF-8。`summarize_csv` 自动 fallback (UTF-8 -> GB18030 -> Latin-1)。
- `_llm_extract_anomalies NotImplementedError` —— 你直接调了 `build_data_brief`。CLI 场景用 `build_data_brief_scaffold`; 完整路径只给 mentor session 用。

### 13.2 Skill 在 `/thermal-mentor` 没激活

- 检查 `ls ~/.claude/skills/thermal-mentor/SKILL.md` 存在。
- 重启 Claude Code (skill registry 在 session 启动时加载)。
- 检查 `SKILL.md` frontmatter 是 `name: thermal-mentor` (case-sensitive)。

### 13.3 某个 DOI 核验卡住

- 看 `cache/doi_verify/<hash>.json`。如果 status=`verifier_error` 但被缓存了, 这是 bug, 应报告。
- 删掉缓存重跑: `rm cache/doi_verify/*.json`。

### 13.4 `data_brief_hash` 在 CLI scaffold 和 mentor session 之间不一致

设计上不该发生。如果出现:

- 检查 `anomaly_brief.py` 里 `HASH_PAYLOAD_KEYS` —— 应该是 `("files_found", "scanner_manifest", "csv_summaries", "text_files_content")`。
- 确认 CSV 没有 None-key 列 (DictReader 在 header 有空字段时会产生)。`_stringify_keys` 处理这个 —— 验证它跑了。

### 13.5 Cross-review reviewer 超时

- Codex GPT-5 xhigh: 30-90 分钟, 偶尔 stdout deadlock; `codex:codex-rescue` 有重试。
- Opus subagent: 5-30 分钟, 看 payload 大小。
- DeepSeek V4 Pro: 5-15 分钟通过 API; 需要父 session env 里有 `DEEPSEEK_API_KEY`。

某 reviewer 没返回, mentor 用剩下的 reviewer 继续, merged JSON 里记一笔 omission。

---

## 14. 扩展开发

### 14.1 加一个新 DOI 核验源

1. 在 `scripts/doi_verify_multisource.py` 实现 lookup 函数:

```python
def datacite_lookup(doi: str, timeout: float = DEFAULT_TIMEOUT) -> SourceLookupResult:
    url = f"https://api.datacite.org/dois/{doi}"
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as cli:
        r = cli.get(url)
        if r.status_code == 200:
            data = r.json()
            if data and data.get("data"):
                return SourceLookupResult(True, data["data"])
        return SourceLookupResult(False, None)
```

2. 加进 `_build_chain()`:

```python
Source("datacite", datacite_lookup, False),  # 非权威
```

3. 在 `tests/test_doi_verify_multisource.py` 加 mock httpx Client 的单测。

### 14.2 加一个新 mode

1. 在 `references/output-schemas.md` (或新文件) 定 schema。
2. 在 `scripts/verifier.py` 加 `verify_<mode>` 函数。
3. 加进 `verifier.py` 顶部的 `MODE_DISPATCH` 表。
4. 加 `render_markdown_<mode>` 函数。
5. 更新 `SKILL.md` Level-1 mode 选项。
6. 在 `tests/test_verifier_mode_dispatch.py` 加单测。

### 14.3 加一个新 mode 0 指标

1. 在 `scripts/eval_runner.py` 加纯函数:

```python
def compute_<metric_name>(payload: dict) -> float:
    ...
    return round(value, 3)
```

2. 在 `tests/test_mode_0_metrics.py` 加单测。

### 14.4 改 skill 名字

如果你 fork 后想重命名:

1. 改仓库目录名。
2. 改 `SKILL.md` frontmatter `name: <new-name>` 和 `description: ...`。
3. 改 `references/*.md` 和 `docs/MANUAL*.md` 里所有 slash-command 引用。
4. 如果你把 `scripts/` 改名, 改 Python import path。

---

*Manual last updated for v0.1.3.*
