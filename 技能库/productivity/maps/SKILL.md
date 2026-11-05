---
name: maps
description: "用于基于 OpenStreetMap 与 OSRM 进行地理编码、兴趣点检索、路线规划与距离测算。"
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [地图服务, 地理编码, 兴趣点检索, 路线规划, 导航指引, 距离测算, openstreetmap, osrm]
    category: productivity
    requires_toolsets: [terminal]
---

# 地图地理信息与路线规划指南（OpenStreetMap / OSRM）

## 概述

指导基于开源的 OpenStreetMap（Nominatim 引擎）、Overpass API 以及 OSRM 路由引擎，在终端环境中免 API 密钥进行地理位置智能查询。支持地名转经纬度坐标（地理编码）、坐标转详细地址（逆地理编码）、周边设施与兴趣点（POI）检索、两地距离与通行耗时测算，以及分段路线导航指引。

## 适用场景

- “查询某个地名或大厦的具体经纬度坐标”
- “根据当前经纬度位置，查找方圆 1 公里内的医院、药店或充电桩”
- “测算从 A 地驾车到 B 地的实际行驶路线距离与预估通行时间”
- “获取从起点到终点的分段转弯行驶导航路线”
- “查询特定城市或经纬度所在的时区与标准时间偏移”

---

## 一、 核心执行入口

所有功能均由内置的 Python 客户端脚本提供（零第三方依赖，纯标准库运行）：

```bash
# 客户端脚本相对路径
MAPS_CLIENT=scripts/maps_client.py
```

---

## 二、 八大常用功能命令范式

### 1. 地名地理编码（地名 $	o$ 经纬度坐标）
输入地名或建筑物名称，返回其精确的经纬度与格式化地址：
```bash
python scripts/maps_client.py search "深圳市南山区科技园"
```

### 2. 逆地理编码（经纬度坐标 $	o$ 详细物理地址）
输入纬度和经度，反查其行政区划与街道门牌：
```bash
python scripts/maps_client.py reverse 22.5431 113.9534
```

### 3. 周边兴趣点检索
在指定坐标周边检索特定类别的便民设施或场所：
```bash
# 检索指定坐标周边 1000 米内的医院与药店
python scripts/maps_client.py nearby 22.5431 113.9534 --radius 1000 --category hospital,pharmacy

# 支持直接指定地名作为中心点
python scripts/maps_client.py nearby --near "广州南站" --category restaurant --limit 5
```
- **常用分类代码**：`restaurant`（餐厅）、`hotel`（酒店）、`hospital`（医院）、`pharmacy`（药店）、`gas_station`（加油站）、`charging_station`（充电站）、`bank`（银行）、`parking`（停车场）。

### 4. 两地距离与预估耗时测算
计算起点到终点的实际道路距离与耗时（支持驾车、骑行、步行）：
```bash
# 测算驾车距离（--mode car）
python scripts/maps_client.py distance "北京南站" "北京大兴国际机场" --mode car

# 测算步行距离（--mode foot）
python scripts/maps_client.py distance "西湖风景区" "断桥残雪" --mode foot
```

### 5. 分段路线导航指引
输出包含分段路口与转弯提示的导航指令清单：
```bash
python scripts/maps_client.py directions "上海虹桥站" "外滩" --mode car
```

### 6. 指定矩形区域内的多点检索
在指定矩形地理范围内检索所有符合条件的设施：
```bash
python scripts/maps_client.py bbox 22.50 113.90 22.60 114.00 --category cafe
```

### 7. 时区信息查询
查询目标地点当前所处的时区标识、UTC 偏移量以及当前本地时间：
```bash
python scripts/maps_client.py timezone "Tokyo"
```

---

## 三、 使用纪律与公共服务规范

1. **遵守公共 API 请求速率约束**：
   - OpenStreetMap 与 Nominatim 属于公共开源基础设施，要求客户端请求频率不得高于每秒 1 次；
   - 客户端脚本内部已加入节流机制，在批量处理多个地点时应避免高频并发轰炸；
2. **坐标顺序规范**：
   - 命令行与日常表述中统一采用**“纬度，经度”**顺序，与国际通用规范保持一致；
3. **输出单位说明**：
   - 距离数值默认统一换算为公里或米，通行耗时统一表示为小时与分钟。

---

## 四、 检查核对清单

- [ ] 输入经纬度时是否核对了“纬度在前、经度在后”的标准顺序？
- [ ] 测算通行距离时是否明确指定了出行方式（驾车、骑行或步行）？
- [ ] 检索周边设施时是否设置了合理的搜索半径，避免返回空结果？
