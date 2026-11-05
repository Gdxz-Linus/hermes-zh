---
name: apple-reminders
description: "用于通过 remindctl 添加、查看与完成苹果提醒事项时。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Reminders, tasks, todo, macOS, Apple]
prerequisites:
  commands: [remindctl]
---

# 苹果提醒事项

用 `remindctl` 在终端直接管理苹果提醒事项。任务经 iCloud 在各苹果设备之间同步。

## 前置条件

- **macOS**，且装有提醒事项应用
- 安装：`brew install steipete/tap/remindctl`
- 首次使用时按提示授予提醒事项权限
- 查状态：`remindctl status`；申请授权：`remindctl authorize`

## 适用场景

- 用户提到「提醒事项」或「提醒事项应用」
- 创建带截止日期的个人待办，并同步到 iPhone
- 管理苹果提醒事项的清单
- 用户要求任务出现在自己的 iPhone 或 iPad 上

## 不适用场景

- 安排智能体定时告警 → 改用 cronjob 工具
- 日历事件 → 用苹果日历或谷歌日历
- 项目任务管理 → 用 GitHub Issue、Notion 等
- 用户说「提醒我」但实际指智能体告警 → 先问清

## 常用命令

### 查看提醒事项

```bash
remindctl                    # 今天的提醒事项
remindctl today              # 今天
remindctl tomorrow           # 明天
remindctl week               # 本周
remindctl overdue            # 已逾期
remindctl all                # 全部
remindctl 2026-01-04         # 指定日期
```

### 管理清单

```bash
remindctl list               # 列出全部清单
remindctl list Work          # 显示指定清单
remindctl list Projects --create    # 新建清单
remindctl list Work --delete        # 删除清单
```

### 新建提醒事项

```bash
remindctl add "买牛奶"
remindctl add --title "给妈妈打电话" --list Personal --due tomorrow
remindctl add --title "会议准备" --due "2026-02-15 09:00"
```

### 截止时间与闹钟的区别

`--due` 与 `--alarm` 是两个不同字段：

- `--due` 设置提醒事项的截止日期与时间。
- `--alarm` 设置 EventKit 的通知触发时间。带具体时间的截止项可能默认在截止时刻发送通知，但用户要求提前提醒时必须显式传 `--alarm`。

例：截止时间为 14:00，通知提前 30 分钟：

```bash
remindctl add --title "理发" --due "2026-05-15 14:00" --alarm "2026-05-15 13:30"
```

修改已有的提醒事项：

```bash
remindctl edit 87354 --due "2026-05-15 14:00" --alarm "2026-05-15 13:30"
```

提醒事项界面可能按闹钟时间显示或归组该条目，因为通知在那个时刻触发。要用 JSON 输出核实，不要凭空认定截止时间被改动：

```bash
remindctl today --json
```

预期字段：

- `dueDate`：真实截止时间
- `alarmDate`：通知时间，也就是提前提醒的时刻

苹果公开的 `EKReminder` 文档只列提醒事项特有的属性。闹钟能力来自继承的 `EKCalendarItem` 行为，由 remindctl 的 `--alarm` 参数暴露。

### 完成与删除

```bash
remindctl complete 1 2 3          # 按编号完成
remindctl delete 4A83 --force     # 按编号删除
```

### 输出格式

```bash
remindctl today --json       # JSON，便于程序处理
remindctl today --plain      # TSV 格式
remindctl today --quiet      # 只输出数量
```

## 日期格式

`--due` 与日期筛选接受以下写法：

- `today`、`tomorrow`、`yesterday`
- `YYYY-MM-DD`
- `YYYY-MM-DD HH:mm`
- ISO 8601（`2026-01-04T12:34:56Z`）

## 规则

1. 用户说「提醒我」时先问清：要苹果提醒事项（同步到手机），还是要智能体定时告警
2. 创建前必须确认提醒内容与截止日期
3. 需要程序解析时用 `--json`
