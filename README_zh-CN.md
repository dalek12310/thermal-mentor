# science-mentor

[![Tests](https://img.shields.io/github/actions/workflow/status/dalek12310/science-mentor/test.yml?label=tests&logo=github)](https://github.com/dalek12310/science-mentor/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-skill-7c3aed.svg)](https://docs.claude.com/en/docs/claude-code/skills)
[![v0.2.0](https://img.shields.io/badge/version-0.2.0-brightgreen.svg)](CHANGELOG.md)

> **一个会读你实验数据的 Claude Code 导师：它找出你的测量与教科书预测矛盾的地方，把每个意外
> 变成一个可证伪的假设 + 一个能区分机制的实验——而且每条引用都经最多 6 个来源交叉核验
> （4 个常驻 + 2 个需 API key），绝不编造。**

它跑的是一套有牙齿的**科学方法流程**：**每条引用都由代码多源核验、绝不编造**；同时 skill 的
硬规则要求每个结论都要有逐字引用、每个机制都要有可证伪的预测。

*关于适用范围，说实话：* 发现 + 核验这套引擎是领域通用的（后端处理的是通用 CSV 列、通用文本、
通用 DOI）。但随包附带的 prompt 示例和可选的 publication 语料是**物理 / 材料学口味**的——
其他领域能用，但配一个领域包会更好。

[English version](README.md) · [完整中文手册](docs/MANUAL_zh-CN.md) · [Full English Manual](docs/MANUAL.md)

---

## 它解决什么问题

你手里有原始数据和一份草稿，却分不清这是一篇 *Nature Materials* 级的故事，还是一篇普通论文——
而真正能给你判断的人都很忙。

于是你去问 LLM，得到的往往是两种没用的回答：

- **空洞的鼓励**——"这看起来是篇很棒的论文！"
- **套路的批评**——"多引点文献、把讨论收紧一点。"

这两种都**没真的看你的数字**。`science-mentor` 从你的数据出发：它找出你的测量与理论预测不符的
地方，从这些"意外"往前推理——就像一个好导师俯身看你的图时会做的事。

## 它跟别的不一样在哪

- **它先读数据，再开口。** 先跑一遍对你目录的确定性扫描（每一列做趋势检测、从你的笔记里摘出
  原文），**然后**才问你想干什么。带动对话的是你数据里最反常的那个点，而不是一个模板。
- **每个"机制"都自带一把能弄死它的刀。** 对每个候选解释，它会列出"如果这个机制成立，你还应该
  在数据里看到什么"，让你能自己去核对、而不是只能信模型——然后给出一个能把竞争机制分开的实验
  （优先选你用已有数据就能回答的）。
- **它编造不了引用。** 每条文献都经 OpenAlex → Crossref → Semantic Scholar → DOI.org
  （有 key 还会加 Lens / Web of Science）核验。核验不了的直接剔除、绝不蒙；网络故障就如实
  报成网络故障，绝不偷偷升级成"已核验"。

## 一个实战示例

假设你目录里有一份 4 行的掺杂序列 CSV：

```csv
sample,dopant_pct,lattice_param_A,conductivity_Scm,activation_eV
S0,0,12.974,1.8e-4,0.42
S2,2,12.961,2.7e-4,0.38
S4,4,12.945,3.5e-4,0.34
S6,6,12.926,4.2e-4,0.31
```

你调用 skill。它给你的不是"很有前景！"，而是：

> **反常（高 surprise）。** 晶格随掺杂*收缩*，电导率却*涨了 4 倍*，活化能*降*了 0.42 → 0.31 eV。
> *教科书预期：* 晶格更紧 → 离子通道更窄 → 迁移势垒应当**升高**。证据：`data.csv`，
> `activation_eV` 列单调下降。
>
> **两个竞争机制——**
> *H1：局域畸变形成新渗流路径。* 若成立，你还应看到高掺杂下 PDF 峰展宽、出现新的 Raman 模。
> *H2：载流子浓度跃升。* 若成立，Hall 测量应显示载流子密度涨约 4 倍。
>
> **一个能区分它俩的实验：** 对同样这 4 个样品做 Hall。载流子密度持平 ⇒ H1；涨约 4 倍 ⇒ H2。
> *（标准四点装置就能答，不用重新合成。）*
>
> **这新颖吗？** 已有两篇报道过电导率上升，但都没有把它和"晶格收缩下 E_a 反降"配在一起——
> *这个配对*才是没人占的角度。*（引用：`10.xxxx/...` 已核验，`10.yyyy/...` 已核验。）*

这就是"聊天机器人"和"导师"的差别：一个扎根于*你自己的数据行*、引用可信、可证伪的下一步。

## 快速上手——当 Claude Code skill 用（推荐）

```bash
git clone https://github.com/dalek12310/science-mentor.git ~/.claude/skills/science-mentor
# 重启 Claude Code，然后在一个有你数据 + 草稿的目录里：
```

```
你: /science-mentor
导师: [静默扫描目录]
      基于你的数据，你想让我做什么？
        1. 深挖你电导率 vs 晶格数据里那个反常结果  (推荐)
        2. 评估这篇稿子能投哪
        3. 两个都要——先深挖，再聊策略
        4. 别的
你: 1
导师: [反常 → 候选机制 → 区分实验，如上]
```

它会扫你当前目录，把扫到的东西摊给你看（带原文，你可以纠正），推断你的意图，然后路由你。
每一步你都说了算。

## 你能得到什么：两种模式

| 模式 | 它替你做什么 |
|---|---|
| **发现模式**（数据优先） | 把你的原始数据变成：与预期矛盾的反常 → 各带一条自检预测的竞争机制 → 每个反常一个区分实验。适合"有数据、想搞清到底发生了什么"。 |
| **出版策略模式** | 诚实的新颖性评估、卖点挖掘、改稿、方向建议——扎根你的数据、不跟期刊吹捧走。适合"有草稿、想知道能投哪"。（用一个可选的本地语料，物理/材料口味。） |

也可以**两个都跑**：先发现、再让策略接着发现的结论往下走。

## 我们怎么保证它诚实

下面这些有的是代码强制、有的是 skill 每步必须遵守的硬规则，不靠自觉：

- **不编造引用。** 多源 DOI 核验；核验不了的剔除并记录，网络错误如实报成"校验器报错"、不隐藏。
- **不拍马屁。** 一条硬规则禁止为了鼓励你而夸大新颖性；如果文献显示你的结果已经发表了，它直说。
- **可复现。** 对确定性扫描算 `data_brief_hash`，让你重跑同一批数据能得到同一个起点；模型/版本
  溯源单独记录。
- **说人话。** 面向用户的输出绝不漏内部 codename；专业术语（DFT、XAFS、phonon……）保留。

## 进阶：当 Python 脚本 / CLI 用

扫描 → 核验 → 落盘这条管线也能在 checkout 里脱离会话直接跑：

```bash
git clone https://github.com/dalek12310/science-mentor.git
cd science-mentor && pip install -e .
pytest tests/ -v          # 77 passed——不需联网、不需 corpus

# 扫数据目录成 scaffold
python scripts/anomaly_brief.py path/to/data --out tmp/data_brief.json --include-text
# （由 mentor session、或你手工，填入 claims + anomalies）
python scripts/verifier.py tmp/payload.json                      # 核验 + 渲染
python scripts/run_acceptance.py tmp/payload.json \
    --run-name "myproject_run1" --reproducibility-manifest tmp/data_brief.json --repeat 3
```

完整的端到端走查见 [`docs/DEMO.md`](docs/DEMO.md)。

## 安装与配置

要求 Python ≥ 3.10。所有环境变量都是**可选**的——不设也能跑、只是功能降级（例如不设 corpus ⇒
本地 citekey 检查返回 `not_found`，发现模式不受影响）。完整表见
[手册](docs/MANUAL_zh-CN.md)；最常用的一个：

```bash
export OPENALEX_MAILTO="you@example.com"   # DOI 核验更快、更友好
```

## 底层原理

给想看机制的读者（用它并不需要懂这些）：

- **三步反思式路由**——*Step 0* 确定性扫描 → *Step 0.5* 把"读到的东西"摊给你（文件、claim、
  候选反常，都带原文）→ *Step 1* 推断意图（case A/B/C/D），给出量身定制的选项，每个都锚定
  一条逐字引用 + mentor 解读，让你能分别质疑"证据"和"解读"。
- **Mode-0 管线**——反常枚举 → 假设枚举（带 `predicts_observable`）→ 区分实验 → 可选交叉评审
  → verifier → 审计日志。
- **圆桌交叉评审**——独立 reviewer 并行 critique，再互看彼此的 finding，最后由确定性 merge 按
  一致度分级置信（全同 / 多数 / 孤证），引用归属不歧视任何 reviewer。
- **paper-pdf-acquisition 联动**——需要全文时，生成 manifest CSV 让你去单独跑
  `/paper-pdf-acquisition`，而不是卡住当前会话。

设计文档见 [`references/`](references/)；完整协议见 [`docs/MANUAL_zh-CN.md`](docs/MANUAL_zh-CN.md)。

## 项目信息

```
science-mentor/
├── SKILL.md            # Claude Code skill 入口
├── scripts/            # Python 后端（扫描器、verifier、DOI 链、交叉评审……）
├── references/         # 设计文档（路由、schema、交叉评审、人话规则）
├── docs/               # 手册（中/英）、DEMO 走查、blog 笔记
├── examples/           # demo 用的样例数据集
└── tests/              # 77 个单测——不需联网、不需 corpus
```

- **跑测试：** `pytest tests/ -v` → 77 passed（mock 过的 `httpx` + 通用样例 fixture）。
- **路线图（v0.1.4+）：** audit 记录加 `pipeline_version`；DataCite/mEDRA DOI 源；跨机复现
  （相对化扫描路径）；可插拔的每领域包。
- **贡献：** 欢迎 issue / PR——提之前请先读 `references/` 下的设计文档。
- **License：** MIT——见 [LICENSE](LICENSE)。

## 引用

```bibtex
@software{science_mentor_2026,
  author  = {science-mentor contributors},
  title   = {science-mentor: a code-enforced scientific-method engine (data-first anomaly →
             hypothesis → discriminating experiment) for Claude Code},
  year    = {2026},
  version = {0.2.0},
  url     = {https://github.com/dalek12310/science-mentor}
}
```
