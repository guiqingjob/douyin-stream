# Media Tools 重构路线图

> 目标：在保持功能完整的前提下，逐步重构代码库，消除技术债务。
>
> 原则：每完成一个阶段 → 测试验收 → git commit → 下一阶段。

---

## 阶段 0：重构基线（1-2 天）

**目标**：建立安全的重构基线，确保后续每一步都可验证。

### 0.1 修复当前回归测试失败

当前有 6 个 backend regression 测试 + 3 个 frontend regression 测试失败。

| 测试 | 问题 | 修复方案 |
|------|------|----------|
| `test_pragma_table_info_uses_validation[assets]` | `assets.py:49` 使用 f-string PRAGMA | 改为参数化查询或 validate_identifier |
| `test_pragma_table_info_uses_validation[creators]` | `creators.py:91` 同上 | 同上 |
| `test_get_table_columns_unified` | `_get_table_columns` 在 assets.py 和 creators.py 重复 | 提取到 `db/core.py` |
| `test_no_hardcoded_vh_calc` | `Discovery.tsx:443` calc(100vh - 320px) | 使用 CSS flex 替代 |
| `test_no_silent_catch` | `Settings.tsx:113` .catch(() => {}) | 改为 .catch(err => console.error(err)) |
| `test_page_components_not_too_large` | Settings.tsx 798 行 | 在阶段 4 处理，此处先标记 |

**验收标准**：
- [ ] `pytest tests/regression/ -q` 全部通过
- [ ] `pytest tests/ -q` 全部通过

**git commit**：`fix: 修复所有回归测试失败，建立重构基线`

### 0.2 建立集成测试框架

新建 `tests/integration/test_e2e_workflow.py`：

```python
"""端到端工作流测试 - 验证完整的下载+转写流程"""
import pytest
import sqlite3

class TestEndToEndWorkflow:
    """模拟完整的创作者同步 → 下载 → 转写流程"""

    def test_creator_sync_creates_task(self):
        """POST /download/creator 创建任务并返回 task_id"""
        pass

    def test_task_progress_updates(self):
        """任务进度正确更新到数据库"""
        pass

    def test_websocket_broadcasts_progress(self):
        """WebSocket 正确广播进度消息"""
        pass

    def test_auto_transcribe_runs_after_download(self):
        """开启自动转写时，下载完成后自动触发转写"""
        pass

    def test_task_completion_has_result_summary(self):
        """任务完成时包含正确的 result_summary"""
        pass
```

**验收标准**：
- [ ] 新建 `tests/integration/` 目录
- [ ] 至少 3 个集成测试通过
- [ ] `pytest tests/integration/ -v` 输出详细结果

**git commit**：`test: 添加集成测试框架和端到端工作流测试`

### 0.3 定义统一 WebSocket 消息格式

当前 WebSocket 消息格式混乱，后端发送的字段和前端解析不一致。

**新增 `src/media_tools/api/schema.py`**：

```python
from pydantic import BaseModel, Field
from typing import Literal

class WSProgressMessage(BaseModel):
    type: Literal["progress"] = "progress"
    task_id: str
    status: Literal["RUNNING", "COMPLETED", "FAILED", "PAUSED"]
    progress: float = Field(ge=0.0, le=1.0)
    stage: str  # "downloading" | "transcribing" | "completed" | "failed"
    message: str
    result_summary: dict | None = None
    subtasks: list[dict] | None = None

class WSCompletedMessage(BaseModel):
    type: Literal["completed"] = "completed"
    task_id: str
    status: Literal["COMPLETED", "FAILED"]
    message: str
    result_summary: dict | None = None
    subtasks: list[dict] | None = None
```

**验收标准**：
- [ ] 所有 WebSocket 发送点使用统一 schema
- [ ] 前端 `useStore.ts` 正确解析新格式
- [ ] WebSocket 消息包含 `stage` 字段

**git commit**：`refactor: 统一 WebSocket 消息格式`

---

## 阶段 1：配置系统统一（2-3 天）

**目标**：消除三源鼎立，数据库是唯一事实源。

### 1.1 提取统一配置模块

**新增 `src/media_tools/core/config.py`**（核心文件）：

