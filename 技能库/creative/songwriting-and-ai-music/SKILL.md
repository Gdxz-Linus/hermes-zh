---
name: songwriting-and-ai-music
description: "用于进行音乐创作、歌词结构编排与生成适配 Suno 等平台的专业 AI 音乐提示词。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [音乐创作, 歌词编排, suno提示词, 曲风标签, 音乐生成, 创意写作]
    category: creative
    related_skills: [chinese-official-writing]
---

# 音乐创作与 AI 音乐提示词工程指南（Songwriting & AI Music）

## 概述

指导开展专业的歌词创作、经典歌曲段落结构编排，以及为现代 AI 音乐生成平台（如 Suno、Udio 等）设计精准的曲风与编曲提示词。指导如何利用结构化元标签控制旋律起伏、高潮爆发、乐器独奏与人声表现，将灵感构思转化为完整度极高的音乐作品。

## 适用场景

- “为一段关于深夜写代码的经历写一首民谣或摇滚风格的歌词”
- “为 Suno 生成适配某首歌词的专业曲风标签、乐器组合与情绪提示词”
- “改编一段既有歌词进行趣味填词，同时保持原曲的押韵与节拍”
- “设计包含前奏、主歌、副歌、乐器间奏与尾声的完整音乐结构脚本”

---

## 一、 经典流行音乐六段式结构与元标签

在编写提交给 AI 音乐生成器的歌词时，使用标准的结构方括号元标签能够精准引导模型在特定时间点切换编曲能量：

| 结构标签 | 音乐角色与功能 | 编曲与情绪指导 |
| :--- | :--- | :--- |
| `[Intro]` | **前奏** | 确立全曲基调与核心和弦，通常为纯乐器铺垫或轻柔哼唱。 |
| `[Verse 1]` / `[Verse 2]` | **主歌（第1段/第2段）** | 交代故事背景与叙事细节，旋律平缓，能量适中。 |
| `[Pre-Chorus]` | **导歌（副歌预备）** | 节奏开始推进，和弦情绪逐渐爬升，为副歌的高潮爆发蓄势。 |
| `[Chorus]` | **副歌（核心高潮）** | 全曲最抓人、最容易记忆的核心高潮旋律，能量达到峰值，乐器全面加入。 |
| `[Bridge]` | **桥段** | 打破前面主副歌的重复感，引入全新的旋律走势与情感转折。 |
| `[Guitar Solo]` / `[Instrumental]` | **乐器独奏 / 间奏** | 人声留白，突出电吉他、钢琴、合成器或小提琴的独奏表现力。 |
| `[Outro]` | **尾声** | 渐弱淡出或强力收尾，给全曲画上完整句号。 |

---

## 二、 Suno 曲风与编曲提示词工程范式

Suno 的风格输入框（Style of Music）对层级分明的关键词组合最为敏感，标准提示词配方由四个维度构成：

```
[核心曲风] + [细分流派/时代特征] + [核心配器] + [情绪基调与人声特质]
```

### 经典曲风范例配方：
1. **暗黑工业合成器浪潮**：
   ```
   dark synthwave, 1980s retro, analog synthesizer, arpeggiated bass, driving drums, melancholic, male baritone vocals
   ```
2. **现代流行摇滚**：
   ```
   modern pop rock, energetic electric guitars, punchy drums, uplifting chorus, powerful female belt vocals, stadium anthemic
   ```
3. **东方古典民谣**：
   ```
   chinese acoustic folk, wooden acoustic guitar, bamboo flute, guzheng, warm, intimate, storytelling, soft male vocals
   ```

---

## 三、 完整创作示例与标准格式

提交给生成器的标准交付文本包含曲风参数与结构化歌词两部分：

```markdown
### 推荐曲风标签：
cyberpunk dark synthpop, pulsating electronic bass, futuristic synthesizers, driving tempo, atmospheric, confident female vocals

### 歌曲结构与歌词：

[Intro]
(Atmospheric synth pads fading in, slow heartbeat rhythm)

[Verse 1]
屏幕亮起冷光，窗外暴雨未歇
数万行日志流过，在指尖停歇
那些未被解答的异常，在深夜里重现

[Pre-Chorus]
时钟悄悄走向凌晨三点
所有的连接突然跨越了界限

[Chorus]
编译全部通过，没有一次报错
所有的数据流在光缆中穿梭
所有的疲惫在此刻彻底解脱
[Bass Drop]
这就是工程师坚守的承诺

[Bridge]
(Synthesizer solo builds up energy)
纵然外部世界瞬息万变
代码的逻辑永远不会欺骗

[Chorus]
编译全部通过，没有一次报错
所有的数据流在光缆中穿梭
所有的疲惫在此刻彻底解脱

[Outro]
终端渐渐安静，晨光悄悄洒进
(Music slowly fades out)
[End]
```

---

## 四、 检查核对清单

- [ ] 歌词结构是否包含了前奏、主歌、副歌等标准的元标签，引导编曲起伏？
- [ ] 曲风提示词是否涵盖了核心流派、配器与人声特征，避免了空泛词汇？
- [ ] 韵脚与音节节奏是否自然顺畅，适合真实音乐演唱？
