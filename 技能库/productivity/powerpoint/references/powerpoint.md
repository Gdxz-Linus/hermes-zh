# PowerPoint（.pptx）

## 概述

用 python-pptx 库创建、查看与编辑 PowerPoint 演示文稿。五个脚本覆盖：按 JSON 规格新建、结构化回读、原地修改、按品牌模板生成、幻灯片渲染成图。全部离线运行，不需要安装 PowerPoint。

脚本都在 `scripts/` 下，用 `terminal` 调用，都支持 `--help`，成功时向标准输出打印 JSON，失败时退出码非零。

不属于本技能的场景：`.ppt` 旧版二进制文件。装了 LibreOffice 时先转格式：

```bash
soffice --convert-to pptx old.ppt
```

## 适用场景

- 用户要求做演示文稿、汇报材料或路演文稿
- 需要从别人给的 .pptx 里提取文字、备注、表格、图表数据或图片
- 需要修改已有文稿：替换文字、刷新或局部修改图表数据、换 logo、复制或删除或调整页序、设置背景、页脚、超链接、演讲者备注
- 需要按公司 .pptx 模板做出符合品牌规范的文稿

## 怎么运行

```bash
"$PY" scripts/pptx_create.py deck.json out.pptx
"$PY" scripts/pptx_read.py deck.pptx --outline      # 完整 JSON 大纲
"$PY" scripts/pptx_read.py deck.pptx --notes        # 演讲者备注
"$PY" scripts/pptx_read.py deck.pptx --images ./img # 导出图片
"$PY" scripts/pptx_edit.py deck.pptx --replace-text "旧公司名" "新公司名"
"$PY" scripts/pptx_edit.py deck.pptx --chart-data update.json
"$PY" scripts/pptx_edit.py deck.pptx --duplicate-slide 2
"$PY" scripts/pptx_edit.py deck.pptx --remove-slide 3 --move-slide 2 0
"$PY" scripts/pptx_from_template.py brand.pptx out.pptx --values vals.json
"$PY" scripts/pptx_render.py deck.pptx --outdir ./render  # 每页一张 PNG
```

JSON 规格用 `write_file` 写，脚本输出与生成的 JSON 用 `read_file` 看。

## 常用命令对照

| 任务 | 命令 |
| :--- | :--- |
| 按规格新建 | `pptx_create.py spec.json out.pptx` |
| 16:9 或 4:3 | 规格里写 `"slide_size": "16:9"` 或 `"4:3"` |
| 导出大纲 JSON | `pptx_read.py deck.pptx --outline` |
| 导出图片 | `pptx_read.py deck.pptx --images DIR` |
| 替换文字 | `pptx_edit.py deck.pptx --replace-text 旧 新` |
| 替换图表数据 | `pptx_edit.py deck.pptx --chart-data spec.json` |
| 只改某个数据系列 | 同一个参数，规格里用 `"ops"`（见下） |
| 换图片 | `pptx_edit.py deck.pptx --swap-image N NAME new.png` |
| 复制页 | `pptx_edit.py deck.pptx --duplicate-slide N` |
| 删除页 | `pptx_edit.py deck.pptx --remove-slide N` |
| 调整页序 | `pptx_edit.py deck.pptx --move-slide 原位置 目标位置` |
| 设置背景 | `pptx_edit.py deck.pptx --set-background N RRGGBB` |
| 加超链接 | `pptx_edit.py deck.pptx --hyperlink N 文字 URL` |
| 打开页码 | `pptx_edit.py deck.pptx --enable-slide-number N` |
| 设置页脚 | `pptx_edit.py deck.pptx --set-footer N 文字` |
| 写备注 | `pptx_edit.py deck.pptx --set-notes N 文字` |
| 追加备注 | `pptx_edit.py deck.pptx --append-notes N 文字` |
| 按模板填充 | `pptx_from_template.py tpl.pptx out.pptx --values v.json` |
| 渲染成 PNG | `pptx_render.py deck.pptx --outdir DIR` |

## 操作步骤

### 1. 新建文稿

先写 JSON 规格（完整格式见 `pptx_create.py --help`），再运行 `pptx_create.py`。

每页可设置：

| 字段 | 取值 |
| :--- | :--- |
| `layout` | `title`、`title_content`、`section`、`two_content`、`title_only`、`blank` |
| `title`、`subtitle` | 文字 |
| `bullets` | 字符串列表，或字典：`level`（0 到 4）、`size`（磅）、`bold`、`italic`、`font`、`color`（十六进制）、`link`（超链接地址） |
| `background` | 纯色十六进制 |
| `footer` | 文字，启用版式的页脚占位符 |
| `slide_number` | `true`，启用版式的页码占位符 |
| `images` | 路径 + `left`、`top`、`width`、`height`（英寸） |
| `tables` | `rows` 为二维列表 |
| `shapes` | `rectangle`、`rounded_rectangle`、`oval`、`diamond`、`right_arrow`、`chevron`，配 `fill` 十六进制与可选 `text` |
| `charts` | `bar`、`bar_h`、`line`、`pie`，配 `categories` 与 `series` |
| `notes` | 演讲者备注 |

### 2. 读取文稿

```bash
"$PY" scripts/pptx_read.py deck.pptx --outline
```

返回页面尺寸、版式清单，以及每页的：版式名、全部形状文字、表格单元格、图片清单（文件名/扩展名/字节数）、图表的类别与系列与数值、演讲者备注。

