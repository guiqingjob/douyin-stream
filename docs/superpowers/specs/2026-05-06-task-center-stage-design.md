# 任务中心阶段标识系统设计文档

**版本**: 1.1
**最后更新**: 2026-05-06
**创建日期**: 2026-05-06
**状态**: 已实施

---

## 1. 概述

### 1.1 背景

当前任务中心存在以下问题：
- 任务阶段定义混乱，用户无法清晰理解当前进度
- 缺少直观的可视化进度展示
- 错误信息不够友好，用户难以理解失败原因

### 1.2 目标

设计一套直观、易懂的阶段标识系统，让用户能够：
- 快速识别当前所处阶段
- 了解任务的具体进度
- 理解错误原因并知道如何处理

---

## 2. 阶段定义

### 2.1 完整阶段列表

| 阶段 | 显示名称 | 图标 | 颜色 | 进入条件 | 退出条件 |
|------|---------|------|------|---------|---------|
| CREATED | 等待中 | Clock3 | muted-foreground | 任务刚创建 | worker 开始处理 |
| FETCHING | 获取列表 | Loader2 (旋转) | primary | 调用 F2 SDK 获取视频列表 | 收到第一个视频数据或超时/错误 |
| AUDITING | 对账中 | CheckCircle | primary | 视频列表获取完成，开始扫描本地文件 | 对账完成，确定待下载列表 |
| DOWNLOADING | 下载中 | ArrowDown | primary | 开始下载第一个视频 | 所有待下载视频处理完毕 |
| TRANSCRIBING | 转写中 | FileText | primary | 开始转写第一个视频 | 所有视频转写处理完毕 |
| EXPORTING | 导出中 | Upload | primary | 开始导出第一个字幕文件 | 所有字幕文件导出完毕 |
| COMPLETED | 已完成 | CheckCircle2 | success | 所有阶段全部完成 | 无（终态） |
| FAILED | 失败 | XCircle | destructive | 发生不可恢复的错误 | 无（终态） |
| CANCELLED | 已取消 | Ban/MinusCircle | muted-foreground | 用户主动取消 | 无（终态） |

### 2.2 阶段详情

#### 阶段 0：CREATED（等待中）

| 属性 | 值 |
|------|-----|
| **显示名称** | 等待中 |
| **图标** | Clock3 |
| **颜色** | muted-foreground |
| **进度条** | 无（空状态） |
| **占位符百分比** | 0% |
| **动画** | 无 |

**显示文案：**
- 正常：等待开始...
- 超时：等待响应超时，请检查后台服务

**边界情况：**
- 如果超过 30 秒未进入 FETCHING，标记为 STALE 状态

---

#### 阶段 1：FETCHING（获取列表）

| 属性 | 值 |
|------|-----|
| **显示名称** | 获取列表 |
| **图标** | Loader2 (带旋转) |
| **颜色** | primary |
| **进度条** | indeterminate（来回移动） |
| **占位符百分比** | 0% |
| **动画** | 图标旋转 |

**显示文案：**
- 正常：正在获取视频列表...
- 已获取数量：正在获取视频列表 (已获取 45 个)...
- 超时：获取列表超时，重试中...
- 失败：获取列表失败：账号权限不足

**边界情况：**
1. 空列表 - 博主没有视频：直接进入 COMPLETED 状态，显示"该博主暂无视频"
2. 部分获取后超时 - 已有部分数据：继续用已有数据
3. 403/401 错误 - Cookie 失效：进入 FAILED，提示"账号已失效，请更新 Cookie"
4. 网络错误 - 可重试：进入 FAILED 但标记 auto_retry=true

---

#### 阶段 2：AUDITING（对账中）

| 属性 | 值 |
|------|-----|
| **显示名称** | 对账中 |
| **图标** | CheckCircle |
| **颜色** | primary |
| **进度条** | 不确定 |
| **占位符百分比** | 0% |
| **动画** | 无 |

**显示文案：**
- 正常：对账中：发现 8 个本地已有，12 个待下载
- 全部已有：对账完成：全部 20 个视频已存在，跳过下载
- 全部缺失：对账完成：需要下载 20 个视频

**边界情况：**
1. 本地目录不存在 - 视为 0 个已有文件
2. 文件损坏 - 标记为 corrupt，进入待下载列表
3. 数据库查询失败 - 跳过 DB 检查