```python
"""统一配置系统

所有配置项存储在数据库 SystemSettings 表。
启动时加载到内存缓存，修改时写回数据库。

配置优先级（从高到低）：
1. 运行时修改（通过 API）→ 写入数据库
2. 数据库 SystemSettings 表
3. 环境变量（仅用于初始化）
4. 默认值
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import sqlite3

@dataclass(frozen=True)
class AppConfig:
    """应用配置 - 不可变，修改时创建新实例"""
    concurrency: int = 5
    auto_transcribe: bool = False
    auto_delete: bool = True
    project_root: Path = field(default_factory=lambda: Path.cwd())

    @property
    def db_path(self) -> Path:
        return self.project_root / "media_tools.db"

    @property
    def download_path(self) -> Path:
        return self.project_root / "downloads"

    @property
    def output_dir(self) -> Path:
        return self.project_root / "output"


class ConfigManager:
    """配置管理器 - 单例模式"""
    _instance: "ConfigManager | None" = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: Path | None = None):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._db_path = db_path
        self._cache: AppConfig | None = None
        self._load()

    def _load(self) -> None:
        """从数据库加载所有配置"""
        # 从 SystemSettings 表读取
        pass

    def get(self) -> AppConfig:
        if self._cache is None:
            self._load()
        return self._cache

    def set(self, key: str, value: Any) -> None:
        """修改配置，写入数据库并刷新缓存"""
        pass

    def reload(self) -> None:
        """强制重新加载配置"""
        self._cache = None
        self._load()
```

**验收标准**：
- [ ] `ConfigManager` 单例工作正常
- [ ] `AppConfig` 所有字段有默认值
- [ ] `_load()` 从 SystemSettings 表正确读取
- [ ] `set()` 写入数据库并刷新缓存

**git commit**：`feat: 新增统一配置系统 ConfigManager`

### 1.2 迁移所有配置读取点

**修改文件清单**：

| 文件 | 当前读取方式 | 修改为 |
|------|-------------|--------|
| `api/routers/settings.py` | 直接查询 SystemSettings | 使用 `ConfigManager` |
| `api/routers/tasks.py` | `_get_global_setting_bool()` | 使用 `ConfigManager` |
| `douyin/core/config_mgr.py` | `config.yaml` | 委托给 `ConfigManager`（兼容层） |
| `bilibili/core/downloader.py` | `douyin.core.config_mgr` | 使用 `ConfigManager` |
| `pipeline/config.py` | `douyin.core.config_mgr` | 使用 `ConfigManager` |
| `pipeline/orchestrator_v2.py` | `douyin.core.config_mgr` | 使用 `ConfigManager` |
| `db/core.py` | `common.paths` | 使用 `ConfigManager` |

**验收标准**：
- [ ] `grep -r "from media_tools.douyin.core.config_mgr import" src/media_tools/api/` 无结果
- [ ] `grep -r "from media_tools.common.paths import" src/media_tools/` 无结果（除保留文件外）
- [ ] `grep -r "SystemSettings" src/media_tools/api/routers/` 仅限 settings.py
- [ ] 所有测试通过
- [ ] 前端设置页面修改后，后端 worker 能读取到新值

**git commit**：`refactor: 迁移所有配置读取到 ConfigManager`

### 1.3 删除废弃配置源

- [ ] 删除 `src/media_tools/common/paths.py`
- [ ] 删除 `config/config.yaml`（或保留为空文件做兼容）
- [ ] `douyin/core/config_mgr.py` 精简为仅保留 Cookie 相关方法

**验收标准**：
- [ ] `pytest tests/ -q` 全部通过
- [ ] `./run.sh backend` 正常启动
- [ ] 前端设置页面修改保存后刷新页面，设置仍然生效

**git commit**：`chore: 删除废弃的配置源文件`

---

## 阶段 2：后端分层（4-5 天）

**目标**：API / Service / Repository 三层分离。

### 2.1 Repository 层

**新增目录 `src/media_tools/repositories/`**：

```
repositories/
├── __init__.py
├── base.py           # 基类，CRUD 通用逻辑
├── task_repository.py
├── creator_repository.py
├── asset_repository.py
└── settings_repository.py
```

