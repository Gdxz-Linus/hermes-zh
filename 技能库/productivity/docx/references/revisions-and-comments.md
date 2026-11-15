# 修订与批注：XML 层细节

`docx_revisions.py` 与 `docx_comments.py` 的深度参考。需要读懂原始 WordprocessingML、扩展脚本或排查异常文档时读本文件；日常使用只看 SKILL.md 即可。

## 修订记录（w:ins / w:del）

Word 把「修订」记录为段落（`w:p`）内的包装元素，所属命名空间为
`http://schemas.openxmlformats.org/wordprocessingml/2006/main`：

```xml
<w:p>
  <w:r><w:t>Base </w:t></w:r>
  <w:ins w:id="1" w:author="Editor" w:date="2026-01-02T03:04:05Z">
    <w:r><w:t>inserted text</w:t></w:r>
  </w:ins>
  <w:del w:id="2" w:author="Editor" w:date="2026-01-02T03:04:05Z">
    <w:r><w:delText>deleted text</w:delText></w:r>
  </w:del>
</w:p>
```

脚本依赖的几条关键事实：

- 被删除的文字存在 `w:delText` 里，不在 `w:t` 里。所以直接抽取正文得到的是「已接受修订」的视图：插入可见、删除不可见。
- 处理语义：

| 操作 | 实际动作 |
| :--- | :--- |
| 接受 `w:ins` | 拆掉包装，把子元素上提 |
| 拒绝 `w:ins` | 连同内容一起删除 |
| 接受 `w:del` | 连同内容一起删除 |
| 拒绝 `w:del` | 把每个 `w:delText` 改名为 `w:t`，再拆包装 |

- 修订可以出现在任何允许块级内容的位置：正文、表格单元格（含嵌套表格）、页眉、页脚、文本框。脚本遍历正文根节点与每个页眉页脚部件根节点，用 `root.iter(W+"ins", W+"del")` 抓取，因此任意深度都能找到。
- `w:id` 在**元素**层面唯一，但一次逻辑编辑可能产生多个元素。`accept` 与 `reject --id` 只作用于带该 id 的元素本身。

脚本**不处理**以下形态（`docx_read.py --revisions` 能检出，但不改动）：段落标记修订（`w:pPr` 上的 `w:rPr/w:ins`）、表格行的插入与删除（`w:trPr/w:ins`）、格式变更记录（`w:rPrChange`、`w:pPrChange`）、移动（`w:moveFrom`/`w:moveTo`）。

移动在常见编辑器里很少出现；遇到就交给 Word 处理，不要凭猜测改写。

## 批注

由三部分配合构成：

1. **`word/comments.xml`**：每条批注一个 `w:comment` 元素，携带 `w:id`、`w:author`、`w:initials`、`w:date` 与正文段落。document.xml 通过关系类型 `.../comments` 与内容类型 `application/vnd...wordprocessingml.comments+xml` 指向它（还需要在 `[Content_Types].xml` 里加一项覆盖声明，python-docx 的部件机制在注册部件时会自动加上）。
2. **正文里的区域标记**：被批注文字之前是 `w:commentRangeStart w:id="N"`，之后是 `w:commentRangeEnd w:id="N"`。
3. **引用片段**：一个含 `w:commentReference w:id="N"` 的 `w:r`，紧跟在区域结束标记之后，把批注气泡与位置绑定。

`docx_comments.py` 的行为：

- **列出与删除**始终在 XML 层完成，因此任何软件生成的文件都能处理。`anchored_text` 的还原方式是：按文档顺序遍历每个部件根节点，收集每个 id 在起止标记之间的 `w:t` 文字。
- **新增**先把目标文字隔离成完整片段。匹配位置若落在片段中间，就在边界处切分片段（切分时复制 `w:rPr`，格式得以保留）。之后：
  - python-docx 1.2 及以上：使用原生 `document.add_comment(runs, ...)` 接口，它会自行创建批注部件、标记与引用片段。
  - 更早的版本或指定 `--xml`：脚本自行构建 `word/comments.xml`，通过 opc 层注册部件与关系，再手工插入标记与引用。
- 删除批注会移除该 id 的 `w:comment` 元素与三类标记，被批注的正文文字不受影响。

新版 Word 还会写 `commentsExtended.xml`（记录回复关系与已解决状态）。本脚本既不读也不写它：回复内容与「已解决」标记在这里看不到，本技能新增的批注都是普通的一级批注。
