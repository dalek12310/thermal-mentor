# Ask-first prompt banks

Three levels, every invocation. Use `AskUserQuestion` to enforce option-based answers.

## Level 1 — Mode

Question: 你想让我做什么？

Header: 模式

Options:
1. novelty — 评估创新性 / 是否已被发表
2. highlight — 找亮点 / 包装一句话 narrative
3. revision — 改论文
4. direction — 方向建议
5. corpus_query — 文献延展

## Level 2 — Per-mode clarifier

### novelty

Q1: novelty 的定义？
- (a) 第一次提出观点
- (b) 第一次用方法/数据
- (c) 第一次在你的材料体系上 demonstrate

Q2: 失败容忍度？
- 不容忍误报（保守）
- 容忍 5%
- 容忍 10%

Q3: 目标期刊？（仅用于 ceiling estimate，放最后避免框死整个 eval）
- Nat Mater
- Nature Communications
- Advanced Materials
- JACS / ACS Nano / Nano Lett
- 其他（自填）

### highlight

Q1: 卖点：
- mechanism
- performance number
- methodology novelty
- multi-functional coupling

Q2: 目标期刊（同上，放最后避免被 framing 带偏）

### revision

Q1: 改哪部分？
- 语言（English polishing）
- 论证逻辑
- figure narrative
- 全部

Q2: 目标期刊（同上，放最后避免被 framing 带偏）

### direction

Q1: 哪个方向？
- A: DFT phonon + ML potentials
- B: thermoelectric
- C: interface + 2D
- D: topological / chiral phonon
- E: phonon-induced superconductivity

Q2: 时间窗口？
- 6 个月
- 12 个月
- 24 个月

### corpus_query

Q1: 查询类型？
- anchor researcher (输入名字)
- keyword
- DOI
- citekey

## Level 3 — Input source

Header: 输入

Options:
1. folder — 项目文件夹路径
2. question + text — 问题 + 一段手写文本
3. manuscript — manuscript 文件路径 (docx/pdf/md)
4. from-corpus — 现有 citekey
5. review-pdf — 外部 PDF 文件路径
