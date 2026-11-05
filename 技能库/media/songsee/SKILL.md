---
name: songsee
description: "用于通过 songsee 命令行工具分析音频文件，并生成声学语谱图与多维特征图。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  commands: [songsee]
metadata:
  hermes:
    tags: [音频分析, 语谱图, 频谱可视化, 梅尔倒谱, 声学特征, 音乐可视化]
    category: media
    related_skills: []
    homepage: https://github.com/steipete/songsee
---

# 音频频谱与声学特征可视化指南（songsee）

## 概述

指导在终端环境中使用开源音频分析工具 `songsee`，对各类常见音频文件（如 WAV、MP3、FLAC 等）进行声学特征计算与可视化图表生成。支持输出高分辨率线性语谱图、梅尔刻度频谱、十二半音特征图以及梅尔倒谱系数图（MFCC），帮助直观评估音频音质、频响分布与音乐旋律结构。

## 适用场景

- “分析一段录音的背景底噪与频率响应，生成高清语谱图”
- “对一段音乐旋律进行十二半音音阶特征分析并输出可视化面板”
- “对比两段音频在特定频段上的能量衰减差异”

---

## 一、 前置准备与环境检查

使用本技能需确认本地已安装 `songsee` 命令行程序：

1. **环境检查**：
   ```bash
   songsee --help
   ```
2. **支持的音频格式**：
   - 原生支持标准未压缩音频（WAV）以及常见压缩音频格式（MP3、FLAC、OGG 等）。

---

## 二、 常用分析与可视化命令范式

### 1. 生成综合声学特征面板图（默认推荐）
对音频进行全方位分析，生成包含波形、梅尔频谱、音阶特征与倒谱系数的多面板复合大图：
```bash
songsee "D:/Hermes/音频/sample.mp3" -o "D:/Hermes/分析图/sample-dashboard.png"
```

### 2. 单独生成高精度梅尔频谱图
重点观察人耳听觉感知的频率能量随时间分布：
```bash
songsee "D:/Hermes/音频/sample.wav" --feature mel -o "D:/Hermes/分析图/mel-spec.png"
```

### 3. 生成十二半音特征图
分析音乐旋律与和弦走向（将频率归一化映射至 12 个半音阶上）：
```bash
songsee "D:/Hermes/音频/sample.mp3" --feature chroma -o "D:/Hermes/分析图/chroma.png"
```

### 4. 生成梅尔倒谱系数图（MFCC）
提取语音音色特征与说话人声学模型特征：
```bash
songsee "D:/Hermes/音频/voice.wav" --feature mfcc -o "D:/Hermes/分析图/voice-mfcc.png"
```

---

## 三、 输出规范与结果交付

1. **输出图像格式**：生成的产物为标准的 PNG 高清栅格图像；
2. **在会话中直接交付**：
   - 图像文件生成完毕后，按照 Hermes 桌面客户端标准交付规范，在回复中直接输出媒体呈现指令：
     ```
     MEDIA:D:/Hermes/分析图/sample-dashboard.png
     ```
   - 界面将自动就地渲染该声学分析图像，供直接审阅频响特征。

---

## 四、 检查核对清单

- [ ] 输入的音频文件路径是否存在且格式受支持？
- [ ] 输出目录是否已存在，或由工具自动创建了父级目录？
- [ ] 生成图片后是否使用了标准的 `MEDIA:` 指令提供界面预览？
