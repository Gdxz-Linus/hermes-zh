---
name: p5js
description: "用于编写 p5.js 创意编程脚本，生成交互式图形、生成艺术与 WebGL 视觉动效。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [p5js, 创意编程, 生成艺术, canvas, 交互设计, webgl, 着色器, 粒子系统]
    category: creative
    related_skills: [manim-video, ascii-video, popular-web-designs]
---

# p5.js 创意编程与生成艺术全流程指南

## 概述

指导使用现代前端创意编程框架 p5.js，将算法、数学公式、物理模拟与交互事件转化为极具视觉美感的浏览器端动态图形、生成艺术作品与 WebGL 视觉特效。支持构建交互式网页画布、粒子动力学系统、流场模拟、自定义 GLSL 着色器，并可无损导出为 HTML 单页、SVG 矢量图、PNG 序列帧或 MP4/GIF 视频。

## 适用场景

- “用 p5.js 编写一个基于柏林噪声算法的有机流场粒子动画”
- “制作一个支持鼠标拖拽交互与音阶共振的物理重力模拟小实验”
- “设计一段基于 WebGL 与自定义着色器的几何分形艺术图”
- “生成一组高分辨率的生成艺术海报并导出为可打印的矢量文件”

---

## 一、 核心架构与单文件 HTML 运行范式

p5.js 围绕经典的生命周期设计：
- `setup()`：初始化运行环境、创建画布、配置色彩模式与帧率；
- `draw()`：每秒循环执行的主渲染循环，驱动画面逐帧演进。

### 单文件自包含 HTML 标准模板：
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>p5.js 创意艺术展示</title>
  <!-- 引入官方 CDN 脚本 -->
  <script src="https://cdn.jsdelivr.net/npm/p5@1.9.0/lib/p5.min.js"></script>
  <style>
    body {
      margin: 0;
      padding: 0;
      background: #0f1115;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      overflow: hidden;
    }
  </style>
</head>
<body>
  <script>
    let particles = [];
    const NUM_PARTICLES = 300;

    function setup() {
      createCanvas(800, 600);
      background(15, 17, 21);
      // 初始化粒子群
      for (let i = 0; i < NUM_PARTICLES; i++) {
        particles.push({
          pos: createVector(random(width), random(height)),
          vel: createVector(0, 0),
          color: color(random(100, 255), random(150, 220), 255, 180)
        });
      }
    }

    function draw() {
      // 半透明背景实现运动残影拖尾效果
      background(15, 17, 21, 25);

      for (let p of particles) {
        // 基于柏林噪声计算流动角度
        let angle = noise(p.pos.x * 0.005, p.pos.y * 0.005, frameCount * 0.002) * TWO_PI * 2;
        p.vel = p5.Vector.fromAngle(angle).mult(2);
        p.pos.add(p.vel);

        // 边界环回检测
        if (p.pos.x < 0) p.pos.x = width;
        if (p.pos.x > width) p.pos.x = 0;
        if (p.pos.y < 0) p.pos.y = height;
        if (p.pos.y > height) p.pos.y = 0;

        stroke(p.color);
        strokeWeight(1.5);
        point(p.pos.x, p.pos.y);
      }
    }
  </script>
</body>
</html>
```

---

## 二、 常用生成艺术核心技法

1. **粒子系统与动力学模拟**：
   - 为每个粒子赋予位置向量、速度向量与加速度向量；
   - 在主循环中逐帧累加运动轨迹。
2. **柏林噪声流场**：
   - 相比纯随机数 `random()`，使用 `noise(x, y)` 产生平滑连续的有机变化，适合模拟水流、烟雾、云层和地形起伏。
3. **WebGL 与三维几何渲染**：
   - 画布创建时传入 `createCanvas(800, 600, WEBGL)` 开启硬件加速渲染；
   - 支持使用 `rotateX()`、`box()`、`sphere()` 等 API 构建具备三维空间透视的场景。

---

## 三、 交付与本地呈现标准

1. **直接写入自包含 HTML**：
   - 使用 `write_file` 将包含脚本的完整代码保存至本地文件（如 `D:/Hermes/艺术设计/flow-field.html`）；
2. **应用内实时预览**：
   - 在回复中输出标准预览标记，供用户直接在桌面端窗口中观看动画并进行鼠标交互：
     ```
     ::preview{file="D:/Hermes/艺术设计/flow-field.html"}
     ```

---

## 四、 检查核对清单

- [ ] 是否采用了自包含的 HTML 单文件结构，引入了可靠的官方 CDN？
- [ ] 动画循环中是否妥善控制了粒子数量与计算复杂度，保证了 60fps 流畅帧率？
- [ ] 产物是否提供了标准的应用内预览标识？