---

#### 阶段 3：DOWNLOADING（下载中）

| 属性 | 值 |
|------|-----|
| **显示名称** | 下载中 |
| **图标** | ArrowDown |
| **颜色** | primary |
| **进度条** | 确定进度 N/M |
| **百分比** | (N/M) × 100% |
| **动画** | 进度条平滑过渡 |

**显示文案：**
- 正常：正在下载 (3/12)：视频标题...
- 下载完成：正在下载 (12/12)：全部完成，准备转写...
- 全部跳过：下载完成：所有视频已存在，跳过

**边界情况：**
1. 单个视频下载失败 - 记录错误，继续下载下一个，最终状态为 PARTIAL_FAILED
2. 下载被限流 (429) - 等待 60 秒后重试
3. Cookie 失效 (401) - 中断下载，进入 FAILED
4. 磁盘空间不足 - 中断下载，进入 FAILED
5. 用户取消 - 停止下载，保持 CANCELLED

---

#### 阶段 4：TRANSCRIBING（转写中）

| 属性 | 值 |
|------|-----|
| **显示名称** | 转写中 |
| **图标** | FileText |
| **颜色** | primary |
| **进度条** | 确定进度 N/M |
| **百分比** | (N/M) × 100% |
| **动画** | 进度条平滑过渡 |

**显示文案：**
- 正常：正在转写 (2/8)：视频标题...
- 账号信息：正在转写 (2/8) [账号A]：视频标题...
- 全部跳过：转写完成：无需转写的视频

**边界情况：**
1. 单个视频转写失败 - 记录错误类型，继续处理下一个
2. 配额不足 (quota) - 显示"配额不足 [账号A] 0小时"，切换账号重试
3. 网络错误 - 自动重试 3 次，仍失败则标记失败
4. 视频无音频 - 跳过转写，标记 skipped

---

#### 阶段 5：EXPORTING（导出中）

| 属性 | 值 |
|------|-----|
| **显示名称** | 导出中 |
| **图标** | Upload |
| **颜色** | primary |
| **进度条** | 单一进度条 |
| **百分比** | 实际百分比 |
| **动画** | 进度条平滑过渡 |

**显示文案：**
- 正常：正在导出 (0/8)...
- 导出完成：导出完成：8 个字幕文件已保存

---

#### 阶段 6：COMPLETED（已完成）

