---
name: chinese-word-format
description: "中文 Word 文档排版规范：执行国标字号换算、段落首行缩进、中文三线表与公文红头排版。"
version: 1.1.0
author: Hermes Agent (吸收并重构自 Hub word-cn-format 与 GB/T 9704)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [中文排版, 国标格式, Word排版, 红头文件, 字号转换, GBT9704]
    category: productivity
    related_skills: [docx, chinese-official-writing]
---

# 中文 Word 文档排版规范技能（Chinese Word Format）

## 概述

吸收《党政机关公文格式》（GB/T 9704-2012）国家标准与现代中文技术文档排版通则，规范化指导 Word (`.docx`) 文档的页面设置、字号磅值转换、字体层级对应、中文首行缩进、专业三线表以及公文红头排版。

**核心目标**：彻底解决 AI 生成中文文档时常见的“英文字号混乱、段首不缩进、表格无边框、正文每行机械敲回车”等格式缺陷，输出完全符合国内机关、事业单位及专业企业标准的高质感文档。

---

## 一、 中文字号与磅值（Points）精确换算标准表

在底层 Python (`python-docx`) 中，字体尺寸必须以磅值（`Pt`）为单位传入。严禁凭空猜测字号大小，必须严格对照下表进行配置：

| 中文字号名称 | 对应磅值（Pt） | 常用排版位置 | 典型应用场景 |
| :--- | :--- | :--- | :--- |
| **初号** | `42.0 Pt` | 封面超大主标题 | 特大红头、荣誉证书大标题 |
| **小初** | `36.0 Pt` | 公文发文机关标志 | 红头文件发文单位大字 |
| **一号** | `26.0 Pt` | 文档大标题 | 方案、规格书、合同一级封面标题 |
| **小一** | `24.0 Pt` | 报告正标题 | 正式报告、决议案正标题 |
| **二号** | `22.0 Pt` | 公文正文主标题 | GB/T 9704 公文正题（小标宋体） |
| **小二** | `18.0 Pt` | 一级大章节标题 | 项目书大章节、合同章节标题 |
| **三号** | `16.0 Pt` | 公文一级标题 / 发文字号 | 公文一级标题（黑体）、三号仿宋正文 |
| **小三** | `15.0 Pt` | 二级标题 | 技术方案二级小节、合同子条款标题 |
| **四号** | `14.0 Pt` | 三级标题 | 规范文件三级分支、重点说明引导词 |
| **小四** | `12.0 Pt` | **常规企业正文 / 报告正文** | 互联网/科技企业方案、学术论文正文 |
| **五号** | `10.5 Pt` | **表格正文 / 紧凑排版** | 数据表内部文字、代码注释、页眉页脚 |
| **小五** | `9.0 Pt` | 附注说明 / 图表来源 | 表格底部数据来源标注、脚注尾注 |

---

## 二、 中文排版核心通用规范

### 1. 字体搭配层级体系
- **公文标准体系（红头/行政公文）**：
  - 大标题：**方正小标宋简体**（或标宋、微软雅黑）
  - 一级标题：**黑体**（不加粗）
  - 二级标题：**楷体**（如楷体_GB2312）
  - 三级与正文：**仿宋**（如仿宋_GB2312）
- **商业与科技报告体系（方案/技术白皮书）**：
  - 标题体系：**微软雅黑**（加粗）或思源黑体
  - 正文体系：**微软雅黑**（10.5 磅 / 12 磅）或中易宋体
  - 代码与英文：**Consolas** 或 **JetBrains Mono**

### 2. 页面与段落排版黄金参数
- **版心与页边距**：
  - 标准企业报告：上 `2.54 cm`、下 `2.54 cm`、左 `3.18 cm`、右 `3.18 cm`（标准页边距）；
  - 国标公文标准：上 `3.7 cm`、下 `3.5 cm`、左 `2.8 cm`、右 `2.6 cm`。
- **行距设置**：
  - 公文标准：固定行距 `28 磅`（每页排 22 行，每行排 28 个汉字）；
  - 现代技术方案：`1.25 倍` 至 `1.35 倍` 多倍行距。