**base.py**：
```python
from abc import ABC
from typing import Generic, TypeVar
from media_tools.db.core import get_db_connection

T = TypeVar("T")

class BaseRepository(Generic[T], ABC):
    table_name: str

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with get_db_connection() as conn:
            return conn.execute(sql, params)
```

**验收标准**：
- [ ] 所有 Repository 继承 BaseRepository
- [ ] 所有 SQL 查询通过 Repository（router 中无裸 SQL）
- [ ] Repository 有单元测试覆盖

**git commit**：`feat: 新增 Repository 数据访问层`

### 2.2 Service 层

**新增目录 `src/media_tools/services/`**：

```
services/
├── __init__.py
├── task_service.py         # 任务管理
├── creator_service.py      # 创作者管理
├── asset_service.py        # 媒体资产管理
├── download_service.py     # 下载调度
├── transcribe_service.py   # 转写调度
└── settings_service.py     # 设置管理
```

**task_service.py** 核心接口：
```python
class TaskService:
    def __init__(self, repo: TaskRepository, event_bus: EventBus):
        self.repo = repo
        self.event_bus = event_bus

    async def create_creator_sync_task(self, uid: str, mode: str) -> str:
        """创建任务，返回 task_id"""
        pass

    async def update_progress(self, task_id: str, progress: TaskProgress) -> None:
        """更新进度，自动广播 WebSocket"""
        pass

    async def mark_completed(self, task_id: str, result: TaskResult) -> None:
        """标记完成，写入结果摘要"""
        pass

    async def mark_failed(self, task_id: str, error: str) -> None:
        """标记失败"""
        pass
```

**验收标准**：
- [ ] Service 层无 FastAPI / WebSocket 引用
- [ ] Service 可独立单元测试（mock Repository）
- [ ] 所有测试通过

**git commit**：`feat: 新增 Service 业务逻辑层`

### 2.3 拆分 Workers

**新增目录 `src/media_tools/workers/`**：

```
workers/
├── __init__.py
├── base.py              # Worker 基类（取消检测、心跳）
├── creator_sync.py      # 创作者同步 Worker
├── full_sync.py         # 全量同步 Worker
├── pipeline.py          # Pipeline Worker
├── download.py          # 下载 Worker
└── transcribe.py        # 转写 Worker
```

**从 `tasks.py` 迁移内容**：
- `_background_creator_download_worker` → `workers/creator_sync.py`
- `_background_full_sync_worker` → `workers/full_sync.py`
- `_background_pipeline_worker` → `workers/pipeline.py`
- `_background_batch_worker` → `workers/pipeline.py`
- `_background_download_worker` → `workers/download.py`
- `_background_local_transcribe_worker` → `workers/transcribe.py`
- `_transcribe_files` → `workers/transcribe.py`

**base.py**：
```python
class BaseWorker:
    """Worker 基类 - 提供通用功能"""

    def __init__(self, task_id: str, task_service: TaskService):
        self.task_id = task_id
        self.task_service = task_service
        self._cancelled = False

    def is_cancelled(self) -> bool:
        return self._cancelled or get_cancel_event(self.task_id) is not None

    async def report_progress(self, progress: float, message: str) -> None:
        await self.task_service.update_progress(self.task_id, TaskProgress(
            percent=progress, message=message
        ))

    async def heartbeat(self) -> None:
        """定期心跳，防止任务被标记为过期"""
        while not self._cancelled:
            await asyncio.sleep(30)
            await self.task_service.heartbeat(self.task_id)
```

**验收标准**：
- [ ] `tasks.py` 从 1735 行 → <400 行
- [ ] 所有 Worker 继承 BaseWorker
- [ ] Worker 通过 Service 层操作，不直接操作数据库
- [ ] 取消/暂停/恢复功能正常工作
- [ ] 所有测试通过

**git commit**：`refactor: 拆分后台 Worker 到独立模块`

### 2.4 精简 API Router

**重构 `api/routers/tasks.py`**：

```python
"""Tasks API Router - 只处理 HTTP/WebSocket，不含业务逻辑"""
from fastapi import APIRouter
from media_tools.services.task_service import TaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
task_service = TaskService(...)  # 依赖注入

@router.post("/download/creator")
async def trigger_creator_download(req: CreatorDownloadRequest):
    task_id = await task_service.create_creator_sync_task(req.uid, req.mode)
    return {"task_id": task_id, "status": "started"}
```