| 属性 | 值 |
|------|-----|
| **显示名称** | 已完成 |
| **图标** | CheckCircle2 |
| **颜色** | success (#22c55e) |
| **进度条** | 满进度条 100% |
| **百分比** | 100% |
| **动画** | 无 |

**显示文案：**
- 全部成功：已完成：下载 10 个，转写 8 个
- 部分失败：已完成：下载 10 个（失败 2 个），转写 8 个（失败 1 个）
- 全部跳过：已完成：无需处理

---

#### 阶段 7：FAILED（失败）

| 属性 | 值 |
|------|-----|
| **显示名称** | 失败 |
| **图标** | XCircle |
| **颜色** | destructive (#ef4444) |
| **进度条** | 无 |
| **百分比** | 不显示 |

**显示文案格式：**失败：[错误分类] 详细原因

**错误分类与用户提示：**

| 错误类型 | 显示文案 | 用户操作建议 |
|---------|---------|-------------|
| network | 网络连接失败 | 请检查网络后重试 |
| timeout | 请求超时 | 网络不稳定，可重试 |
| auth | 账号权限不足 | 请更新 Cookie |
| quota | API 配额不足 | 账号额度用完，请添加新账号 |
| rate_limit | 触发频率限制 | 请求太频繁，稍后重试 |
| not_found | 资源不存在 | 视频可能已被删除 |
| disk_full | 磁盘空间不足 | 请清理磁盘空间 |
| unknown | 发生未知错误 | 请联系开发者 |

---

#### 阶段 8：CANCELLED（已取消）

| 属性 | 值 |
|------|-----|
| **显示名称** | 已取消 |
| **图标** | Ban/MinusCircle |
| **颜色** | muted-foreground |
| **进度条** | 无 |
| **百分比** | 不显示 |

**显示文案：**
- 用户取消：已取消
- 超时取消：已超时自动取消
- 部分完成取消：已取消（已完成 N 个）

---

## 3. 视觉设计

### 3.1 阶段进度条

```
[●] ─── [●] ─── [●] ─── [◐] ─── [○] ─── [○] ─── [○]
  创建   获取   对账   下载   转写   导出   完成

● = 已完成（绿色）   ○ = 未完成（灰色）   ◐ = 当前阶段（蓝色脉冲）
```

### 3.2 任务卡片布局

**紧凑模式：**
```
┌─────────────────────────────────────────────────────────┐
│ ⬇️ 下载 (4/12)          [████████░░░░░░░░░░]  33%    │
│ 正在下载：第4个视频的标题...                    🔄 进行中 │
└─────────────────────────────────────────────────────────┘
```

**展开模式：**
```
┌─────────────────────────────────────────────────────────┐
│  下载任务                                              │
├─────────────────────────────────────────────────────────┤
│  ⬇️ 下载         33%  ████████░░░░░░░░░░░░         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━          │
│  当前：第4个视频的标题... (4/12)                       │
│                                                       │
│  📊 统计：下载完成 4 个，跳过 8 个，失败 0 个          │
│                                                       │
│  [停止]  [重试]                                       │
└─────────────────────────────────────────────────────────┘
```

---

## 4. 数据结构

### 4.1 后端进度数据结构

```python
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class Stage(str, Enum):
    CREATED = "created"
    FETCHING = "fetching"
    AUDITING = "auditing"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class DownloadProgress:
    downloaded: int = 0
    skipped: int = 0
    failed: int = 0
    total: int = 0
    current_video: str = ""
    current_index: int = 0

@dataclass
class TranscribeProgress:
    done: int = 0
    skipped: int = 0
    failed: int = 0
    total: int = 0
    current_video: str = ""
    current_account: str = ""

@dataclass
class TaskProgress:
    task_id: str
    stage: Stage = Stage.CREATED
    overall_percent: float = 0.0
    download_progress: Optional[DownloadProgress] = None
    transcribe_progress: Optional[TranscribeProgress] = None
    error_count: int = 0
    errors: list = field(default_factory=list)
    start_time: Optional[str] = None
```

### 4.2 API 响应格式

```json
// GET /api/v1/tasks/{task_id}
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_type": "pipeline",
  "status": "RUNNING",
  "progress": {
    "stage": "downloading",
    "overall_percent": 33.3,
    "download_progress": {
      "downloaded": 4,
      "skipped": 8,
      "failed": 0,
      "total": 12,
      "current_video": "这是一个视频标题...",
      "current_index": 4
    },
    "transcribe_progress": null,
    "error_count": 0,
    "errors": []
  },
  "msg": "正在下载 (4/12)：这是一个视频标题...",
  "start_time": "2026-05-06T10:30:00"
}
```

---

## 5. 实施计划

### 5.1 修改文件清单

**后端：**
1. `src/media_tools/domain/entities/task.py` - 添加 Stage 枚举和 TaskProgress 数据类
2. `src/media_tools/services/pipeline_progress.py` - 重构进度构建逻辑
3. `src/media_tools/douyin/core/cancel_registry.py` - 更新进度追踪函数
4. `src/media_tools/douyin/core/downloader.py` - 集成新进度追踪

**前端：**
1. `frontend/src/types/index.ts` - 添加新的类型定义
2. `frontend/src/lib/task-utils.ts` - 更新任务状态解析逻辑
3. `frontend/src/components/layout/TaskMonitorPanel/TaskItem.tsx` - 更新任务卡片组件
4. `frontend/src/components/layout/TaskMonitorPanel.tsx` - 更新面板组件

### 5.2 实施优先级

1. **Phase 1**: 后端数据结构定义
2. **Phase 2**: 进度追踪集成
3. **Phase 3**: 前端类型和工具函数
4. **Phase 4**: UI 组件更新

---

## 6. 验收标准

1. ✅ 用户能清晰看到当前所处阶段
2. ✅ 进度条准确显示 N/M 格式
3. ✅ 当前处理的视频标题直接显示
4. ✅ 错误信息友好且有操作建议
5. ✅ 阶段图标和颜色符合设计规范
