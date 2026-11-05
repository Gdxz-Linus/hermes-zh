---
name: xlsx
description: "Excel (.xlsx) 工作簿处理：构建强类型数据表、自动列宽、公式图表与结构化编辑。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [excel, 电子表格, xlsx, 数据处理, 报表生成, openpyxl]
    category: productivity
    related_skills: [docx, pdf, document-to-action-items]
---

# Excel (.xlsx) 工作簿原生处理技能

## 概述

使用 Python 与 `openpyxl` 引擎构建、审阅和维护专业的 Microsoft Excel (`.xlsx`) 工作簿。实现包含多工作表、强类型数据单元格、财务数字格式化、动态公式、自动冻结窗格、自适应列宽以及原生 Excel 表格的生成。

**质量底线**：严禁将数字、金额或日期全部作为纯文本字符串（String）塞入表格；输出的 Excel 表格必须使用正确的原生底层数据类型，保证下游用户可直接求和与分析。

## 适用场景

- 创建企业级专业财务报表、工程数据清单、指标汇总与审计台账；
- 批量读取现有 `.xlsx` 文件中的各工作表数据、公式、单元格批注与名称定义；
- 编辑现有工作簿：单元格原地修改、追加数据行、插入/删除行列并自动调整公式引用；
- 处理 CSV 与 XLSX 之间的互相转换，兼顾编码自适应与数据类型自动推导。

*不适用场景：早期二进制 `.xls` 格式（需先调用 LibreOffice 转换为 `.xlsx`）。*

---

## 电子表格设计标准规范

### 1. 严格的数据类型规约（核心原则）
- **数值与金额**：必须写入 Python 的原生 `int` 或 `float` 类型，绝不能在外面套字符串引号（例如写入 `12500.50`，而不是 `"12500.50"`）；
- **日期与时间**：必须使用 Python 的 `datetime.date` 或 `datetime.datetime` 写入，并绑定标准格式（如 `YYYY-MM-DD`）；
- **数字格式绑定（Number Formats）**：
  - 货币金额：绑定 `#,##0.00` 或 `¥#,##0.00`，使界面自动带有千分位与两位小数；
  - 百分比：绑定 `0.0%` 或 `0.00%`，数据值存入小数（如 `0.156` 显示为 `15.6%`）。

### 2. 视觉排版与可读性标准
- **表头风格**：首行表头必须设置轻微底色（如科技蓝 `#1F4E78` 或深灰 `#2F3640` 配白字加粗，或浅灰蓝 `#D9E1F2` 配深色字）；
- **网格线与边框**：数据区域必须施加完整的细灰色外边框与内边框（`Thin Border`），禁止留白一片；
- **自适应列宽**：保存前必须根据每列最长内容字符计算并设置列宽（`column_dimensions[col].width`），避免文字被截断显示为 `###`；
- **冻结首行**：多于 20 行的数据表，必须开启首行冻结（`ws.freeze_panes = 'A2'`），保证滚动时表头常驻。

---

## 常用操作与代码模式

### 1. 创建规范企业级报表的标准代码模式
```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import datetime

wb = Workbook()
ws = wb.active
ws.title = "季度财务收支明细"

# 1. 样式常量定义
HEADER_FONT = Font(name="Microsoft YaHei", size=11, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
BODY_FONT = Font(name="Microsoft YaHei", size=10)
TOTAL_FONT = Font(name="Microsoft YaHei", size=10, bold=True)

THIN_SIDE = Side(border_style="thin", color="D3D3D3")
TABLE_BORDER = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)

# 2. 写入表头数据
headers = ["序号", "交易日期", "支出类目", "责任部门", "单据金额", "税率", "最终报销额"]
ws.append(headers)

for col_num in range(1, len(headers) + 1):
    cell = ws.cell(row=1, column=col_num)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = TABLE_BORDER

# 3. 写入强类型业务数据
data_rows = [
    [1, datetime.date(2026, 10, 1), "云服务器租用", "研发中心", 45000.0, 0.06, "=E2*(1+F2)"],
    [2, datetime.date(2026, 10, 5), "办公网络专线", "运维保障部", 12800.0, 0.09, "=E3*(1+F3)"],
    [3, datetime.date(2026, 10, 12), "安全渗透审查", "信息安全部", 28000.0, 0.06, "=E4*(1+F4)"],
]

for row_idx, row_data in enumerate(data_rows, start=2):
    ws.append(row_data)
    for col_idx in range(1, len(row_data) + 1):
        c = ws.cell(row=row_idx, column=col_idx)
        c.font = BODY_FONT
        c.border = TABLE_BORDER
        
        # 针对特定数据类型绑定数值显示格式与排版
        if col_idx == 1:
            c.alignment = Alignment(horizontal="center")
        elif col_idx == 2:
            c.number_format = 'yyyy-mm-dd'
            c.alignment = Alignment(horizontal="center")
        elif col_idx in (5, 7):
            c.number_format = '¥#,##0.00'
            c.alignment = Alignment(horizontal="right")
        elif col_idx == 6:
            c.number_format = '0.0%'
            c.alignment = Alignment(horizontal="right")

# 4. 追加合计行
total_row_idx = len(data_rows) + 2
ws.cell(row=total_row_idx, column=1, value="合计").font = TOTAL_FONT
ws.cell(row=total_row_idx, column=5, value=f"=SUM(E2:E{total_row_idx-1})").number_format = '¥#,##0.00'
ws.cell(row=total_row_idx, column=7, value=f"=SUM(G2:G{total_row_idx-1})").number_format = '¥#,##0.00'

for col_idx in range(1, len(headers) + 1):
    c = ws.cell(row=total_row_idx, column=col_idx)
    c.border = TABLE_BORDER
    if not c.font.bold:
        c.font = TOTAL_FONT

# 5. 开启首行冻结与自适应列宽
ws.freeze_panes = 'A2'

for col in ws.columns:
    max_len = 0
    col_letter = get_column_letter(col[0].column)
    for cell in col:
        val_str = str(cell.value or '')
        # 中文字符长度计算补偿
        cell_len = sum(2 if ord(char) > 127 else 1 for char in val_str)
        max_len = max(max_len, cell_len)
    ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

wb.save("财务明细表.xlsx")
```

---

### 2. 读取现有工作簿并转换为结构化字典
```python
from openpyxl import load_workbook

wb = load_workbook("财务明细表.xlsx", data_only=True)  # data_only=True 获取计算值而非公式表达式
ws = wb.active

records = []
headers = [cell.value for cell in ws[1]]

for row in ws.iter_rows(min_row=2, values_only=True):
    if not any(row):
        continue
    record = dict(zip(headers, row))
    records.append(record)

print(f"成功提取 {len(records)} 条记录")
```

---

## 交付与自检核对清单

- [ ] 数值、金额列是否保存为浮点数或整数，而非带有引号的字符串？
- [ ] 日期列是否已设定为 `yyyy-mm-dd` 格式？
- [ ] 表头行是否配置了底色填充并加粗文字？
- [ ] 全量单元格是否均施加了边框，未发生无边框断裂？
- [ ] 是否已计算并展开列宽，杜绝界面出现 `###`？
- [ ] 20 行以上数据表是否已开启 `freeze_panes` 首行冻结？
