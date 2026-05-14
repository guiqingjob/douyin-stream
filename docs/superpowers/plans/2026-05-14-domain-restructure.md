# Domain Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 media-tools 按业务能力重新组织为 platform/download/transcribe/assets/scheduler/api/store/core 模块，统一配置/日志/数据库管理。

**Architecture:** 按"能力"而非"技术层次"拆分模块，消除 services/workers/pipeline/repositories 大杂烩。严格分层依赖：api→scheduler→业务→platform/store。

**Tech Stack:** Python 3.11+, FastAPI, SQLite, asyncio

---

## File Structure (Target)

```
src/media_tools/
├── __init__.py
├── platform/              # 平台交互
│   ├── __init__.py
│   ├── base.py
│   ├── douyin.py          # 合并原 douyin/ 下载+认证+辅助逻辑
│   └── bilibili.py        # 合并原 bilibili/ 下载逻辑
├── download/              # 下载能力
│   ├── __init__.py
│   ├── service.py         # 原 pipeline/download_router.py 调度逻辑
│   └── worker.py          # DownloadWorker
├── transcribe/            # 转写能力（吞并 pipeline/ 核心）
│   ├── __init__.py
│   ├── service.py         # 原 pipeline/orchestrator.py 核心
│   ├── worker.py          # 合并 CreatorTranscribeWorker, LocalTranscribeWorker
│   ├── flow.py            # 原 transcribe/flow.py
│   ├── accounts.py        # 账号池（原 services/account_pool_service.py + transcribe/accounts.py）
│   ├── runs.py            # 转写运行记录（原 services/transcribe_run_service.py）
│   ├── quota.py           # 原 transcribe/quota.py
│   ├── error_types.py     # 原 pipeline/error_types.py
│   ├── models.py          # 合并 pipeline/models.py + transcribe 模型
│   ├── config.py          # 合并 pipeline/config.py + transcribe/config.py
│   ├── helpers.py         # 原 pipeline/helpers.py
│   ├── preview.py         # 原 pipeline/preview.py
│   ├── preview_backfill.py # 原 pipeline/preview_backfill.py
│   ├── http.py            # 原 transcribe/http.py
│   ├── oss_sign.py        # 原 transcribe/oss_sign.py
│   ├── oss_upload.py      # 原 transcribe/oss_upload.py
│   ├── export_utils.py    # 原 transcribe/export_utils.py
│   ├── runtime.py         # 原 transcribe/runtime.py
│   ├── result_metadata.py # 原 transcribe/result_metadata.py
│   ├── error_classifier.py # 原 transcribe/error_classifier.py
│   └── errors.py          # 原 transcribe/errors.py
├── assets/                # 资源管理
│   ├── __init__.py
│   ├── service.py         # 合并 media_asset_service + asset_update_service
│   ├── repository.py      # 原 repositories/asset_repository.py
│   ├── file_ops.py        # 原 services/asset_file_ops.py
│   ├── gc.py              # 合并 asset_gc + cloud_cleanup_service
│   ├── local.py           # 原 services/local_asset_service.py
│   └── reconciler.py      # 原 services/transcript_reconciler.py
├── scheduler/             # 任务调度（吞并 workers/ 骨架 + services/ 任务管理）
│   ├── __init__.py
│   ├── base.py            # 原 workers/base.py（Worker 基类）
│   ├── registry.py        # Worker 注册表（从 base.py 分离）
│   ├── dispatcher.py      # 原 workers/task_dispatcher.py
│   ├── queue.py           # 任务队列操作（从 task_ops.py 抽取）
│   ├── ops.py             # 原 services/task_ops.py 核心
│   ├── state.py           # 原 services/task_state.py
│   ├── retry.py           # 原 services/auto_retry.py
│   ├── progress.py        # 原 services/pipeline_progress.py
│   ├── health.py          # 原 services/health_check_service.py
│   └── cleanup.py         # 原 services/cleanup.py 任务相关部分
├── creators/              # 创作者管理
│   ├── __init__.py
│   ├── service.py         # 创作者业务逻辑
│   ├── repository.py      # 原 repositories/creator_repository.py
│   └── sync.py            # 原 workers/creator_sync.py 业务逻辑
├── accounts/              # 账号管理（独立域）
│   ├── __init__.py
│   ├── service.py         # 原 services/account_pool_service.py
│   ├── repository.py      # 原 repositories/account_repository.py
│   └── status.py          # 原 services/qwen_status.py
├── api/                   # HTTP 入口
│   ├── __init__.py
│   ├── app.py
│   ├── schemas.py
│   └── routers/
│       ├── __init__.py
│       ├── assets.py
│       ├── creators.py
│       ├── download.py    # 合并原 douyin.py + bilibili.py 下载路由
│       ├── metrics.py
│       ├── scheduler.py   # 原 tasks.py 重命名
│       ├── search.py
│       ├── settings.py
│       └── transcribe.py  # 新增/从原有路由提取
├── store/                 # 数据存储
│   ├── __init__.py
│   ├── db.py              # 简化版数据库连接（原 db/core.py 精简）
│   ├── models.py          # Pydantic/dataclass 模型 + 状态枚举
│   ├── fts.py             # 原 db/fts.py
│   ├── path_utils.py      # 原 db/path_utils.py
│   ├── schema/            # 表定义（替代 init_db 大函数）
│   │   ├── __init__.py
│   │   ├── creators.py
│   │   ├── assets.py
│   │   ├── tasks.py
│   │   ├── auth.py
│   │   ├── accounts.py
│   │   ├── settings.py
│   │   ├── scheduled.py
│   │   ├── video_meta.py
│   │   ├── user_info.py
│   │   └── transcribe.py
│   └── migrations/        # 迁移脚本（替代 _ensure_column）
│       ├── __init__.py
│       ├── runner.py
│       └── 001_init.py
└── core/                  # 核心基础设施
    ├── __init__.py
    ├── config.py
    ├── exceptions.py
    ├── events.py
    ├── logging_context.py
    ├── cookie_manager.py
    ├── background.py
    ├── task_progress.py
    ├── workflow.py
    └── secure_storage.py
```