**验收标准**：
- [ ] Router 中无业务逻辑代码
- [ ] Router 中无裸 SQL
- [ ] Router 只负责：解析请求 → 调用 Service → 返回响应
- [ ] 所有测试通过

**git commit**：`refactor: 精简 API Router，业务逻辑委托给 Service`

---

## 阶段 3：任务状态机重构（3-4 天）

**目标**：清晰的状态机、事件驱动架构。

### 3.1 定义任务状态机

**新增 `src/media_tools/core/workflow.py`**：

```python
from enum import Enum, auto
from dataclasses import dataclass
from typing import Protocol

class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

class TaskStage(Enum):
    INITIALIZING = "initializing"
    FETCHING_METADATA = "fetching_metadata"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"

VALID_TRANSITIONS: dict[TaskStatus, list[TaskStatus]] = {
    TaskStatus.PENDING: [TaskStatus.RUNNING, TaskStatus.CANCELLED],
    TaskStatus.RUNNING: [TaskStatus.PAUSED, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED],
    TaskStatus.PAUSED: [TaskStatus.RUNNING, TaskStatus.CANCELLED],
    TaskStatus.COMPLETED: [],
    TaskStatus.FAILED: [TaskStatus.RUNNING],
    TaskStatus.CANCELLED: [TaskStatus.RUNNING],
}

class InvalidTransitionError(ValueError):
    pass

def validate_transition(from_status: TaskStatus, to_status: TaskStatus) -> None:
    if to_status not in VALID_TRANSITIONS.get(from_status, []):
        raise InvalidTransitionError(
            f"Invalid transition: {from_status.name} -> {to_status.name}"
        )

@dataclass
class Subtask:
    id: str
    title: str
    status: TaskStatus
    error: str | None = None

@dataclass
class TaskResult:
    success_count: int
    failed_count: int
    skipped_count: int
    total_count: int
    subtasks: list[Subtask]
```

**验收标准**：
- [ ] 所有状态转移都有验证
- [ ] 非法转移抛出 `InvalidTransitionError`
- [ ] 单元测试覆盖所有状态转移路径

**git commit**：`feat: 定义任务状态机和阶段枚举`

### 3.2 事件总线

**新增 `src/media_tools/core/events.py`**：

```python
from abc import ABC
from dataclasses import dataclass
from typing import Callable, Awaitable
import asyncio

@dataclass
class Event(ABC):
    task_id: str
    timestamp: float

@dataclass
class TaskProgressEvent(Event):
    stage: str
    percent: float
    message: str
    result_summary: dict | None = None
    subtasks: list[dict] | None = None

@dataclass
class TaskCompletedEvent(Event):
    result: TaskResult

class EventBus:
    def __init__(self):
        self._handlers: dict[type, list] = {}

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: Event) -> None:
        for handler in self._handlers.get(type(event), []):
            asyncio.create_task(handler(event))
```

**验收标准**：
- [ ] 事件总线支持多订阅者
- [ ] 发布事件时所有订阅者都被调用
- [ ] 异常不传播到其他订阅者

**git commit**：`feat: 新增事件总线 EventBus`

### 3.3 重写核心工作流

**修改 `workers/creator_sync.py`**：

```python
async def run_creator_sync_workflow(
    task_id: str,
    uid: str,
    mode: str,
    task_service: TaskService,
    event_bus: EventBus,
    config: AppConfig,
):
    worker = CreatorSyncWorker(task_id, task_service, event_bus, config)
    await worker.run(uid, mode)

class CreatorSyncWorker(BaseWorker):
    async def run(self, uid: str, mode: str) -> None:
        # 阶段 1: 初始化
        await self.set_stage(TaskStage.INITIALIZING)
        creator = await self._fetch_creator_info(uid)

        # 阶段 2: 下载
        await self.set_stage(TaskStage.DOWNLOADING)
        downloaded = await self._download_videos(creator, mode)

        if not downloaded:
            await self.complete(success=0, failed=0, total=0)
            return

        if not self.config.auto_transcribe:
            await self.complete(success=len(downloaded), failed=0, total=len(downloaded))
            return

        # 阶段 3: 转写
        await self.set_stage(TaskStage.TRANSCRIBING)
        success, failed = await self._transcribe_videos(downloaded)

        await self.complete(success=success, failed=failed, total=len(downloaded))

    async def set_stage(self, stage: TaskStage) -> None:
        await self.report_progress(
            self._get_progress_for_stage(stage),
            f"当前阶段: {stage.value}"
        )

    def _get_progress_for_stage(self, stage: TaskStage) -> float:
        return {
            TaskStage.INITIALIZING: 0.05,
            TaskStage.DOWNLOADING: 0.1,
            TaskStage.TRANSCRIBING: 0.6,
            TaskStage.FINALIZING: 0.95,
        }.get(stage, 0.0)
```