用 `--images DIR` 把内嵌图片导出成文件，需要看内容时再用 `vision_analyze`。

### 3. 修改文稿

`pptx_edit.py` 一次可组合多个操作；加 `--output` 可保留原文件。

| 操作 | 说明 |
| :--- | :--- |
| 替换文字 | 扫描形状、表格单元格与备注 |
| 换图片 | 重指向图片的关系编号，位置与尺寸保持不变 |
| 删除页 | 删掉关系与 `<p:sldId>` 条目 |
| 调整页序 | 在 `<p:sldIdLst>` 内移动 `<p:sldId>` 元素 |
| 复制页 | 追加第 N 页的独立深拷贝：形状 XML 与图片、媒体、超链接关系一并复制并重新映射编号，改副本不会影响原页 |

python-pptx 对删页与调序没有公开接口，脚本直接做 XML 层操作。**含图表的页不能复制**（见「注意事项」）。

设置备注用 `--set-notes` 或 `--append-notes`；`--set-background`、`--hyperlink`、`--enable-slide-number`、`--set-footer` 处理版面细节。

#### 图表数据更新

用 `--chart-data` 传 JSON 规格。整体替换：

```json
{"slide": 0, "chart": 0, "categories": ["一季度", "二季度"], "series": {"销量": [12, 34]}}
```

局部修改改用 `"ops"`，取值为操作列表：

| 操作 | 字段 |
| :--- | :--- |
| `update_series` | `name`、`values` |
| `add_series` | 同上 |
| `remove_series` | `name` |
| `rename_category` | `from`/`to` 或 `index` |
| `set_title` | 文字 |

python-pptx 只能整体替换图表数据集，所以局部操作是「读出原数据 → 修改 → 整体替换」的包装。无法用「类别 + 数值系列」表达的图表数据，会在这一轮读写中被归一化。

### 4. 按模板生成

`pptx_from_template.py` 打开品牌模板，替换各页、表格、备注里的所有 `{{占位标记}}`，还能追加使用模板自有版式的新页（按版式名或序号），从而继承母版的字体与配色。

起步时若模板自带示例页，生成完用 `pptx_edit.py --remove-slide` 删掉。

### 5. 视觉核验

```bash
"$PY" scripts/pptx_render.py deck.pptx --outdir ./render
```

脚本用 `soffice --headless` 把文稿转成 PDF，再用 `pdftoppm`（或 `pdftocairo`）拆成一页一张 PNG，输出 JSON 列出图片路径，逐张用 `vision_analyze` 检查。

两个工具任一缺失时，脚本退出码为 0，输出 `{"rendered": false, "missing": [...]}` 与处理建议；此时退回 `pptx_read.py` 的 JSON 大纲——它能验证内容与结构，只是看不到版面。

## 注意事项

- **文字被拆成片段**：PowerPoint 会在拼写检查与编辑边界处把段落文字切成多个片段。`--replace-text` 会先把格式相同的相邻片段合并，因此跨片段的匹配也能替换且格式完整保留。只有当匹配跨越**格式确实不同**的片段时，才会用首个片段的格式重写整段——这类页替换后请核对。
- **含图表的页不能复制**：每个图表关系内嵌一个独立的 XLSX 工作簿部件，可靠地复制这套结构不受支持，所以 `--duplicate-slide` 遇到含图表的页会直接拒绝，而不是把文稿弄坏。要在新页上重建图表。外部超链接与图片、媒体关系会一并带过；版式与备注关系重新创建。
- **图表操作是包装**：python-pptx 只能整体替换数据集，`"ops"` 是把现有数据读出再整体写回；**图表类型无法更改**。
- **调序是 XML 层操作**：python-pptx 没有受支持的调序接口，`--move-slide` 直接改 `<p:sldIdLst>`。普通文稿安全，改完请重新读取确认。
- **跨文稿复制页不受支持**：复制只能在同一文稿内进行，因为版式与母版是共享的。
- **页脚与页码**：启用时从该页版式复制占位符；版式若没有对应占位符，`--set-footer` 会明确报错，此时改加文本框。
- **超链接作用于整个片段**：`--hyperlink` 会给该页包含指定文字的所有片段加上链接。
- **默认尺寸**：python-pptx 自带模板是 4:3；新建脚本默认设为 16:9，除非规格另有指定。自定义模板保持自身尺寸。
- **版式序号因模板而异**：用品牌模板时先列出可用版式：`pptx_read.py template.pptx --outline`，看 `layouts_available`。
- **空白版式没有标题占位符**：`slide.shapes.title` 在空白版式上为 None。新建脚本已处理，自己写 python-pptx 代码时要记得。
- **写规格文件必须指定 `encoding="utf-8"`**：`{{city}}` 这类占位标记可能填入非 ASCII 内容。

## 交付前核对

1. 任何新建或修改之后，运行 `pptx_read.py 输出.pptx --outline`，核对页数、文字、表格、备注、图表数值是否符合预期。
2. 用 `--images DIR` 导出后查文件大小，确认图片确实嵌入。
3. 用 `pptx_render.py deck.pptx --outdir ./render` 渲染每页，逐张用 `vision_analyze` 查看——这一步能发现大纲看不出的形状重叠、文字截断与配色问题。渲染工具缺失时脚本会说明，退回大纲核验。
4. 完整契约以测试集为准：`python -m pytest tests/ -q`（需要 python-pptx 与 pytest）。
