---
name: arxiv
description: "用于检索学术文献、提取论文核心摘要并输出结构化文献分析报告。"
version: 1.2.0
author: Hermes Agent (融合 Hub literature-research-pipeline 规范)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [arxiv, 学术文献, 论文检索, 文献分析, 科研调研, 论文摘要]
    category: research
    related_skills: [grounded-citations, pdf]
---

# 学术文献检索与多维分析技能（arXiv Research）

## 概述

使用 arXiv 官方开放接口与多源文献检索工具，检索全球最新计算机科学、人工智能、数学与物理学领域的预印本文献。提取论文元数据、结构化解析核心算法与创新点，并生成包含背景、方法、实验基准与局限性分析的完整中文文献调研报告。

**核心准则**：
- **学术依据准确**：所有论文必须附带合法的 arXiv 唯一编号（如 `2402.03300`）与官方 PDF 直达链接；
- **结构化深度提炼**：严禁机械翻译长篇摘要，必须提炼出“研究动机、核心技术突破、实验基准对比与工程实施局限”四大核心要素。

## 适用场景

- “检索近期关于混合专家（MoE）注意力机制优化的前沿论文”
- “查找某篇特定编号论文并输出中文深度精读报告”
- “调研某项特定技术（如推测解码、长文本缓存压缩）的学术发展脉络与各方案对比”

---

## 一、 常用检索操作与指令

### 1. 精准字段检索（REST 接口调用）
利用 `curl` 结合 Python 脚本直接请求 arXiv 官方接口并解析输出：

```bash
# 1. 综合关键词检索（最新 5 篇）
curl -s "https://export.arxiv.org/api/query?search_query=all:mixture+of+experts+sparse+attention&max_results=5&sortBy=submittedDate&sortOrder=descending"

# 2. 按指定论文编号（arXiv ID）提取单篇详情
curl -s "https://export.arxiv.org/api/query?id_list=2402.03300"
```

### 2. 检索语法前缀规范
- `ti:` —— 限定仅搜索论文标题（如 `ti:"mixture of experts"`）
- `au:` —— 限定搜索特定作者姓名（如 `au:vaswani`）
- `abs:` —— 限定在摘要内容中检索
- `cat:` —— 限定特定学术分类（如 `cat:cs.AI` 人工智能，`cat:cs.CL` 计算语言学，`cat:cs.DC` 分布式计算）

---

## 二、 学术文献多维结构化分析范式

当对检索到的高价值论文进行精读汇报时，必须按照以下四个维度输出中文结构化分析：

```markdown
# [论文中文译名] 深度解析报告
- **原版标题**：[Original Paper Title]
- **arXiv 编号**：[例如：2402.03300] | **发表日期**：[YYYY-MM-DD]
- **核心作者与机构**：[机构名称，如 DeepSeek-AI / Google Research]
- **文献链接**：[PDF 官方直达链接]

### 1. 研究背景与核心问题（Motivation）
- 该论文试图解决现有技术体系中的什么核心瓶颈？（例如显存占用过高、多机通信延迟大、模型泛化能力不足等）；
- 既有前人方案的不足之处在哪里。

### 2. 核心方法与技术突破（Methodology）
- 论文提出的新型模型架构、数学推导公式或调度算法细节；
- 相比传统方法的本质机理差异（附带关键流程图或伪代码说明）。

### 3. 实验设计与性能基准（Benchmark Results）
- 论文采用的测试数据集与对比基准模型；
- 取得的确切实验对比数据（如吞吐提升百分比、上下文长度扩展规模、困惑度降低幅度等）。

### 4. 工程实施局限性与借鉴意义（Limitations & Insights）
- 该算法对硬件加速卡（如显存带宽、算子指令集）的特定依赖门槛；
- 实际应用在私有化生产部署中可能面临的挑战与借鉴价值。
```

---

## 三、 自检核对清单

- [ ] 检索到的文献是否均包含真实有效的 arXiv 编号与官方 PDF 访问链接？
- [ ] 论文摘要与分析是否采用纯正书面中文表达，消除了所有机器直译腔调？
- [ ] 实验数据结论是否严格对照原文表格，未凭空夸大或篡改基准数据？