**验收标准**：
- [ ] 工作流有清晰的阶段划分
- [ ] 每个阶段进度正确
- [ ] 阶段信息通过 WebSocket 发送到前端
- [ ] 前端能正确显示当前阶段

**git commit**：`refactor: 重写创作者同步工作流，使用清晰阶段划分`

---

## 阶段 4：前端重构（5-6 天）

**目标**：组件拆分、Store 拆分、添加测试。

### 4.1 拆分 Zustand Store

**新建文件**：

```
store/
├── useCreatorsStore.ts    # 创作者状态（独立）
├── useTasksStore.ts       # 任务状态（独立）
├── useSettingsStore.ts    # 设置状态（独立）
├── useWebSocketStore.ts   # WebSocket 连接（独立）
└── useAppStore.ts         # 组合 store（可选）
```

**useTasksStore.ts**：
```typescript
import { create } from 'zustand';
import { taskService } from '@/services/tasks';
import type { Task } from '@/types/task';

interface TasksState {
  tasks: Task[];
  activeTaskId: string | null;
  updateTask: (update: Partial<Task> & { task_id: string }) => void;
  addTask: (task: Task) => void;
  removeTask: (taskId: string) => void;
}

export const useTasksStore = create<TasksState>((set, get) => ({
  tasks: [],
  activeTaskId: null,

  updateTask: (update) => {
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.task_id === update.task_id ? { ...t, ...update } : t
      ),
    }));
  },

  addTask: (task) => {
    set((state) => ({
      tasks: [task, ...state.tasks],
    }));
  },

  removeTask: (taskId) => {
    set((state) => ({
      tasks: state.tasks.filter((t) => t.task_id !== taskId),
    }));
  },
}));
```

**验收标准**：
- [ ] 每个 Store 职责单一
- [ ] Store 之间无循环依赖
- [ ] Store 可独立测试

**git commit**：`refactor: 拆分 Zustand Store 为独立模块`

### 4.2 新建服务层

**新建 `services/` 目录**：

```
services/
├── creators.ts    # 创作者 API 封装
├── assets.ts      # 资产 API 封装
├── tasks.ts       # 任务 API 封装
├── settings.ts    # 设置 API 封装
└── websocket.ts   # WebSocket 封装
```

**services/tasks.ts**：
```typescript
import { apiClient } from '@/lib/api';
import type { Task } from '@/types/task';

export const taskService = {
  async getHistory(): Promise<Task[]> {
    const { data } = await apiClient.get('/tasks/');
    return data;
  },

  async triggerCreatorDownload(uid: string, mode: string): Promise<string> {
    const { data } = await apiClient.post('/tasks/download/creator', { uid, mode });
    return data.task_id;
  },

  async pause(taskId: string): Promise<void> {
    await apiClient.post(`/tasks/${taskId}/pause`);
  },

  async resume(taskId: string): Promise<void> {
    await apiClient.post(`/tasks/${taskId}/resume`);
  },

  async rerun(taskId: string): Promise<void> {
    await apiClient.post(`/tasks/${taskId}/rerun`);
  },

  async delete(taskId: string): Promise<void> {
    await apiClient.delete(`/tasks/${taskId}`);
  },
};
```

**验收标准**：
- [ ] 所有 API 调用通过 service 层
- [ ] Service 层有错误处理
- [ ] Service 层可独立测试

**git commit**：`feat: 新增前端服务层`

### 4.3 拆分巨型组件

**TaskMonitorPanel 拆分**：

