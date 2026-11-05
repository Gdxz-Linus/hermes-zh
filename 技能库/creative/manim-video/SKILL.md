---
name: manim-video
description: "用于通过 Manim 社区版引擎编写数学与算法动画脚本，生成教学视频。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [manim, 数学动画, 算法可视化, 视频生成, 3blue1brown风格, 教学动效, python动画]
    category: creative
    related_skills: [ascii-video, p5js, architecture-diagram]
---

# Manim 数学与算法动画视频生成指南（Manim Community Edition）

## 概述

指导使用 Python 开源动画引擎 Manim 社区版（Manim CE，即知名科普频道 3Blue1Brown 背后的底层动画系统），将抽象复杂的数学定理、推导过程、算法数据流与系统架构演进，转化为结构严谨、视觉流畅的高清动画视频。

**核心创作原则**：
```
每一帧画面都应当传递确凿的知识结构，动画的核心价值在于将思维盲区转化为豁然开朗的顿悟时刻
```
在编写具体动画代码前，必须先理清视觉叙事主线：观众在此处容易产生什么直觉误区？通过怎样的几何变换或公式位移能够最清晰地揭示其内在规律？

## 适用场景

- “制作一段解释快速傅里叶变换或欧拉公式的几何动画”
- “将二叉树平衡旋转或图的最短路径算法动态演示出来”
- “制作一段带有数学公式推导、坐标系平移与曲线绘制的技术科普视频”
- “为技术方案设计带有动态高亮与数据流动效果的架构演进动画”

---

## 一、 动画制作四阶段标准工作流程

```
第一阶段：分镜头脚本设计（确立叙事主线、核心顿悟节点与各场景时长分配）
  ↓
第二阶段：场景与数学对象构建（定义坐标系、公式文本、几何图形与数据点）
  ↓
第三阶段：动效编排与状态追踪（使用变换、淡入淡出、路径追踪实现自然过渡）
  ↓
第四阶段：视频编译与交付（分级渲染低分辨率预览，验证无误后导出高清成品）
```

---

## 二、 核心动画代码编写范式

遵循 Manim CE 面向对象架构，所有视觉元素均派生自 Mobject 几何基类：

```python
from manim import *

class AlgorithmExplainer(Scene):
    def construct(self):
        # 1. 设置暗黑背景与坐标系
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            axis_config={"color": BLUE_D}
        )
        
        # 2. 构建数学公式（支持 LaTeX 语法解析）
        title = Title("注意力机制核心计算公式", font_size=36)
        formula = MathTex(
            r"	ext{Attention}(Q, K, V) = 	ext{softmax}\left(rac{QK^T}{\sqrt{d_k}}
ight)V",
            font_size=40
        )
        formula.set_color_by_tex("Q", YELLOW)
        formula.set_color_by_tex("K", TEAL)
        formula.set_color_by_tex("V", RED)

        # 3. 编排进场与变换动效
        self.play(Write(title))
        self.play(FadeIn(axes), run_time=1.5)
        self.play(Write(formula))
        self.wait(1)

        # 4. 高亮与局部变换
        box = SurroundingRectangle(formula[0][14:21], color=YELLOW, buff=0.1)
        self.play(Create(box))
        self.wait(2)
```

---

## 三、 视频渲染与分级导出命令

通过终端命令行编译 Manim Python 脚本并生成 MP4 视频文件：

### 1. 快速草稿预览（低分辨率，节省渲染时间）
在编写和调试动画逻辑阶段，使用 `-ql` 参数（480p, 15fps）快速验证排版与时序：
```bash
manim -ql scene.py AlgorithmExplainer
```

### 2. 高清成品渲染
逻辑验证无误后，使用 `-qh` 参数（1080p, 60fps）导出正式的高清视频：
```bash
manim -qh scene.py AlgorithmExplainer
```

### 3. 生成可嵌入网页的循环动态图（GIF）
```bash
manim -ql -i scene.py AlgorithmExplainer
```

---

## 四、 常见避坑与渲染排障

1. **LaTeX 编译依赖报错**：
   - 使用 `MathTex` 需要系统安装有 LaTeX 环境（如 MiKTeX 或 TeXLive）；
   - 若当前运行环境未安装 LaTeX，优先使用纯文本 `Text` 对象配合 Unicode 符号进行排版，避免因依赖缺失导致渲染中断；
2. **对象坐标重叠**：
   - 避免直接使用绝对坐标，优先使用相对布局方法（如 `next_to`、`shift`、`arrange`）保持元素间距协调；
3. **交付呈现**：
   - 导出的 MP4 文件存放在 `media/videos/` 目录下，在回复中直接输出媒体呈现指令提供界面播放：
     ```
     MEDIA:D:/Hermes/视频/AlgorithmExplainer.mp4
     ```

---

## 五、 检查核对清单

- [ ] 动画脚本是否围绕明确的核心逻辑展开，杜绝了无意义的花哨晃动？
- [ ] 调试阶段是否优先采用了低分辨率快速预览，节省了渲染等待时间？
- [ ] 涉及数学公式时是否确认了 LaTeX 环境可用性或选用了纯文本替代方案？