- **中文首行缩进**：
  - 正文自然段落必须强制缩进 2 汉字字符，严禁使用空格强行缩进：
    - 小四号字（12 Pt）缩进：`first_line_indent = Pt(24)`；
    - 五号字（10.5 Pt）缩进：`first_line_indent = Pt(21)`；
    - 三号字（16 Pt）缩进：`first_line_indent = Pt(32)`。

### 3. 数据表排版（标准三线表）
- 表格整体水平居中；
- 顶线与底线加粗（一般为 `1.5 磅` 粗细），表头下方栏目线为细线（`0.75 磅`）；
- 竖直边框全部隐藏；
- 表头文字水平居中并加粗，数字金额靠右排列，常规文本靠左排列。

---

### 4. 底层防乱码、标记清洗与独占锁容错措施
- **彻底解决汉字“豆腐块（□）”乱码**：在底层 Office OpenXML 规范中，西文字体（`w:ascii`）与东亚中文字体（`w:eastAsia`）是分离的。仅设置 `run.font.name = '微软雅黑'` 会导致中文软件强制回退西文字体解析汉字从而引发满屏乱码方块。**必须显式向 XML 注入 `w:eastAsia` 映射**。
- **行内标记物理转换**：生成的文档中严禁残留未解析的 Markdown 反引号（`` ` ``）或原始 LaTeX 代码（如 `$\ge 512\text{GB}$`），必须将其剥离并转化为等宽字体 Consolas 底色高亮，或转义为标准 unicode 符号（如 `≥ 512 GB`）。
- **Windows 文件独占锁定与安全写盘避坑**：在通过 Python 保存 Word 文档时，若目标文件正被用户的办公软件打开，系统会直接抛出权限拒绝异常。**严禁强行杀死用户正在使用的进程**，必须在写盘时捕获权限异常，并在被独占时自动保存为带版本后缀的新文件，向用户交付新文件并说明原因，待用户关闭原文件后再行覆盖同步。

---

## 三、 典型排版自动化实现（python-docx 模板）

```python
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import re

def set_run_font(run, font_name="微软雅黑", font_size=10.5, is_code=False):
    '''彻底解决豆腐块：显式绑定东亚字体 w:eastAsia'''
    run.font.size = Pt(font_size)
    r_pr = run._r.get_or_add_rPr()
    r_fonts = r_pr.find(qn('w:rFonts'))
    if r_fonts is None:
        r_fonts = OxmlElement('w:rFonts')
        r_pr.append(r_fonts)
        
    if is_code:
        r_fonts.set(qn('w:ascii'), 'Consolas')
        r_fonts.set(qn('w:hAnsi'), 'Consolas')
        r_fonts.set(qn('w:eastAsia'), '微软雅黑')
        run.font.name = 'Consolas'
    else:
        r_fonts.set(qn('w:ascii'), 'Microsoft YaHei')
        r_fonts.set(qn('w:hAnsi'), 'Microsoft YaHei')
        r_fonts.set(qn('w:eastAsia'), font_name)
        run.font.name = 'Microsoft YaHei'

def add_official_heading(doc, text, level=1):
    p = doc.add_paragraph()
    run = p.add_run(text)
    
    if level == 1:
        # 一级标题：三号黑体
        run.font.name = '黑体'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        run.font.size = Pt(16)
        p.paragraph_format.first_line_indent = Pt(32)  # 缩进 2 字符
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
    elif level == 2:
        # 二级标题：三号楷体
        run.font.name = '楷体'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '楷体')
        run.font.size = Pt(16)
        p.paragraph_format.first_line_indent = Pt(32)
    return p
```

---

## 四、 交付核验自检清单

- [ ] 字号是否严格映射到正确的磅值（如五号对应 10.5 Pt，小四对应 12 Pt）？
- [ ] 中文正文是否全部采用 2 字符的系统首行缩进，未用手工空格冒充？
- [ ] 中文与西文混合时，是否显式绑定了中文字体族（`eastAsia` 映射）？
- [ ] 表格是否水平居中，且采用了规范的顶底加粗三线表设计？
