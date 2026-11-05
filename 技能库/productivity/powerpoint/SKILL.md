---
name: powerpoint
description: "PowerPoint (.pptx) 演示文稿处理：16:9 现代宽屏排版、原生可编辑组件、图表数据更新与规范化制作。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pptx, powerpoint, 幻灯片, 演示文稿, 汇报制作, python-pptx]
    category: productivity
    related_skills: [docx, xlsx, pdf]
---

# PowerPoint (.pptx) 演示文稿处理技能

## 概述

使用 Python 与 `python-pptx` 引擎实现 PowerPoint (`.pptx`) 格式幻灯片的自动化制作、结构化提取与就地修改。无需宿主机安装微软 Office 套件即可完全离线执行，生成符合商务与技术汇报标准的演示文稿。

**核心质量红线**：
1. **强制 16:9 现代宽屏版式**：严禁采用过时的 4:3 方屏画幅（默认尺寸统一为 16:9 宽屏，即宽 13.333 英寸、高 7.5 英寸）；
2. **原生完全可编辑组件**：所有文字标题、文本框、形状、表格与图表必须为 Office 原生矢量元素，**严禁将整页作为背景图片平铺冒充幻灯片**；
3. **中文版面留白与可读性**：单张幻灯片正文要点严格控制在 3 至 6 行以内，杜绝整段冗长密集的文字堆砌。

## 适用场景

- 创建符合企业与工程标准的技术方案汇报、季度总结、立项评审或架构演进演示文稿；
- 从既有 `.pptx` 文档中提取大纲文本、演讲者备注（Speaker Notes）、数据表或内嵌图像；
- 编辑现有文稿：原地查找替换文字、更新图表数据、调整版式、复制或重排幻灯片顺序；
- 基于已有企业模板（`.pptx`）进行变量填充生成定制演示文稿。

*不适用场景：早期二进制 `.ppt` 格式（需先调用 LibreOffice 转换为 `.pptx`）。*

---

## 一、 技术与商务汇报标准框架

生成成套幻灯片时，必须遵循以下结构规范：

1. **封面页（Title Slide）**：包含主标题（28~36 磅加粗）、副标题（16~20 磅）、汇报人部门与日期；
2. **背景与核心挑战页（Context & Challenges）**：采用双栏或三列对比排版，清晰陈述业务背景与面临的客观挑战；
3. **架构与方案页（Architecture & Solution）**：利用原生表格、内容线框或层级图展示技术架构与核心方案；
4. **推进实施路线页（Roadmap & Execution）**：按时间轴或阶段里程碑拆解关键实施步骤；
5. **指标与成效页（Metrics & Business Impact）**：利用原生数据图表或大字号指标（24~32 磅粗体数字）突出关键成果；
6. **结语与问答页（Q&A）**：规范的总结致谢。

---

## 二、 原生排版与代码调用规范

### 1. 规范创建 16:9 幻灯片的标准代码模式
```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()

# 1. 强制设定为 16:9 现代宽屏画幅 (13.333 x 7.5 英寸)
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# 2. 选择空白版式添加单页
blank_slide_layout = prs.slide_layouts[6]
slide = prs.slides.add_slide(blank_slide_layout)

# 3. 添加原生标题文本框
title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.7), Inches(1.0))
tf_title = title_box.text_frame
tf_title.word_wrap = True
p_title = tf_title.paragraphs[0]
p_title.text = "系统架构演进与性能提升方案"
p_title.font.name = "Microsoft YaHei"
p_title.font.size = Pt(28)
p_title.font.bold = True
p_title.font.color.rgb = RGBColor(0x1F, 0x4E, 0x78)  # 深蓝商务色

# 4. 添加三列分栏内容区块
card_width = Inches(3.6)
card_height = Inches(4.5)
card_y = Inches(1.8)

columns_data = [
    ("一、 核心挑战诊断", "当前系统面临高并发写入延迟过高瓶颈，单机队列容量已达物理上限。"),
    ("二、 核心改造", "全面引入分布式消息队列中间件，实施异步拆解与批量处理。"),
    ("三、 预期成效", "全流程处理耗时预期降低 65%，系统可用性提升至 99.99%。")
]

for idx, (card_title, card_body) in enumerate(columns_data):
    card_x = Inches(0.8 + idx * 4.0)
    # 添加浅色矩形背景底框
    shape = slide.shapes.add_shape(1, card_x, card_y, card_width, card_height)  # 1 代表矩形
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(0xF2, 0xF4, 0xF8)
    shape.line.color.rgb = RGBColor(0xD9, 0xE1, 0xF2)
    
    # 填充区块内部文字
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_top = Inches(0.3)
    tf.margin_left = Inches(0.3)
    
    p1 = tf.paragraphs[0]
    p1.text = card_title
    p1.font.name = "Microsoft YaHei"
    p1.font.size = Pt(16)
    p1.font.bold = True
    p1.font.color.rgb = RGBColor(0x1F, 0x4E, 0x78)
    p1.space_after = Pt(14)
    
    p2 = tf.add_paragraph()
    p2.text = card_body
    p2.font.name = "Microsoft YaHei"
    p2.font.size = Pt(12)
    p2.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

prs.save("架构演进方案.pptx")
```

---

### 2. 命令行工具使用参考
配套脚本位于技能脚本目录中，可通过 `terminal` 工具直接调用：

```bash
# 基于 JSON 规格说明书生成完整幻灯片
python scripts/pptx_create.py deck_spec.json output.pptx

# 结构化读取现有幻灯片大纲（输出 JSON）
python scripts/pptx_read.py presentation.pptx --outline

# 提取所有幻灯片中的演讲者备注
python scripts/pptx_read.py presentation.pptx --notes

# 提取幻灯片中内嵌的高清图像至目录
python scripts/pptx_read.py presentation.pptx --images ./exported_images/

# 原地文本替换（保持原有字号色彩完好）
python scripts/pptx_edit.py presentation.pptx --replace-text "旧部门名" "新部门名"

# 导出每页幻灯片为高清预览图像
python scripts/pptx_render.py presentation.pptx --outdir ./slide_previews/
```

---

## 三、 自检核对清单

- [ ] 画幅比例是否确认为 16:9 现代宽屏（宽 13.333 英寸，高 7.5 英寸），未回退为 4:3？
- [ ] 所有文本内容是否均写入可编辑文本框，杜绝了整页平铺截图？
- [ ] 中文字体是否统一绑定为微软雅黑等常见无衬线字体？
- [ ] 单页内容是否保持了合理的行间距与外边距留白，未发生文字超出边界截断？