```
components/layout/TaskMonitorPanel/
├── index.tsx              # 主容器（~80 行）
├── TaskStats.tsx          # 统计卡片
├── TaskFilterTabs.tsx     # 过滤器标签
├── TaskList.tsx           # 任务列表
├── TaskItem.tsx           # 单个任务
│   ├── index.tsx
│   ├── TaskProgress.tsx   # 进度条
│   ├── TaskActions.tsx    # 操作按钮
│   └── SubtaskList.tsx    # 子任务展开
└── hooks/
    └── useTaskActions.ts  # 任务操作逻辑
```

**Settings 页面拆分**：

```
pages/Settings/
├── index.tsx              # 主容器
├── QwenSection.tsx        # Qwen 账户
├── DouyinSection.tsx      # 抖音账户
├── BilibiliSection.tsx    # B站账户
├── GlobalSettings.tsx     # 全局设置
└── ScheduledTasks.tsx     # 定时任务
```

**验收标准**：
- [ ] 每个组件 <200 行
- [ ] 组件职责单一
- [ ] 组件可独立测试
- [ ] regression 测试 `test_page_components_not_too_large` 通过

**git commit**：`refactor: 拆分巨型组件为独立子组件`

### 4.4 添加前端测试

**安装依赖**：
```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

**新建 `vitest.config.ts`**：
```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
```

**新建测试文件**：

```
tests/
├── unit/
│   ├── services/
│   │   └── tasks.test.ts
│   ├── store/
│   │   └── useTasksStore.test.ts
│   └── components/
│       └── TaskMonitorPanel.test.tsx
└── e2e/
    └── workflow.spec.ts
```

**验收标准**：
- [ ] `npm test` 命令可用
- [ ] 至少 10 个前端单元测试通过
- [ ] 至少 2 个 E2E 测试通过

**git commit**：`test: 添加前端测试框架和首批测试`

---

## 阶段 5：错误处理与可观测性（3 天）

### 5.1 统一异常体系

**新增 `src/media_tools/core/exceptions.py`**：

```python
class AppError(Exception):
    """应用异常基类"""
    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

class ConfigurationError(AppError):
    def __init__(self, message: str, **kwargs):
        super().__init__("CONFIG_ERROR", message, kwargs)

class DownloadError(AppError):
    def __init__(self, message: str, url: str | None = None, **kwargs):
        super().__init__("DOWNLOAD_ERROR", message, {"url": url, **kwargs})

class TranscribeError(AppError):
    def __init__(self, message: str, file_path: str | None = None, **kwargs):
        super().__init__("TRANSCRIBE_ERROR", message, {"file_path": file_path, **kwargs})

class TaskCancelledError(AppError):
    def __init__(self, task_id: str):
        super().__init__("TASK_CANCELLED", f"Task {task_id} was cancelled", {"task_id": task_id})
```

**验收标准**：
- [ ] 所有业务异常继承 AppError
- [ ] 异常包含结构化信息（code, message, details）
- [ ] 无 `except Exception:` 裸捕获（或极少且记录日志）

**git commit**：`feat: 统一异常体系`

### 5.2 结构化日志

**重构 `src/media_tools/logger.py`**：

```python
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s %(task_id)s %(stage)s %(duration_ms)d"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

class TaskLogAdapter:
    """为任务添加上下文信息"""
    def __init__(self, logger: logging.Logger, task_id: str):
        self.logger = logger
        self.task_id = task_id

    def info(self, msg: str, **kwargs):
        self.logger.info(msg, extra={"task_id": self.task_id, **kwargs})

    def error(self, msg: str, **kwargs):
        self.logger.error(msg, extra={"task_id": self.task_id, **kwargs})
```

**验收标准**：
- [ ] 所有日志包含 task_id
- [ ] 异常信息包含完整上下文
- [ ] 日志可搜索、可过滤

**git commit**：`feat: 结构化日志，添加任务上下文`

### 5.3 API 错误处理中间件

**修改 `api/app.py`**：

```python
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=400,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        }
    )

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", extra={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "服务器内部错误"}
    )
