# Excel 进阶参考

主技能文档讲的是「创建规范报表 + 读取」的常用路径。本文件补上其余能力与已知陷阱。

## 一、 创建规格的完整字段

JSON 规格的完整说明见 `xlsx_create.py --help` 与其文档字符串。每张工作表支持：

| 字段 | 作用 |
| :--- | :--- |
| `rows` | 行数据，可为标量或带样式的单元格对象 |
| `cells` | 稀疏覆盖，只写指定单元格 |
| `column_widths`、`row_heights` | 列宽、行高 |
| `merges` | 合并单元格 |
| `freeze_panes` | 冻结窗格 |
| `autofilter` | 自动筛选 |
| `conditional_formats` | 条件格式（单元格比较规则与色阶） |
| `charts` | 图表，`bar`、`line`、`pie`，数据源为单元格区域 |
| `validations` | 数据验证，主要是列表下拉 |
| `tables` | 原生 Excel 表格，可指定样式名 |
| `protection` | 工作表保护 |

工作簿级还有 `defined_names`（名称到区域的映射）。单元格对象可另加 `hyperlink` 与 `note`。

### 取值类型

| 类型 | 写法 |
| :--- | :--- |
| 数字、布尔 | JSON 原生类型，原样写入 |
| 日期 | `{"value": "2026-01-31", "type": "date"}` |
| 数字格式 | Excel 格式字符串：金额 `"$#,##0.00"`、百分比 `"0.0%"`、日期 `"yyyy-mm-dd"` |

## 二、 公式与重算

公式有两种写法：

```text
规格里      "formula": "SUM(B2:B9)"
编辑器里    --set "C1==SUM(A:A)"
```

写公式时要加 `"full_calc_on_load": true`（规格）或 `--recalc`（编辑器）。它会设置工作簿的 `fullCalcOnLoad` 标志，让 Excel 或 LibreOffice 打开时重算全部公式。

**openpyxl 本身从不计算公式。**

## 三、 读取

| 参数 | 输出 |
| :--- | :--- |
| `--sheets` | 工作表清单：名称、尺寸、合并区域、图表数量、表格、保护状态、定义名称 |
| `--json`、`--csv` | 数据 |
| `--formulas` | 每条公式与其缓存结果配对 |
| `--notes` | 单元格批注 |
| `--names` | 定义名称 |

缓存结果只在文件被真实表格软件保存过之后才存在；openpyxl 刚写出的文件这里为 `null`。

要让结果真正算出来，用 `xlsx_recalc.py 文件.xlsx` 调 LibreOffice 无界面重算（`soffice` 缺失时打印 `{"recalculated": false, ...}` 并正常退出），之后用 `--data-only` 读取。

## 四、 编辑与结构调整

`xlsx_edit.py` 的执行顺序是：先改名与复制，再做行列结构变更，最后执行 `--set` 与 `--append`。不加 `--out` 时原地修改，要保留原文件请先复制。

**工作表里含公式、合并、表格或筛选时，增删行列改用 `xlsx_restructure.py`**，不要用 `xlsx_edit.py`。

它会重写所有工作表上的公式引用（绝对引用、区域、跨表引用）、平移合并区、自动筛选、冻结窗格、数据验证与条件格式区域、表格引用、定义名称、行列尺寸，最后打印一份 JSON 报告，其中 `not_shifted` 列出没有平移的项。规则与限制见 `references/restructuring.md`。

## 五、 CSV 互转

| 脚本 | 行为 |
| :--- | :--- |
| `csv_to_xlsx.py` | 逐单元格推断整数、浮点、布尔、ISO 日期，并给表头加样式 |
| `xlsx_to_csv.py` | 日期写成 ISO 格式，空单元格写成空字符串 |

两者默认 UTF-8，可用 `--encoding` 指定其他编码（`utf-8-sig` 便于 Excel 识别，`cp1252` 用于旧的 Windows 导出）。

## 六、 已知陷阱

- **openpyxl 不算公式**：公式结果只有文件被 Excel 或 LibreOffice 保存过之后才读得到，否则是 `None`。
- **`xlsx_edit.py` 增删行列不会平移引用**：这是 openpyxl 的原生行为。要用 `xlsx_restructure.py`。即便用它，也移不动图表锚点、图片与条件格式**规则里的公式**——看它 JSON 报告里的 `not_shifted`，以及 `references/restructuring.md`。
- **工作表保护不是安全措施**：`--protect` 只是 xlsx 标准保护哈希，向守规矩的软件表示「别改这里」，仅此而已。任何人改 zip 里的 XML 或在 LibreOffice 里取消勾选都能去掉。**不要用它保护机密或完整性，它不加密任何内容。**
- **以 `data_only=True` 打开再保存会丢掉全部公式**：缓存值会替换掉公式。除确有需要，不要这样保存。
- **打开再保存会丢图表与图片**：openpyxl 无法往返图表，修改含图表的工作簿并保存后图表消失。改完要重新加图表，或者干脆不要保存含图表的文件。
- **CSV 的本地化陷阱**：显式指定编码（脚本已内置）。欧洲区 CSV 常用分号分隔、小数用逗号——用 `--delimiter ';'`，并预期 `"12,5"` 这类内容保持字符串。
- **日期是 datetime 对象**：Excel 内部按序列号存日期，openpyxl 返回 `datetime` 或 `date`，本技能的导出统一写成 ISO 字符串。
- **工作表名限制**：最长 31 个字符，不能包含 `[ ] : * ? / \`。

## 七、 交付前核对

| 阶段 | 核对方法 |
| :--- | :--- |
| 创建后 | `xlsx_read.py 输出.xlsx --sheets`，确认工作表名、尺寸、合并区域、图表数量 |
| 数据 | `--json` 导出后与来源数据比对 |
| 编辑后 | 重新导出改动区域；写了公式就确认 `--formulas` 能列出，且已加 `--recalc` |
| 结构调整后 | 读 `xlsx_restructure.py` 的 JSON 报告，再跑一次 `--formulas` 与 `--sheets` 确认引用与区域落在预期位置 |
| 整体外观 | `soffice --headless --convert-to pdf 输出.xlsx`，看 PDF |