---

## Phase 1: Store 基础设施（原 db/ 重组）

### Task 1: 创建 store/ 目录结构

**Files:**
- Create: `src/media_tools/store/__init__.py`
- Create: `src/media_tools/store/schema/__init__.py`
- Create: `src/media_tools/store/migrations/__init__.py`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p src/media_tools/store/schema
mkdir -p src/media_tools/store/migrations
```

- [ ] **Step 2: 创建 `__init__.py` 文件**

```python
# src/media_tools/store/__init__.py
from .db import get_db, get_db_connection
from .path_utils import resolve_safe_path, resolve_query_value, local_asset_id
```

```python
# src/media_tools/store/schema/__init__.py
from .creators import create_table as create_creators_table
from .assets import create_table as create_assets_table
from .tasks import create_table as create_tasks_table
from .auth import create_table as create_auth_table
from .accounts import create_table as create_accounts_table
from .settings import create_table as create_settings_table
from .scheduled import create_table as create_scheduled_table
from .video_meta import create_table as create_video_meta_table
from .user_info import create_table as create_user_info_table
from .transcribe import create_table as create_transcribe_table

def init_schema(conn):
    create_creators_table(conn)
    create_assets_table(conn)
    create_tasks_table(conn)
    create_auth_table(conn)
    create_accounts_table(conn)
    create_settings_table(conn)
    create_scheduled_table(conn)
    create_video_meta_table(conn)
    create_user_info_table(conn)
    create_transcribe_table(conn)
```

```python
# src/media_tools/store/migrations/__init__.py
from .runner import run_migrations
```

- [ ] **Step 3: Commit**

```bash
git add src/media_tools/store/
git commit -m "chore(store): create directory structure for store layer"
```

### Task 2: 迁移 db/core.py → store/db.py（简化版）

**Files:**
- Create: `src/media_tools/store/db.py`
- Delete: `src/media_tools/db/core.py` (later, after all imports updated)

- [ ] **Step 1: 创建简化版 db.py**

```python
# src/media_tools/store/db.py
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from media_tools.logger import get_logger

logger = get_logger('db')

_db_path: Optional[str] = None


def get_db_path() -> str:
    global _db_path
    if _db_path is None:
        project_root = Path(__file__).resolve().parents[2]
        default = project_root / "data" / "media_tools.db"
        default.parent.mkdir(parents=True, exist_ok=True)
        _db_path = str(default)
    return _db_path


