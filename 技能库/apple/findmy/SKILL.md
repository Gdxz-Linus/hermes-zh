---
name: findmy
description: "用于在 macOS 上通过查找应用定位苹果设备与 AirTag 时。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [FindMy, AirTag, location, tracking, macOS, Apple]
---

# 查找（苹果）

在 macOS 上通过查找应用定位苹果设备与 AirTag。苹果没有为查找提供命令行工具，因此本技能用 AppleScript 打开应用，再用屏幕截图读取设备位置。

## 前置条件

- **macOS**，装有查找应用，且已登录 iCloud
- 设备与 AirTag 已加入查找
- 终端已获得屏幕录制权限（系统设置 → 隐私与安全性 → 屏幕录制）
- **可选但建议**：安装 `peekaboo` 以获得更稳的界面自动化能力：`brew install steipete/tap/peekaboo`

## 适用场景

- 用户问「我的设备／猫／钥匙／包在哪里」
- 定位 AirTag
- 查看设备位置（iPhone、iPad、Mac、AirPods）
- 长期观察宠物或物品的移动轨迹（AirTag 巡逻路线）

## 方法一：AppleScript 加屏幕截图（基础）

### 打开查找并切换页面

```bash
# 打开查找应用
osascript -e 'tell application "FindMy" to activate'

# 等界面加载
sleep 3

# 截取查找窗口
screencapture -w -o ~/.hermes/cache/scratch/findmy.png
```

然后用 `vision_analyze` 读截图：

```
vision_analyze(image_url="~/.hermes/cache/scratch/findmy.png", question="界面上有哪些设备或物品，各自在什么位置？")
```

### 在标签页之间切换

```bash
# 切到设备页
osascript -e '
tell application "System Events"
    tell process "FindMy"
        click button "Devices" of toolbar 1 of window 1
    end tell
end tell'

# 切到物品页（AirTag）
osascript -e '
tell application "System Events"
    tell process "FindMy"
        click button "Items" of toolbar 1 of window 1
    end tell
end tell'
```

## 方法二：peekaboo 界面自动化（推荐）

装有 `peekaboo` 时，用它操作界面更稳：

```bash
# 打开查找
osascript -e 'tell application "FindMy" to activate'
sleep 3

# 截图并标注可点击元素
peekaboo see --app "FindMy" --annotate --path ~/.hermes/cache/scratch/findmy-ui.png

# 按元素编号点击指定设备或物品
peekaboo click --on B3 --app "FindMy"

# 截取详情页
peekaboo image --app "FindMy" --path ~/.hermes/cache/scratch/findmy-detail.png
```

然后用视觉能力分析：

```
vision_analyze(image_url="~/.hermes/cache/scratch/findmy-detail.png", question="这个设备或物品显示的位置在哪？有地址或坐标就一并给出。")
```

## 工作流：长期跟踪 AirTag 位置

用于观察 AirTag 的移动（例如追踪猫的活动路线）：

```bash
# 1. 打开查找并切到物品页
osascript -e 'tell application "FindMy" to activate'
sleep 3

# 2. 点开该 AirTag（页面必须保持打开，AirTag 只在页面打开时刷新位置）

# 3. 定时截图
while true; do
    screencapture -w -o ~/.hermes/cache/scratch/findmy-$(date +%H%M%S).png
    sleep 300  # 每 5 分钟一次
done
```

逐张用视觉能力提取坐标，再拼出移动路线。

## 限制

- 查找**没有命令行接口，也没有 API**，只能用界面自动化
- AirTag 只在查找页面处于打开状态时才刷新位置
- 定位精度取决于附近加入查找网络的苹果设备
- 截图需要屏幕录制权限
- AppleScript 的界面自动化可能随 macOS 版本变化而失效

## 规则

1. 跟踪 AirTag 时让查找应用保持在前台，最小化后位置不再刷新
2. 截图内容交给 `vision_analyze` 读，不要试图解析像素
3. 需要长期跟踪时，用 cronjob 定时截图并记录位置
4. 尊重隐私，只跟踪用户本人拥有的设备与物品
