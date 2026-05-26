# thermal-mentor

[![Tests](https://img.shields.io/github/actions/workflow/status/dalek12310/thermal-mentor/test.yml?label=tests&logo=github)](https://github.com/dalek12310/thermal-mentor/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-skill-7c3aed.svg)](https://docs.claude.com/en/docs/claude-code/skills)
[![v0.1.3](https://img.shields.io/badge/version-0.1.3-brightgreen.svg)](CHANGELOG.md)

> Claude Code skill — 给科研稿件做**数据优先**的导师会话工具。
> 面向材料、物理、化学、工程等方向的研究者。

[English version](README.md) · [完整中文手册](docs/MANUAL_zh-CN.md) · [Full English Manual](docs/MANUAL.md)

---

## 这玩意儿干啥用

在 Claude Code 里调 `/thermal-mentor`,skill 会跑一套**三步反思式路由**:

1. **Step 0** — 扫你当前目录的稿件 (`.docx/.pdf/.md/.txt`) 和实验数据 (`.csv/.xlsx`),建一个 `data_brief.json` 骨架。Mentor session (LLM, 也就是你) 来填异常提取的部分。

2. **Step 0.5** — 给用户一屏阅读:扫到的文件 + 关键 claim (含来源引用) + 候选 anomaly (含原文 verbatim)。用户可以打断纠正。

3. **Step 1** — 内心独白推断用户意图 (case A/B/C/D), 然后用 `AskUserQuestion` 给 2-4 个量身定制的选项。每个选项含 verbatim 原文 + mentor 解读两栏。

然后路由到两条 pipeline 之一:

- **Mode 0 (data-first)** — anomaly 枚举 -> hypothesis 枚举 -> 区分实验 -> 可选 cross-review -> verifier -> 审计日志
- **Publication-strategy mode** — v0.1 原有 workflow, 做 novelty review / highlight / revision / direction / corpus query

或者 **both** — 先 mode 0, 再 publication strategy 接力。

## 核心特性

### 多源 DOI 核验

DOI 多源验证链: 4 个常驻源 (OpenAlex / Crossref / Semantic Scholar / DOI.org HEAD) + 2 个 env-gated 源 (Lens.org 需 `LENS_API_TOKEN`, Web of Science 需 `WOS_API_KEY`)。权威 `not_found` 语义 (Crossref + DOI.org HEAD = 真值)。本地缓存 24 小时。网络异常时显式返回 `verifier_error` (不会偷偷映射成 `verified`)。

### 数据驱动的导师推理

Mode 0 主动在数据里找**反课本的惊喜** —— 用户测出来的现象和教科书预测冲突的位置。每个 anomaly 都按 6 字段 schema 填: `observation` / `expected_textbook` / `surprise_score` / `data_evidence` / `mentor_inference` / `context_questions_to_user`。

### 圆桌审稿 (cross-review)

独立审稿人 (Opus / Codex / DeepSeek) 并行 critique mentor 输出 (Round 1), 看完彼此的 finding 再表态 (Round 2), 然后 Python merge + 对称 DOI 归属 (Round 3-4)。引用归属上无审稿人歧视。

### paper-pdf-acquisition 联动

Mentor 需要某篇 paper 全文但拿不到时, 生成 CSV manifest (`doi, citekey, why_needed, expected_section, resume_token`), 用户开新 session 跑 `/paper-pdf-acquisition` 拿全文, 完成后回本 session 接续。

### Reproducibility lock (复现锁)

`data_brief_hash` 只对**扫描器决定的不变量**做哈希 (文件 SHA256, CSV summary, 文本内容)。LLM 写入的字段不算入哈希, 因此同一目录跑多次 mode 0 的 brief hash 总相等。`run_acceptance.py` 支持 `--repeat N` 做稳定性测试。

### 人话硬规则

面向用户的文案 (Markdown 渲染, `AskUserQuestion` 选项) 必须是中文/英文人话 —— 不出现内部 codename (`mode_0`, `L1/L3`, `anomaly_brief`)。专业术语 (DFT, XAFS, XPS, phonon) 保留。

## 安装

### 装成 Claude Code skill (推荐)

```bash
git clone https://github.com/dalek12310/thermal-mentor.git ~/.claude/skills/thermal-mentor
# 重启 Claude Code; skill 在 /thermal-mentor 调用时自动激活
```

### 当独立 Python 库用

```bash
git clone https://github.com/dalek12310/thermal-mentor.git
cd thermal-mentor
pip install -e .

# 跑单测 (不需要联网, 不需要 corpus, 应当 pass)
pytest tests/ -v
```

要求 Python >= 3.10。

## 配置 (环境变量)

下面所有变量都是可选的, 不设置也能跑, 但功能会降级:

| 变量名 | 用途 | 不设置时的行为 |
|---|---|---|
| `OPENALEX_MAILTO` | OpenAlex / Crossref polite pool 用的邮箱 | 匿名池 (限流, 慢) |
| `THERMAL_MENTOR_CORPUS` | 本地 corpus 目录 (含 `distillation_corpus_v2.csv` + `retraction_blacklist.yaml`) | publication 模式的本地 citekey 检查返回 `not_found`; mode 0 不受影响 |
| `LENS_API_TOKEN` | Lens.org Scholarly API token | L3 fan-out 跳过 Lens 源 |
| `WOS_API_KEY` | Web of Science Starter API key | 跳过 WoS 源 |
| `CLAUDE_MODEL_ID`, `CLAUDE_MODEL_VERSION` | acceptance 跑的 reproducibility 块记录 | 记成 `"unknown"` |

可以写进 shell profile (`.bashrc` / `.zshrc`), 也可以在仓库根目录建个 `.env` 文件 (`.env` 已在 `.gitignore` 里)。

## 快速上手

### 1. 装成 Claude Code skill 用

在任何 Claude Code session 里调 `/thermal-mentor`。Skill 会自动扫 CWD 给你路由。

### 2. 当 CLI 工具用

```bash
# 第一步: 扫数据目录, 输出 scaffold
python scripts/anomaly_brief.py path/to/your/data/dir --out tmp/data_brief.json --include-text

# 第二步: 手改 tmp/data_brief.json (或者让 skill session 通过 Claude 加工)
#   - 填 central_claims, candidate_anomalies, materials_system, manuscript_stage

# 第三步: 跑 mode 0 verifier
python scripts/verifier.py tmp/payload.json

# 第四步: 落盘 acceptance run, 带 reproducibility manifest
python scripts/run_acceptance.py tmp/payload.json \
    --run-name "myproject_v1_data_first_run1" \
    --reproducibility-manifest tmp/data_brief.json \
    --repeat 3   # N=3 重复跑做稳定性测试

# Cross-review 合并 (收集到审稿人 JSON 之后)
python scripts/cross_review_merge.py \
    tmp/round1_opus.json tmp/round1_codex.json tmp/round1_ds.json \
    --out tmp/cross_review_final.json
```

## 目录结构

```
thermal-mentor/
|-- SKILL.md                 # Claude Code skill 入口
|-- README.md                # 英文版 README
|-- README_zh-CN.md          # 本文件
|-- LICENSE                  # MIT
|-- pyproject.toml           # Python 包配置
|-- scripts/                 # 11 个 Python 模块
|   |-- anomaly_brief.py     # Step 0 扫描器 + data_brief scaffold + summarize_csv
|   |-- audit_log.py         # JSONL append-only 审计日志
|   |-- cross_review_merge.py  # Round 3-4: finding 分类 + 对称 DOI 归属 + Markdown 渲染
|   |-- doi_verify_multisource.py  # 6 源 DOI 核验链 + 24h 缓存
|   |-- eval_runner.py       # Mode 0 指标 (anomaly_recall, hypothesis_completeness, ...)
|   |-- live_search.py       # L3 fan-out: OpenAlex/S2/arXiv + 可选 Lens/WoS
|   |-- manuscript_brief.py  # 文档文本提取 (.docx/.pdf/.md/.txt)
|   |-- paper_pdf_handoff.py # Manifest CSV + resume instruction
|   |-- run_acceptance.py    # 落盘 JSON+MD + reproducibility 块 + N-repeat
|   `-- verifier.py          # Mode 分发 + verify_mode_0 + verify_payload (publication)
|-- references/              # 7 篇设计文档
|   |-- ask-first-prompts.md
|   |-- data-first-prompts.md
|   |-- output-schemas.md
|   |-- output-schemas-data-first.md
|   |-- user-facing-language.md
|   |-- cross-review-protocol.md
|   `-- pdf-acquisition-handoff.md
|-- docs/
|   |-- MANUAL.md            # 完整英文使用手册
|   `-- MANUAL_zh-CN.md      # 完整中文使用手册
`-- tests/                   # 64 个单测, 无外部依赖
    |-- conftest.py
    |-- fixtures/sample_dataset/
    `-- test_*.py
```

完整英文手册见 [`docs/MANUAL.md`](docs/MANUAL.md), 完整中文手册见 [`docs/MANUAL_zh-CN.md`](docs/MANUAL_zh-CN.md)。

## 跑测试

```bash
pytest tests/ -v
# 期望: 64 passed
```

测试都用 mock 过的 `httpx` 客户端 + 通用 `sample_dataset` fixture, 不需要联网, 不需要 corpus。

## 路线图 (v0.1.4+)

- `audit_log` 记录里加 `pipeline_version` 字段
- DataCite / mEDRA DOI 源扩展
- Reproducibility 块再加 Python 版本 + 依赖哈希 + 随机种子
- SKILL.md 镜像漂移的 pre-commit hook
- `verifier_error_metadata` 传播的防御不变式

## 引用

如果本工具帮到你的科研流程, 请引用:

```bibtex
@software{thermal_mentor_2026,
  author = {thermal-mentor contributors},
  title = {thermal-mentor: Reflective routing + data-first mode for scientific manuscript mentor sessions},
  year = {2026},
  version = {0.1.3},
  url = {https://github.com/dalek12310/thermal-mentor}
}
```

## 贡献

欢迎 issue / PR。提之前请先读 `references/` 下的设计文档。

## License

MIT — 见 [LICENSE](LICENSE)。