def set_db_path(path: str) -> None:
    global _db_path
    _db_path = path


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency – yields a connection with explicit transaction."""
    conn = sqlite3.connect(get_db_path(), timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    conn.execute("BEGIN")
    try:
        yield conn
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


_thread_local = threading.local()


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection (thread-local cached)."""
    cached = getattr(_thread_local, "conn", None)
    if cached is not None:
        try:
            cached.execute("SELECT 1")
            return cached
        except sqlite3.Error:
            try:
                cached.close()
            except Exception:
                pass
            _thread_local.conn = None

    conn = sqlite3.connect(get_db_path(), timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    _thread_local.conn = conn
    return conn


def close_db_connection() -> None:
    cached = getattr(_thread_local, "conn", None)
    if cached is not None:
        try:
            cached.close()
        except sqlite3.Error:
            pass
        _thread_local.conn = None
```

- [ ] **Step 2: 迁移 db/fts.py → store/fts.py**

```bash
git mv src/media_tools/db/fts.py src/media_tools/store/fts.py
```

- [ ] **Step 3: 迁移 db/path_utils.py → store/path_utils.py**

```bash
git mv src/media_tools/db/path_utils.py src/media_tools/store/path_utils.py
```

- [ ] **Step 4: Commit**

```bash
git add src/media_tools/store/db.py src/media_tools/store/fts.py src/media_tools/store/path_utils.py
git rm src/media_tools/db/fts.py src/media_tools/db/path_utils.py
git commit -m "refactor(store): migrate db layer to store/ with simplified connection management"
```

### Task 3: 创建 schema/ 表定义文件

**Files:**
- Create: `src/media_tools/store/schema/*.py` (10 files)

- [ ] **Step 1: 从 db/core.py 提取每张表的 CREATE TABLE 到独立文件**

以 assets.py 为例：

```python
# src/media_tools/store/schema/assets.py
import sqlite3


def create_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS media_assets (
        asset_id TEXT PRIMARY KEY,
        creator_uid TEXT,
        source_url TEXT,
        title TEXT,
        duration INTEGER,
        video_path TEXT,
        video_status TEXT DEFAULT 'pending',
        transcript_path TEXT,
        transcript_status TEXT DEFAULT 'none',
        create_time DATETIME,
        update_time DATETIME
    )
    """)


def create_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_assets_creator ON media_assets(creator_uid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_assets_video_status ON media_assets(video_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_assets_transcript_status ON media_assets(transcript_status)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_media_assets_creator_status "
        "ON media_assets(creator_uid, video_status, transcript_status)"
    )
```

其余 9 张表（creators, tasks, auth, accounts, settings, scheduled, video_meta, user_info, transcribe）同理提取。

- [ ] **Step 2: Commit**

```bash
git add src/media_tools/store/schema/
git commit -m "refactor(store): extract table definitions into schema/ modules"
```

### Task 4: 创建 migrations/ 框架和初始迁移

**Files:**
- Create: `src/media_tools/store/migrations/runner.py`
- Create: `src/media_tools/store/migrations/001_init.py`

- [ ] **Step 1: 创建迁移运行器**

```python
# src/media_tools/store/migrations/runner.py
import sqlite3
import logging

logger = logging.getLogger(__name__)


def ensure_version_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)


def get_current_version(conn: sqlite3.Connection) -> int:
    ensure_version_table(conn)
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return row[0] or 0


def run_migrations(conn: sqlite3.Connection) -> None:
    from . import 001_init

    current = get_current_version(conn)
    migrations = [
        (1, 001_init),
    ]

    for version, module in migrations:
        if version > current:
            logger.info(f"Applying migration {version}")
            module.apply(conn)
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
            conn.commit()
```

- [ ] **Step 2: 创建初始迁移（合并所有 _ensure_column 调用）**

```python
# src/media_tools/store/migrations/001_init.py
import sqlite3

version = 1


def apply(conn: sqlite3.Connection) -> None:
    """Apply all schema changes that were previously handled by _ensure_column."""
    # task_queue columns
    conn.execute("ALTER TABLE task_queue ADD COLUMN update_time DATETIME")
    conn.execute("ALTER TABLE task_queue ADD COLUMN cancel_requested INTEGER DEFAULT 0")
    conn.execute("ALTER TABLE task_queue ADD COLUMN auto_retry INTEGER DEFAULT 0")

    # creators columns
    conn.execute("ALTER TABLE creators ADD COLUMN platform TEXT DEFAULT 'douyin'")
    conn.execute("ALTER TABLE creators ADD COLUMN sync_status TEXT DEFAULT 'active'")
    conn.execute("ALTER TABLE creators ADD COLUMN last_fetch_time DATETIME")
    conn.execute("ALTER TABLE creators ADD COLUMN auto_sync BOOLEAN DEFAULT 0")
    conn.execute("ALTER TABLE creators ADD COLUMN avatar TEXT")
    conn.execute("ALTER TABLE creators ADD COLUMN bio TEXT")

    # Accounts_Pool columns
    conn.execute("ALTER TABLE Accounts_Pool ADD COLUMN remark TEXT DEFAULT ''")
    conn.execute("ALTER TABLE Accounts_Pool ADD COLUMN auth_state_path TEXT DEFAULT ''")

    # media_assets columns
    conn.execute("ALTER TABLE media_assets ADD COLUMN source_url TEXT")
    conn.execute("ALTER TABLE media_assets ADD COLUMN is_read BOOLEAN DEFAULT 0")
    conn.execute("ALTER TABLE media_assets ADD COLUMN is_starred BOOLEAN DEFAULT 0")
    conn.execute("ALTER TABLE media_assets ADD COLUMN folder_path TEXT DEFAULT ''")
    conn.execute("ALTER TABLE media_assets ADD COLUMN create_time DATETIME")
    conn.execute("ALTER TABLE media_assets ADD COLUMN update_time DATETIME")
    conn.execute("ALTER TABLE media_assets ADD COLUMN transcript_preview TEXT")
    conn.execute("ALTER TABLE media_assets ADD COLUMN transcript_text TEXT")
    conn.execute("ALTER TABLE media_assets ADD COLUMN transcript_last_error TEXT")
    conn.execute("ALTER TABLE media_assets ADD COLUMN transcript_error_type TEXT")
    conn.execute("ALTER TABLE media_assets ADD COLUMN transcript_retry_count INTEGER DEFAULT 0")
    conn.execute("ALTER TABLE media_assets ADD COLUMN transcript_failed_at DATETIME")
    conn.execute("ALTER TABLE media_assets ADD COLUMN last_task_id TEXT")
    conn.execute("ALTER TABLE media_assets ADD COLUMN source_platform TEXT")
```

- [ ] **Step 3: Commit**

```bash
git add src/media_tools/store/migrations/
git commit -m "feat(store): add migration framework replacing _ensure_column patches"
```

### Task 5: 创建 store/models.py 并迁移状态枚举

**Files:**
- Create: `src/media_tools/store/models.py`

- [ ] **Step 1: 创建模型文件，包含状态枚举**

```python
# src/media_tools/store/models.py
from enum import Enum


class VideoStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    FAILED = "failed"


class TranscriptStatus(str, Enum):
    NONE = "none"
    TRANSCRIBING = "transcribing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PARTIAL_FAILED = "PARTIAL_FAILED"


# Backward compatibility mappings
VIDEO_STATUS_MAP = {s.value: i for i, s in enumerate(VideoStatus)}
TRANSCRIPT_STATUS_MAP = {s.value: i for i, s in enumerate(TranscriptStatus)}
TASK_STATUS_MAP = {s.value: i for i, s in enumerate(TaskStatus)}
```

- [ ] **Step 2: Commit**

```bash
git add src/media_tools/store/models.py
git commit -m "feat(store): add models.py with status enums extracted from db/core"
```

### Task 6: 更新所有 import db.core → store.db

**Files:**
- Modify: 所有引用 `media_tools.db.core` 的文件

- [ ] **Step 1: 批量替换 import**

```bash
# Find all files importing from db.core
find src -name "*.py" -exec grep -l "from media_tools.db.core\|from media_tools.db import\|import media_tools.db" {} \;

# Replace patterns
find src -name "*.py" -exec sed -i '' 's/from media_tools\.db\.core import/from media_tools.store.db import/g' {} \;
find src -name "*.py" -exec sed -i '' 's/from media_tools\.db import/from media_tools.store.db import/g' {} \;
find src -name "*.py" -exec sed -i '' 's/import media_tools\.db/import media_tools.store.db/g' {} \;
```

- [ ] **Step 2: 验证替换没有遗漏**

```bash
grep -r "media_tools.db" src/ --include="*.py" | grep -v "store.db"
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor: update all imports from db.core to store.db"
```

### Task 7: Phase 1 验证

- [ ] **Step 1: 跑全部测试**

```bash
python -m pytest tests/ -x -q
```

- [ ] **Step 2: 手动启动服务验证**

```bash
cd src && python -m media_tools.api.app
```

---

## Phase 2: Services 拆分

### Task 8: 创建 scheduler/ 目录并迁移任务管理

**Files:**
- Create: `src/media_tools/scheduler/__init__.py`
- Create: `src/media_tools/scheduler/ops.py` (from services/task_ops.py)
- Create: `src/media_tools/scheduler/state.py` (from services/task_state.py)
- Create: `src/media_tools/scheduler/retry.py` (from services/auto_retry.py)
- Create: `src/media_tools/scheduler/progress.py` (from services/pipeline_progress.py)
- Create: `src/media_tools/scheduler/health.py` (from services/health_check_service.py)
- Create: `src/media_tools/scheduler/cleanup.py` (from services/cleanup.py task-related)
- Create: `src/media_tools/scheduler/queue.py` (new, extracted from task_ops.py)

- [ ] **Step 1: 创建目录**

```bash
mkdir -p src/media_tools/scheduler
```

- [ ] **Step 2: 迁移文件（用 git mv 保留历史）**

```bash
git mv src/media_tools/services/task_ops.py src/media_tools/scheduler/ops.py
git mv src/media_tools/services/task_state.py src/media_tools/scheduler/state.py
git mv src/media_tools/services/auto_retry.py src/media_tools/scheduler/retry.py
git mv src/media_tools/services/pipeline_progress.py src/media_tools/scheduler/progress.py
git mv src/media_tools/services/health_check_service.py src/media_tools/scheduler/health.py
```

- [ ] **Step 3: 更新 import 路径（scheduler 内部）**

```bash
find src/media_tools/scheduler -name "*.py" -exec sed -i '' 's/from media_tools\.services\./from media_tools.scheduler./g' {} \;
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(scheduler): migrate task management from services/ to scheduler/"
```

### Task 9: 创建 assets/ 目录并迁移资源管理

**Files:**
- Create: `src/media_tools/assets/__init__.py`
- Create: `src/media_tools/assets/service.py` (合并 media_asset_service + asset_update_service)
- Create: `src/media_tools/assets/repository.py` (from repositories/asset_repository.py)
- Create: `src/media_tools/assets/file_ops.py` (from services/asset_file_ops.py)
- Create: `src/media_tools/assets/gc.py` (合并 asset_gc + cloud_cleanup_service)
- Create: `src/media_tools/assets/local.py` (from services/local_asset_service.py)
- Create: `src/media_tools/assets/reconciler.py` (from services/transcript_reconciler.py)

- [ ] **Step 1: 迁移 repository**

```bash
git mv src/media_tools/repositories/asset_repository.py src/media_tools/assets/repository.py
```

- [ ] **Step 2: 迁移 services**

```bash
git mv src/media_tools/services/asset_file_ops.py src/media_tools/assets/file_ops.py
git mv src/media_tools/services/asset_gc.py src/media_tools/assets/gc.py
git mv src/media_tools/services/local_asset_service.py src/media_tools/assets/local.py
git mv src/media_tools/services/transcript_reconciler.py src/media_tools/assets/reconciler.py
```

- [ ] **Step 3: 创建合并后的 assets/service.py**

合并 `media_asset_service.py` 和 `asset_update_service.py` 的内容到一个文件。

- [ ] **Step 4: 删除旧的 services 文件**

```bash
git rm src/media_tools/services/media_asset_service.py
git rm src/media_tools/services/asset_update_service.py
git rm src/media_tools/services/cloud_cleanup_service.py
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(assets): migrate asset management to assets/ domain"
```

### Task 10: 创建 accounts/ 目录并迁移账号管理

**Files:**
- Create: `src/media_tools/accounts/__init__.py`
- Create: `src/media_tools/accounts/service.py` (from services/account_pool_service.py)
- Create: `src/media_tools/accounts/repository.py` (from repositories/account_repository.py)
- Create: `src/media_tools/accounts/status.py` (from services/qwen_status.py)

- [ ] **Step 1: 迁移文件**

```bash
git mv src/media_tools/repositories/account_repository.py src/media_tools/accounts/repository.py
git mv src/media_tools/services/account_pool_service.py src/media_tools/accounts/service.py
git mv src/media_tools/services/qwen_status.py src/media_tools/accounts/status.py
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "refactor(accounts): create accounts/ domain from account_pool_service"
```

### Task 11: Phase 2 验证

- [ ] **Step 1: 跑全部测试**

```bash
python -m pytest tests/ -x -q
```

---

## Phase 3: Workers 与 Pipeline 拆分

### Task 12: 迁移 Worker 基类和注册表到 scheduler/

**Files:**
- Create: `src/media_tools/scheduler/base.py` (from workers/base.py)
- Create: `src/media_tools/scheduler/registry.py` (new, extracted from base.py)
- Create: `src/media_tools/scheduler/dispatcher.py` (from workers/task_dispatcher.py)

- [ ] **Step 1: 拆分 base.py 为 base.py + registry.py**

将 `workers/base.py` 中的 `_WORKER_REGISTRY`、`register_worker`、`get_worker_class`、`list_worker_types` 提取到 `scheduler/registry.py`。

`scheduler/base.py` 保留 `BaseWorker` 类，但更新 import 从 `scheduler/ops.py` 和 `scheduler/state.py`。

- [ ] **Step 2: 迁移 dispatcher**

```bash
git mv src/media_tools/workers/task_dispatcher.py src/media_tools/scheduler/dispatcher.py
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor(scheduler): migrate worker infrastructure from workers/ to scheduler/"
```

### Task 13: 创建 download/ 域并迁移 DownloadWorker

**Files:**
- Create: `src/media_tools/download/__init__.py`
- Create: `src/media_tools/download/service.py` (from pipeline/download_router.py)
- Create: `src/media_tools/download/worker.py` (from workers/pipeline_worker.py DownloadWorker)

- [ ] **Step 1: 提取 DownloadWorker 到 download/worker.py**

从 `workers/pipeline_worker.py` 提取 `DownloadWorker` 类。

- [ ] **Step 2: 迁移下载调度逻辑**

从 `pipeline/download_router.py` 提取调度逻辑到 `download/service.py`。

- [ ] **Step 3: Commit**

```bash
git add src/media_tools/download/
git commit -m "feat(download): create download/ domain with service and worker"
```

### Task 14: 扩展 transcribe/ 域（吞并 pipeline/ 核心）

**Files:**
- Create: `src/media_tools/transcribe/service.py` (from pipeline/orchestrator.py)
- Modify: `src/media_tools/transcribe/worker.py` (合并多个 worker)

- [ ] **Step 1: 迁移 orchestrator**

```bash
git mv src/media_tools/pipeline/orchestrator.py src/media_tools/transcribe/service.py
```

- [ ] **Step 2: 合并转写 worker**

合并 `workers/creator_transcribe_worker.py`、`workers/local_transcribe_worker.py`、`workers/full_sync_worker.py` 到 `transcribe/worker.py`。

- [ ] **Step 3: 迁移 pipeline 辅助文件**

```bash
git mv src/media_tools/pipeline/models.py src/media_tools/transcribe/models.py
git mv src/media_tools/pipeline/error_types.py src/media_tools/transcribe/error_types.py
git mv src/media_tools/pipeline/helpers.py src/media_tools/transcribe/helpers.py
git mv src/media_tools/pipeline/config.py src/media_tools/transcribe/config.py
git mv src/media_tools/pipeline/preview.py src/media_tools/transcribe/preview.py
git mv src/media_tools/pipeline/preview_backfill.py src/media_tools/transcribe/preview_backfill.py
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(transcribe): absorb pipeline/ core into transcribe/ domain"
```

### Task 15: Phase 3 验证

- [ ] **Step 1: 跑全部测试**

```bash
python -m pytest tests/ -x -q
```

---

## Phase 4: 平台模块合并

### Task 16: 创建 platform/ 并合并 douyin/ bilibili/

**Files:**
- Create: `src/media_tools/platform/__init__.py`
- Create: `src/media_tools/platform/base.py`
- Create: `src/media_tools/platform/douyin.py`
- Create: `src/media_tools/platform/bilibili.py`

- [ ] **Step 1: 合并 douyin/ 核心逻辑到 platform/douyin.py**

合并 `douyin/core/downloader.py`、`douyin/core/f2_helper.py`、`douyin/core/auth_server.py` 等到一个文件。

- [ ] **Step 2: 合并 bilibili/ 核心逻辑到 platform/bilibili.py**

合并 `bilibili/core/downloader.py` 和 `bilibili/utils/*.py`。

- [ ] **Step 3: 删除旧目录**

```bash
git rm -rf src/media_tools/douyin/
git rm -rf src/media_tools/bilibili/
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(platform): merge douyin/ and bilibili/ into platform/ domain"
```

### Task 17: Phase 4 验证

- [ ] **Step 1: 跑全部测试**

```bash
python -m pytest tests/ -x -q
```

---

## Phase 5: API 路由整理

### Task 18: 重组 api/routers/

**Files:**
- Create: `src/media_tools/api/routers/download.py`
- Rename: `src/media_tools/api/routers/tasks.py` → `scheduler.py`
- Modify: `src/media_tools/api/app.py`

- [ ] **Step 1: 合并下载路由**

合并 `api/routers/douyin.py` 和 `api/routers/bilibili.py` 的下载相关路由到 `api/routers/download.py`。

- [ ] **Step 2: 重命名 tasks.py → scheduler.py**

```bash
git mv src/media_tools/api/routers/tasks.py src/media_tools/api/routers/scheduler.py
```

- [ ] **Step 3: 更新 app.py 的 router include**

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(api): reorganize routers, merge download routes"
```

### Task 19: Phase 5 验证

- [ ] **Step 1: 跑全部测试**

```bash
python -m pytest tests/ -x -q
```

- [ ] **Step 2: 手动启动验证**

```bash
cd src && python -m media_tools.api.app
```

---

## Phase 6: 配置/日志/测试/清理

### Task 20: 统一配置

- [ ] **Step 1: 删除源码目录内的配置**

```bash
rm -rf src/config/
rm -rf src/media_tools/config/
```

- [ ] **Step 2: 合并 active_preset.txt → config/presets.yaml**

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore(config): consolidate all config to config/ directory"
```

### Task 21: 统一日志

- [ ] **Step 1: 删除分散的日志目录**

```bash
rm -rf src/logs/
rm -rf src/media_tools/logs/
rm -rf frontend/logs/
rm -rf frontend/data/logs/
rm -rf data/logs/
```

- [ ] **Step 2: 清理 f2-trace 空文件**

```bash
find logs/ -name "f2-trace-*.log" -size 0 -delete
```

- [ ] **Step 3: 更新日志配置，统一输出到 logs/**

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(logs): consolidate all logs to logs/ directory, remove empty f2-trace files"
```

### Task 22: 重组测试目录

- [ ] **Step 1: 按新模块结构重组 tests/**

```bash
mkdir -p tests/platform tests/download tests/transcribe tests/assets tests/scheduler tests/store tests/creators tests/accounts
```

- [ ] **Step 2: 移动测试文件**

按测试目标将现有测试文件移到对应目录。

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "test: reorganize tests to mirror new module structure"
```

### Task 23: 删除空目录和废弃文件

- [ ] **Step 1: 删除已空的旧目录**

```bash
# 检查并删除空目录
find src/media_tools -type d -empty -delete
```

- [ ] **Step 2: 删除 services/ 目录（应该已空）**

```bash
rm -rf src/media_tools/services/
rm -rf src/media_tools/workers/
rm -rf src/media_tools/pipeline/
rm -rf src/media_tools/repositories/
rm -rf src/media_tools/db/
rm -rf src/media_tools/common/
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore(cleanup): remove empty directories after restructure"
```

### Task 24: 最终验证

- [ ] **Step 1: 跑全部测试**

```bash
python -m pytest tests/ -q
```

- [ ] **Step 2: 检查依赖方向**

```bash
# 检查是否存在反向依赖
# platform/ 不应 import 业务域
grep -r "from media_tools\.\(download\|transcribe\|assets\|scheduler\)" src/media_tools/platform/ || echo "OK"

# store/ 不应 import 业务域
grep -r "from media_tools\.\(download\|transcribe\|assets\|scheduler\|platform\)" src/media_tools/store/ || echo "OK"
```

- [ ] **Step 3: 手动启动服务**

```bash
cd src && python -m media_tools.api.app
```

- [ ] **Step 4: 运行核心流程验证（下载+转写）**

---

## Self-Review Checklist

- [ ] **Spec coverage:** 所有 6 个 Phase 都有对应 Task
- [ ] **Placeholder scan:** 无 TBD/TODO
- [ ] **Import 一致性:** 所有新模块使用 `media_tools.{domain}` 前缀
- [ ] **Git 历史:** 使用 `git mv` 保留文件历史
- [ ] **测试覆盖:** 每 Phase 后有测试验证步骤
