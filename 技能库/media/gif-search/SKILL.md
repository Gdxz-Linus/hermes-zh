---
name: gif-search
description: "用于通过 Tenor API 检索与下载动图（GIF），支持关键词搜索与分类发现。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [TENOR_API_KEY]
  commands: [curl]
metadata:
  hermes:
    tags: [gif, 动图检索, 图片下载, tenor, 媒体素材, 视觉内容]
    category: media
    related_skills: []
---

# 动图检索与本地下载指南（Tenor GIF Search）

## 概述

指导在终端环境中使用 `curl` 工具直接调用 Google Tenor 官方 API 接口，实现动态图片（GIF）的关键词检索、热门分类浏览与图片文件本地下载。无需安装多余的重型依赖包，通过标准轻量 HTTP 请求即可快速获取高质量动图素材，用于文档配图或沟通展示。

## 适用场景

- “搜索一个表示‘庆祝通过’或‘鼓掌’的高质量动图”
- “查找关于某个科技主题的动画演示例图并保存到本地文件夹”
- “浏览当前热门的动态表情并获取其预览直链”

---

## 一、 访问凭据配置与请求基础

调用 Tenor API 需要在环境配置文件中配置专属 API 密钥：

1. **获取与保存 API 密钥**：
   - 从 Google Cloud 控制台申请并启用 Tenor API 密钥；
   - 将密钥写入 `$HERMES_HOME/.env` 配置文件：
     ```bash
     TENOR_API_KEY="你的Tenor密钥"
     ```
2. **基础端点与通用参数**：
   - 基础请求地址：`https://tenor.googleapis.com/v2`；
   - 客户端标识参数：每次请求需携带 `client_key=hermes_agent` 用于身份标记。

---

## 二、 常用 API 检索与下载命令范式

### 1. 关键词搜索动图
根据关键词检索前 5 张动图，并输出直链与分辨率：
```bash
curl -s "https://tenor.googleapis.com/v2/search?q=celebrate&key=$TENOR_API_KEY&client_key=hermes&limit=5"   | python -m json.tool
```

### 2. 精准提取高画质或紧凑型动图 URL
使用 Python 单行命令从 JSON 结果中直接提取最适合展示的媒体链接：
```bash
curl -s "https://tenor.googleapis.com/v2/search?q=success&key=$TENOR_API_KEY&client_key=hermes&limit=3" | python -c '
import sys, json
data = json.load(sys.stdin)
for idx, item in enumerate(data.get("results", [])):
    title = item.get("content_description", "未命名")
    # 获取体积小、适合嵌入的 tinygif 或高质量 gif
    url = item.get("media_formats", {}).get("tinygif", {}).get("url")
    print(f"[{idx+1}] {title} -> {url}")
'
```

### 3. 下载动图保存至本地目录
选定满意的动图后，直接下载至本地指定路径：
```bash
curl -s -L "目标动图URL" -o "<工作目录>/素材/celebrate.gif"
```

---

## 三、 使用纪律与安全规范

1. **安全筛选级别**：
   - API 默认支持安全内容过滤参数 `contentfilter=high`；在工作与正式文档环境中，必须保持高安全级别过滤，杜绝检索到违规或不雅内容；
2. **下载前确认存储空间**：
   - 高清动图体积通常在 2MB 至 10MB 之间，批量下载时应确认本地磁盘存储位置，避免无节制下载占用过多空间。

---

## 四、 检查核对清单

- [ ] 环境变量 `$TENOR_API_KEY` 是否已正确配置在 `.env` 中？
- [ ] 搜索关键词是否明确，并配置了合理的分页上限（limit）？
- [ ] 下载保存时是否指定了正确的本地目录与以 `.gif` 结尾的绝对文件名？
