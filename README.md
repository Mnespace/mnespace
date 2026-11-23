# Mnespace

**Generative memory that acts.**

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

> **Mnespace** = *mneme* (memory) + *space*. The name renders the theory's core construct **meta-space (元空间)** as what it actually is: a space of memory, not an abstract "meta". This repository is the open-source release of the paper **Generative Memory Theory: How Agents Construct Memory in Meta-Space to Generate Intelligent Behavior**.

**English is the default language of this repository.** A Chinese version is provided alongside ([生成性记忆理论.md](生成性记忆理论.md)).

---

## What is this?

Most agent systems treat **knowledge** — documents, ontologies, retrieved facts — as the thing that guides action. **Generative Memory Theory (GMT)** inverts this: the substance guiding intelligent behavior is **generative memory**, an associative structure the agent continually **constructs** through interaction with the digital and physical worlds. **Meta-space** is the functional setting where this construction happens and where memory is organized to guide perception, imagination, and action.

The paper is a **theory with falsifiable hypotheses**, not a finished system. It offers a functional model, eight research propositions with matched-control experiments, a reference architecture, and an evaluation design.

## Read the paper

| Language | Markdown | Word |
| --- | --- | --- |
| **English (default)** | [GenerativeMemoryTheory.md](GenerativeMemoryTheory.md) | [GenerativeMemoryTheory.docx](GenerativeMemoryTheory.docx) |
| 中文 | [生成性记忆理论.md](生成性记忆理论.md) | [生成性记忆理论.docx](生成性记忆理论.docx) |

## Core ideas

- **Generative memory, not a store.** Behavior arises from memory; knowledge is the *articulated export* of memory, not its runtime substance. Reading a manual once does not create the structure that handles exceptions.
- **Meta-space `M = (G, F)`.** `G` is an associative network of cue–action–consequence links that persist across events; `F = (S, A, T, V, κ; N)` organizes how those links are used for situation discrimination, prospective simulation, valuation, self-competence, and role.
- **Activation → selection → expression.** `Act(G, c)` evokes a judgment basis; `Gate(P_int, r, c)` selects what is worth saying to a listener in a scene; `Read(P_out)` forms the utterance or action.
- **Construction dynamics.** Feedback drives **sedimentation**, **calibration**, and **restructuring** — distinguished from transient prompt effects and institutional authorization changes.
- **Contextual articulation.** The same memory yields different content for different listeners/scenes because *communicative need* differs — not because of secrecy. Formal disclosure rules constrain expression only where applicable; a combination can be sensitive even when each item is public (the mosaic effect).
- **Acquisition.** A recipient rebuilds capability through demonstration, practice, and feedback; the criterion is delayed retention and unprompted transfer, not repeating an explanation.
- **Eight propositions (P1–P8)** with causal-intervention tests (connection swapping, cross-task directed transfer, paired yoked-review controls).

## Figures

![Four-figure overview](figures/overview.png)

| # | Figure | Topic |
| --- | --- | --- |
| 1 | [Mechanism](figures/01_mechanism.png) | Action–feedback loop and cross-agent articulation/acquisition |
| 2 | [Association](figures/02_association.png) | Associative activation and compositional disclosure |
| 3 | [Learning dynamics](figures/03_learning_dynamics.png) | Sedimentation, calibration, restructuring |
| 4 | [Articulation](figures/04_articulation.png) | One trip memory, three communicative tasks |

Editable vector sources (`.svg`) and the generator (`render_en.py`) are in [`figures/`](figures/). Chinese figures are in [`论文配图/`](论文配图/).

## Repository contents

```
.
├── GenerativeMemoryTheory.md     # paper (English, default)
├── GenerativeMemoryTheory.docx   # paper (Word, figures + superscript citations)
├── figures/                      # English figures (PNG + SVG) + render_en.py
├── 生成性记忆理论.md              # paper (Chinese)
├── 生成性记忆理论.docx            # paper (Chinese, Word)
├── 论文配图/                      # Chinese figures (PNG + SVG) + render.py
├── README.md
├── CITATION.cff
└── LICENSE                       # CC BY 4.0
```

Citations are rendered as superscripts (GB/T 7714 numeric style) in the Word files; 77 authoritative references are listed and cross-checked.

## Status & scope

- This is a **functional theory of intelligent behavior**, not a claim about phenomenal consciousness.
- The AGI claim is a **necessity hypothesis** (generative memory is necessary for intelligent behavior), explicitly *not* a sufficiency claim. Section 9.4 states its falsification condition.
- The reference architecture (GMT-LLM) is **proposed**, not implemented here. Code may follow in future releases.

## Citation

If you use this work, please cite it (see [`CITATION.cff`](CITATION.cff)):

```bibtex
@misc{wang2026generative,
  title  = {Generative Memory Theory: How Agents Construct Memory in Meta-Space to Generate Intelligent Behavior},
  author = {Wang, Yang},
  year   = {2026},
  url    = {https://github.com/Mnespace/mnespace},
  note   = {Open-source theory paper, CC BY 4.0}
}
```

## License

The paper text and figures are licensed under **[CC BY 4.0](LICENSE)** — you may share and adapt with attribution. Any future code will be licensed separately (likely MIT).

---

## 中文简介

**Mnespace**（mneme 记忆 + space 空间）是论文《生成性记忆理论：元空间中的记忆建构与智能行为生成》的开源仓库，**默认英文**，中文版见 [生成性记忆理论.md](生成性记忆理论.md)。理论主张：指导智能行为的实体不是知识存储，而是智能体在与数字世界和物理世界交互中主动建构的**生成性记忆**；**元空间**是这一建构发生、记忆被组织以指导感知、想象与行动的功能场域。核心机制包括 `M=(G,F)` 的功能结构、`Act→Gate→Read` 的激活与表达选择、沉淀/校准/重塑的建构动力学、**情境化言传**（同一记忆因沟通需要而非密级对不同听者呈现不同内容）与**习得**（以延迟保持和无提示迁移为判据）。论文给出八条可证伪命题及对照实验设计。许可证 CC BY 4.0。