```

**验收标准**：
- [ ] AppError 返回 400 + 结构化错误信息
- [ ] 未知异常返回 500 + 通用错误信息（不暴露内部细节）
- [ ] 前端能正确显示错误信息

**git commit**：`feat: API 统一错误处理中间件`

---

## 阶段 6：收尾与验证（2-3 天）

### 6.1 性能优化

- [ ] 数据库索引检查：`media_assets.creator_uid`, `task_queue.status`, `task_queue.update_time`
- [ ] WebSocket 去重：相同状态不重复发送
- [ ] 前端虚拟化：大列表使用 React Virtuoso

### 6.2 清理和删除

- [ ] 删除所有未使用的导入
- [ ] 删除 `common/paths.py`（已在阶段 1 删除）
- [ ] 删除 `douyin/core/ui.py`（若未使用）
- [ ] 删除 `douyin/core/env_check.py`（若未使用）

### 6.3 代码检查工具

**新增 `pyproject.toml` 配置**：

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
ignore = ["E501"]
```

**验收标准**：
- [ ] `mypy src/media_tools` 0 错误
- [ ] `ruff check src/media_tools` 0 错误
- [ ] `npx tsc --noEmit` 0 错误

### 6.4 文档

**新增 `ARCHITECTURE.md`**：
- 架构图（文字版）
- 模块职责说明
- 数据流说明
- 配置说明

**新增 `DEVELOPMENT.md`**：
- 开发环境搭建
- 测试命令
- 代码规范
- 提交规范

### 6.5 最终验证

**验收 checklist**：
- [ ] `pytest tests/ -q` 全部通过（包括回归测试）
- [ ] `pytest tests/integration/ -v` 全部通过
- [ ] `mypy src/media_tools` 0 错误
- [ ] `ruff check src/media_tools` 0 错误
- [ ] `npx tsc --noEmit` 0 错误
- [ ] `./run.sh` 前后端正常启动
- [ ] 手动验证：创作者同步 → 下载 → 转写 完整流程
- [ ] 手动验证：任务中心显示正确（阶段、统计、子任务）
- [ ] 手动验证：设置页面修改后生效

**最终 git commit**：`chore: 重构完成，清理和最终验证`

---

## Git 提交策略

### 分支策略

```
main (稳定分支)
  └── refactor/phase-0-baseline
        └── refactor/phase-1-config
              └── refactor/phase-2-backend-layers
                    └── refactor/phase-3-workflow
                          └── refactor/phase-4-frontend
                                └── refactor/phase-5-observability
                                      └── refactor/phase-6-final
```

每完成一个阶段：
1. 在当前分支验收测试
2. `git merge --no-ff` 到下一阶段分支
3. 必要时 rebase 到 main

### Commit Message 规范

```
类型: 描述

- feat: 新功能
- fix: 修复
- refactor: 重构
- test: 测试
- chore: 杂项
- docs: 文档

示例：
feat: 新增统一配置系统 ConfigManager
refactor: 拆分后台 Worker 到独立模块
test: 添加前端测试框架
```

---

## 风险与回滚策略

| 风险 | 回滚方案 |
|------|----------|
| 重构导致功能损坏 | 每个阶段独立分支，可单独 revert |
| 数据库 schema 变更 | 只增不改，旧代码兼容新 schema |
| 配置迁移失败 | 保留 config.yaml 做 fallback |
| 测试覆盖率不足 | 每阶段强制要求集成测试通过 |
| 时间超出预期 | 优先完成 Phase 1+2+6，其余可延后 |

---

## 工作量估算

| 阶段 | 天数 | 主要工作 |
|------|------|----------|
| 0 | 1-2 | 修复回归测试、添加集成测试 |
| 1 | 2-3 | 统一配置系统 |
| 2 | 4-5 | 后端分层（Repository + Service + Workers）|
| 3 | 3-4 | 任务状态机 + 事件驱动 |
| 4 | 5-6 | 前端重构（Store 拆分、组件拆分、测试）|
| 5 | 3 | 错误处理 + 可观测性 |
| 6 | 2-3 | 收尾验证 |
| **总计** | **20-26** | **约 4-5 周** |

---

## 开始之前

1. **备份当前代码**：`git branch backup-before-refactor`
2. **确认基线稳定**：`pytest tests/ -q` 全部通过
3. **创建重构分支**：`git checkout -b refactor/main`
