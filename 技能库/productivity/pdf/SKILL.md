---
name: pdf
description: "PDF 文档处理：结构化生成、中文双栏版面解析、表格抽取、表单填写与多模态办公格式转换。"
version: 1.2.0
author: Hermes Agent (融合 Hub pdf-processor-cn-tool-free)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pdf, 中文解析, 双栏识别, 表格提取, 表单填写, pdf_to_office]
    category: productivity
    related_skills: [docx, xlsx, powerpoint, document-to-action-items]
---

# PDF 文档处理技能（PDF Skill）

## 概述

基于 Python 原生库（`pypdf`、`reportlab`、`pdfplumber`）与多模态视觉流水线，提供 PDF 文档的全生命周期处理能力：包括基于结构化配置生成 PDF、处理包含中文复杂版面（双栏、三线表、多层标题）的文档解析、表单生成与填充、页面提取合并、图章水印以及转换为可编辑 Office 格式。

**核心原则**：
1. **涉及 Office 格式转换必须走多模态视觉流水线**：严禁使用纯文本抽取库机械提取 `.docx`、`.xlsx` 或 `.pptx`；
2. **中文文本断行修复**：针对中文 PDF 抽取常见的“硬换行断句”问题，执行基于标点符号与几何坐标的语义流式重组；
3. **表格与双栏坐标还原**：多栏排版优先按阅读顺序进行分块识别，防止左右栏文字交错混杂。

---

## 一、 多模态 PDF 转 Office 强制流水线（Office Conversions）

当需要将 PDF 转换为可编辑的 Microsoft Office 格式（`.docx`、`.xlsx`、`.pptx`）时，**必须调用 `pdf_to_office` 原生工具走多模态视觉流水线**，杜绝纯文本机械抽取：

1. **页面图像渲染（`render_pages`）**：
   - 调用 `pdf_to_office(action="render_pages", pdf_path="...", pages="all", dpi=150)`；
   - 引擎将页面渲染为 150 DPI 高清图像保存在临时目录，保留全部几何排版、文字字号、色彩与表格线框。
2. **多模态版面语义识别**：
   - 调用模型视觉通道（`vision_analyze`）直接识别排版要素：
     - **转 Word（`docx`）**：识别真实的阅读顺序、标题层级（一级至三级）、正文段落与表格结构；
     - **转 Excel（`xlsx`）**：识别表格边界、表头行、数据单元格原生类型（数字、日期、金额），去除千分位逗号，确保数字可计算；
     - **转 PowerPoint（`pptx`）**：识别幻灯片标题、副标题、要点列表框与汇总表格。
3. **原生二进制编译（`build_*`）**：
   - 调用 `pdf_to_office(action="build_docx"|"build_xlsx"|"build_pptx", spec=..., output_path="...")` 编译生成原生 Office 二进制文件。

---

## 二、 中文版面解析与文本抽取规范

针对非扫描件的可编辑 PDF 执行纯文本或表格抽取时，严格遵循以下处理规则：

### 1. 中文流式文本重组（消除机械断行）
PDF 底层存储往往将每行文字截断并记录绝对坐标。提取中文文本时，按以下规则重组段落：
- 若上一行末尾为汉字且不包含句号（`。`）、问号（`？`）、感叹号（`！`）或冒号（`：`），下一行开头同样为汉字，**必须剥离行尾换行符，将两行合并为一个连续自然段落**；
- 若上一行末尾为连字符（`-`），且跨越英文字词，剥离连字符并拼接单词。

### 2. 双栏与多栏版面识别
- 对页面内文字块（BBoxes）进行 X 坐标投影分析；
- 若存在明显的中间纵向空白间隙，将页面在逻辑上划分为左栏与右栏；
- **阅读顺序重排**：严格按照“左栏自上而下 $\to$ 右栏自上而下”顺序读取，严禁横向贯通读取导致语义错乱。

### 3. 表格抽取规范
- 使用 `pdfplumber` 的表格抽取能力，优先依赖显式边框线识别单元格；
- 对无边框的三线表，依据文字列坐标投影辅助判定列边界；
- 输出保存为结构化 JSON 或 CSV 文件。

---

## 三、 常用命令行操作与代码模式

所有辅助脚本均位于技能配套目录中，通过 `terminal` 工具执行调用：

### 1. 结构化读取与信息提取
```bash
# 提取逐页文本内容（JSON 输出）
python scripts/pdf_read.py document.pdf --text

# 提取表格并输出为 CSV 与结构化 JSON
python scripts/pdf_read.py document.pdf --tables --csv-dir ./extracted_tables/

# 提取文档元数据、页数、加密状态与页面几何尺寸
python scripts/pdf_read.py document.pdf --meta

# 提取可填写表单字段名与当前取值
python scripts/pdf_read.py form.pdf --fields
```

### 2. 页面与文档编辑操作
```bash
# 合并多个 PDF 文件并保留书签大纲
python scripts/pdf_merge.py part1.pdf part2.pdf -o merged.pdf --bookmarks

# 拆分与提取指定页面（支持旋转）
python scripts/pdf_split.py source.pdf --pages 1-3,5 -o extracted.pdf --rotate 90

# 填写交互式表单（并可选执行平坦化，禁止后续篡改）
python scripts/pdf_fill_form.py form.pdf --fields-json values.json -o filled.pdf --flatten

# 添加文本水印图章
python scripts/pdf_stamp.py doc.pdf -o stamped.pdf --text "内部资料 严禁外传" \
  --x 200 --y 400 --font-size 45 --rotation 45 --opacity 0.25 --color "#888888"

# 导出指定页面为高清 PNG 图像（供视觉核验）
python scripts/pdf_page_image.py doc.pdf --pages 1-5 --dpi 150 --out-dir ./page_images/
```

---

## 四、 交付与自检核对清单

- [ ] 涉及 Office 格式转换的任务，是否严格调用了 `pdf_to_office` 多模态流水线，未采用纯文本直接生成？
- [ ] 提取的中文文本段落是否存在行末机械断行问题？
- [ ] 双栏论文或报刊类文档是否严格保持了先左后右的阅读顺序？
- [ ] 导出的表格数据是否完整保留了表头与数字对应排布？
