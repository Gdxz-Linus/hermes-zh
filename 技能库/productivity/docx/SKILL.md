---
name: docx
description: "Word (.docx) 原生文档处理：规范化创建、结构化读取、段落样式重塑、表格编辑与模板填充。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [word, docx, 办公文档, 报告生成, 文档排版, 样式规范]
    category: productivity
    related_skills: [xlsx, pdf, document-to-action-items]
---

# Word (.docx) 原生文档处理技能

## 概述

使用 Python 与 `python-docx` 原生引擎对 Microsoft Word (`.docx`) 格式文档进行全生命周期管理：从规范化创建多级样式报告、提取正文大纲结构，到精确替换段落文字、修改表格单元格以及基于模板变量执行数据填充。

**质量底线**：严禁生成将文字用硬换行强行分段、或者缺乏层级样式的散乱文档。输出的 Word 文档必须具备原生完全可编辑性与标准样式树。

## 适用场景

- 创建符合正式技术规范、项目报告或商业合同要求的专业 Word 文档；
- 提取既有 `.docx` 文件的纯文本、大纲层级结构、表格数据或内嵌图片；
- 针对现有文档执行段落文字替换、批量更新或表格特定单元格数据修改；
- 使用模板并填充 `{{变量名}}` 形式的变量生成定制文档；
- 审阅、接受或驳回文档中的修订痕迹（Track Changes）与批注内容；
- 补齐正式文档的动态目录（TOC）字段与“第 X 页 / 共 Y 页”页码页脚。

*不适用场景：早期二进制 `.doc` 格式（需先调用 LibreOffice 执行无损转换）或纯视觉像素排版。*

---

## 中文 Word 文档质量规范

生成或修改 Word 文档时，必须强制遵循以下格式要求：

### 1. 标题与段落样式规范
- **标题层级必须使用原生样式**：主标题、一级标题至三级标题必须应用标准的 `Heading 1`、`Heading 2`、`Heading 3` 样式，确保导航窗格与自动大纲能正确识别，严禁通过手动放大正文字号来假冒标题；
- **流式段落与自然断行**：段落之间依靠段前段后间距（Space Before/After）区分，**严禁在每行末尾机械插入软换行或硬回车**；
- **首行缩进规范**：中文正文段落推荐配置 2 字符首行缩进（`first_line_indent = Pt(21)` 或基于字体尺寸的换算值）。

### 2. 表格设计与单元格排版
- **居中与自适应**：表格整体在页面水平居中，列宽应根据内容长短显式分配，严禁出现内容溢出页面边界；
- **表头高亮**：表头首行必须设置轻微底色填充（如浅灰 `#F2F4F7`）并加粗字体；
- **三线表规范**：技术报告或正式公文中的数据表，优先采用三线表格式（顶线、底线粗，栏目线细，竖直边框默认隐去）。

---

## 常用操作与代码模式

### 1. 创建规范文档的标准代码模式
```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()

# 1. 设置正文默认字体属性
normal_style = doc.styles['Normal']
normal_style.font.name = 'Microsoft YaHei'  # 微软雅黑
normal_style.font.size = Pt(10.5)           # 五号字，约 10.5 磅
normal_style.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

# 2. 插入居中文档大标题
title_p = doc.add_paragraph()
title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
title_run = title_p.add_run("项目系统架构设计说明书")
title_run.font.size = Pt(22)  # 二号字
title_run.bold = True
title_p.paragraph_format.space_before = Pt(12)
title_p.paragraph_format.space_after = Pt(18)

# 3. 插入原生层级标题
h1 = doc.add_heading(level=1)
h1_run = h1.add_run("一、 系统总体概述")
h1_run.font.name = 'Microsoft YaHei'
h1.paragraph_format.space_before = Pt(12)
h1.paragraph_format.space_after = Pt(6)

# 4. 插入具有首行缩进的正文段落
body_p = doc.add_paragraph()
body_p.paragraph_format.first_line_indent = Pt(21)  # 2 字符缩进
body_p.paragraph_format.line_spacing = 1.35         # 1.35 倍行距
body_p.add_run("本系统基于高并发微服务架构构建，各模块之间采用轻量化异步消息队列进行通信分离...")

# 5. 插入标准三线数据表
table = doc.add_table(rows=1, cols=3)
table.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr_cells = table.rows[0].cells
hdr_cells[0].text = "模块编号"
hdr_cells[1].text = "服务名称"
hdr_cells[2].text = "核心功能职责"
for cell in hdr_cells:
    cell.paragraphs[0].runs[0].bold = True

row_cells = table.add_row().cells
row_cells[0].text = "MOD-01"
row_cells[1].text = "认证鉴权中心"
row_cells[2].text = "负责分布式令牌签发与会话生命周期管理"

doc.save("架构说明书.docx")
```

---

### 2. 提取既有文档大纲与文本
```python
from docx import Document

doc = Document("现有文件.docx")

# 提取大纲结构
for p in doc.paragraphs:
    if p.style.name.startswith('Heading'):
        print(f"[{p.style.name}] {p.text}")

# 遍历读取表格内容
for t_idx, table in enumerate(doc.tables):
    print(f"\n--- 表格 {t_idx + 1} ---")
    for row in table.rows:
        row_text = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
        print(" | ".join(row_text))
```

---

### 3. 精准查找替换（保持格式完好）
```python
def replace_text_in_paragraph(paragraph, old_text, new_text):
    if old_text in paragraph.text:
        # 当文字跨越多个不同格式分段（runs）时，直接合并重写
        full_text = paragraph.text.replace(old_text, new_text)
        # 清除旧分段并保留第一个分段的基准格式
        if paragraph.runs:
            first_run = paragraph.runs[0]
            for run in paragraph.runs[1:]:
                run.text = ""
            first_run.text = full_text
        else:
            paragraph.text = full_text

# 遍历段落与表格执行替换
for p in doc.paragraphs:
    replace_text_in_paragraph(p, "旧公司名称", "新公司名称")

for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                replace_text_in_paragraph(p, "旧公司名称", "新公司名称")
```

---

## 交付与自检核对清单

- [ ] 文档标题是否使用了标准的 `Heading 1-9` 原生样式？
- [ ] 中文正文是否存在每行强行敲回车造成的断裂问题？
- [ ] 表格整体是否在页面中居中，且表头行文字加粗居中？
- [ ] 保存后的 `.docx` 文件能否在 Microsoft Office 与 WPS 中无报错正常打开？
