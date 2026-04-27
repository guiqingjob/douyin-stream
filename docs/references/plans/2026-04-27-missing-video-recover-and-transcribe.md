# Missing Video Recovery + Auto Transcribe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Goal:** 当“作品列表数 > 实际落盘视频数”时，系统自动对账并在任务中心列出缺失视频（按标题展示），自动重试 3 次后转入“人工补齐”；用户在 UI 点击“补齐并转写”会创建一个新任务完成单条下载并立即转写。
>
> **Architecture:** 下载任务结束后基于 `video_metadata`(aweme_id, desc) 与 `media_assets`(video_status, video_path) 做作品级对账生成 `missing_items`；对缺失项自动执行单条补齐尝试（最多 3 次）；补齐仍失败则在原任务 subtasks 中标记 `manual_required`。前端在 subtasks 中渲染按钮触发新任务 `recover_aweme_transcribe`。
>
> **Tech Stack:** FastAPI + asyncio tasks + SQLite (task_queue/video_metadata/media_assets) + React + WebSocket task_update

---

## File Map (新增/修改点)

**Backend**
- Modify: `src/media_tools/workers/creator_sync.py`
- Modify: `src/media_tools/api/routers/tasks.py`
- Modify: `src/media_tools/api/schemas.py`
- Create: `src/media_tools/workers/aweme_recover_worker.py`
- (Optional) Modify: `src/media_tools/douyin/core/downloader.py`（暴露/复用单条下载函数已存在：`download_aweme_by_url`）

**Frontend**
- Modify: `frontend/src/components/layout/TaskMonitorPanel/TaskItem.tsx`
- Modify: `frontend/src/lib/api.ts`（新增调用）

**Tests**
- Create: `tests/api/test_tasks_recover_aweme_transcribe.py`
- Create: `tests/test_creator_download_missing_items_payload.py`

---

## Conventions / Data Contracts

### Task payload fields
- `payload.missing_items`: `Array<{ aweme_id: string; title: string; status: "manual_required"; reason: string; attempts: number }>`
- `payload.subtasks`: 继续复用现有结构（前端已展示），其中缺失项用：
  - `status="failed"`（用于红色展示）或新增 `status="manual_required"`（推荐），并用 `error` 填写 reason
  - `title` 填写视频标题

### New task type
- `task_type="recover_aweme_transcribe"`（单条补齐并转写）
- payload 必带：`creator_uid`, `aweme_id`, `title`（可为空，后端会从 video_metadata 回填）

---

## Task 1: Creator Download 对账 + 缺失项生成

**Files:**
- Modify: `src/media_tools/workers/creator_sync.py`
- Test: `tests/test_creator_download_missing_items_payload.py`

- [ ] **Step 1: Write failing test for missing_items payload**

```python
import asyncio
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_creator_download_sets_missing_items_in_payload() -> None:
    from media_tools.workers.creator_sync import background_creator_download_worker

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE creators (uid TEXT PRIMARY KEY, sec_user_id TEXT, nickname TEXT, platform TEXT, sync_status TEXT);
        CREATE TABLE task_queue (task_id TEXT PRIMARY KEY, task_type TEXT, status TEXT, progress REAL, payload TEXT, error_msg TEXT, update_time TEXT);
        CREATE TABLE video_metadata (aweme_id TEXT PRIMARY KEY, uid TEXT NOT NULL, desc TEXT);
        CREATE TABLE media_assets (asset_id TEXT PRIMARY KEY, creator_uid TEXT, title TEXT, video_path TEXT, video_status TEXT, transcript_status TEXT);
        """
    )
    creator_uid = "douyin:123"
    conn.execute("INSERT INTO creators(uid, sec_user_id, nickname, platform, sync_status) VALUES(?,?,?,?, 'active')", (creator_uid, "MS4wxxx", "n", "douyin"))
    task_id = "t1"
    conn.execute("INSERT INTO task_queue(task_id, task_type, status, progress, payload) VALUES(?, ?, 'RUNNING', 0.0, '{}')", (task_id, "creator_sync_incremental"))

    conn.execute("INSERT INTO video_metadata(aweme_id, uid, desc) VALUES(?,?,?)", ("a_ok", creator_uid, "ok title"))
    conn.execute("INSERT INTO video_metadata(aweme_id, uid, desc) VALUES(?,?,?)", ("a_missing", creator_uid, "missing title"))
    conn.execute("INSERT INTO media_assets(asset_id, creator_uid, title, video_path, video_status, transcript_status) VALUES(?,?,?,?,?,?)",
                 ("a_ok", creator_uid, "ok title", "x.mp4", "downloaded", "none"))
    conn.execute("INSERT INTO media_assets(asset_id, creator_uid, title, video_path, video_status, transcript_status) VALUES(?,?,?,?,?,?)",
                 ("a_missing", creator_uid, "missing title", "", "pending", "none"))
    conn.commit()

    fake_dl_result = {"success": True, "new_files": []}

    with patch("media_tools.workers.creator_sync.get_db_connection", return_value=conn), patch(
        "media_tools.workers.creator_sync.asyncio.to_thread",
        new=AsyncMock(return_value=fake_dl_result),
    ), patch(
        "media_tools.workers.creator_sync.get_runtime_setting_bool",
        return_value=False,
    ):
        await background_creator_download_worker(task_id, creator_uid, "incremental")

    row = conn.execute("SELECT payload FROM task_queue WHERE task_id=?", (task_id,)).fetchone()
    assert row is not None
    assert "missing title" in row["payload"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
.venv/bin/python -m pytest -q tests/test_creator_download_missing_items_payload.py::test_creator_download_sets_missing_items_in_payload
```
Expected: FAIL（payload 中没有 missing_items/subtasks 缺失信息）

- [ ] **Step 3: Implement missing_items derivation in creator_sync**

Implementation notes (在 `background_creator_download_worker` 下载完成后、自动转写前或后均可，但推荐在下载完成后立即生成)：
- 从 `video_metadata` 获取该 `creator_uid` 的 `aweme_id, desc`
- 从 `media_assets` 获取同一批 `aweme_id` 的 `video_status`
- `missing = [aweme_id where video_status != 'downloaded']`
- 将缺失项写入：
  - `subtasks.append({"title": desc, "status": "manual_required", "error": reason})`
  - `result_summary.total` 用 `len(video_metadata)`；`result_summary.failed` 用 `len(missing)`
  - `msg` 增加“缺失 N 条，可在任务详情中补齐”

Code skeleton (放在 `creator_sync.py` 内部，复用现有 `update_task_progress/_complete_task` 输出 payload 合并逻辑)：

```python
def _build_missing_items(conn: sqlite3.Connection, creator_uid: str) -> list[dict[str, object]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT aweme_id, COALESCE(desc, '') AS title FROM video_metadata WHERE uid=? AND aweme_id != ''",
        (creator_uid,),
    ).fetchall()
    if not rows:
        return []
    aweme_ids = [str(r["aweme_id"]) for r in rows]
    title_by_id = {str(r["aweme_id"]): str(r["title"] or "") for r in rows}
    placeholders = ",".join("?" * len(aweme_ids))
    assets = conn.execute(
        f"SELECT asset_id, video_status FROM media_assets WHERE asset_id IN ({placeholders})",
        aweme_ids,
    ).fetchall()
    status_by_id = {str(r["asset_id"]): str(r["video_status"] or "") for r in assets}
    missing_items: list[dict[str, object]] = []
    for aweme_id in aweme_ids:
        if status_by_id.get(aweme_id) != "downloaded":
            missing_items.append({
                "aweme_id": aweme_id,
                "title": title_by_id.get(aweme_id) or aweme_id,
                "status": "manual_required",
                "reason": "download_failed",
                "attempts": 3,
            })
    return missing_items
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
.venv/bin/python -m pytest -q tests/test_creator_download_missing_items_payload.py::test_creator_download_sets_missing_items_in_payload
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/workers/creator_sync.py tests/test_creator_download_missing_items_payload.py
git commit -m "feat(tasks): surface missing videos after creator download"
```

---

## Task 2: 单条“补齐并转写”任务（recover_aweme_transcribe）

**Files:**
- Create: `src/media_tools/workers/aweme_recover_worker.py`
- Modify: `src/media_tools/api/schemas.py`
- Modify: `src/media_tools/api/routers/tasks.py`
- Test: `tests/api/test_tasks_recover_aweme_transcribe.py`

- [ ] **Step 1: Write failing API test**

```python
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from media_tools.api.app import app


def test_trigger_recover_aweme_creates_new_task() -> None:
    client = TestClient(app)
    with patch("media_tools.api.routers.tasks._register_background_task") as reg, patch(
        "media_tools.api.routers.tasks._create_task",
        new=AsyncMock(),
    ):
        resp = client.post("/api/v1/tasks/recover/aweme", json={"creator_uid": "douyin:1", "aweme_id": "123", "title": "t"})
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == "started"
    assert reg.called
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest -q tests/api/test_tasks_recover_aweme_transcribe.py::test_trigger_recover_aweme_creates_new_task
```
Expected: FAIL（endpoint 不存在）

- [ ] **Step 3: Add request schema**

In `src/media_tools/api/schemas.py`:

```python
class RecoverAwemeTranscribeRequest(BaseModel):
    creator_uid: str
    aweme_id: str
    title: str = ""
```

- [ ] **Step 4: Add tasks router endpoint**

In `src/media_tools/api/routers/tasks.py` add:

```python
@router.post("/recover/aweme")
async def trigger_recover_aweme(req: RecoverAwemeTranscribeRequest):
    task_id = str(uuid.uuid4())
    await _create_task(task_id, "recover_aweme_transcribe", {"creator_uid": req.creator_uid, "aweme_id": req.aweme_id, "title": req.title})
    from media_tools.workers.aweme_recover_worker import background_recover_aweme_transcribe_worker
    _register_background_task(task_id, background_recover_aweme_transcribe_worker(task_id, req.creator_uid, req.aweme_id, req.title))
    return {"task_id": task_id, "status": "started"}
```

- [ ] **Step 5: Implement worker**

Create `src/media_tools/workers/aweme_recover_worker.py`:

```python
from __future__ import annotations

import asyncio
import sqlite3
from typing import Any

from media_tools.db.core import get_db_connection
from media_tools.services.task_ops import update_task_progress, _complete_task
from media_tools.services.task_state import _task_heartbeat
from media_tools.douyin.core.downloader import download_aweme_by_url
from media_tools.workers.transcribe import transcribe_files
from media_tools.core.config import get_runtime_setting_bool


async def background_recover_aweme_transcribe_worker(task_id: str, creator_uid: str, aweme_id: str, title: str) -> None:
    async def _progress(p: float, msg: str, stage: str = "") -> None:
        await update_task_progress(task_id, p, msg, "recover_aweme_transcribe", stage=stage)

    heartbeat = asyncio.create_task(_task_heartbeat(task_id))
    try:
        resolved_title = title
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT desc FROM video_metadata WHERE aweme_id=? LIMIT 1", (aweme_id,)).fetchone()
                if row and row["desc"]:
                    resolved_title = str(row["desc"])
        except (sqlite3.Error, OSError):
            pass

        await _progress(0.05, f"补齐下载：{resolved_title or aweme_id}", stage="downloading")
        url = f"https://www.douyin.com/video/{aweme_id}"
        result = await download_aweme_by_url(url)
        if not isinstance(result, dict) or not result.get("success"):
            raise RuntimeError(f"补齐下载失败: {result}")

        new_files = result.get("new_files") or []
        if not new_files:
            raise RuntimeError("补齐下载未产生新文件")

        await _progress(0.6, f"开始转写：{len(new_files)} 个文件", stage="transcribing")
        auto_delete = get_runtime_setting_bool("auto_delete")
        tr = await transcribe_files(task_id, _progress, list(new_files), resolved_title or creator_uid, auto_delete)

        s = int(tr.get("success_count", 0) or 0)
        f = int(tr.get("failed_count", 0) or 0)
        total = int(tr.get("total", s + f) or (s + f))
        subtasks = tr.get("subtasks", []) or []
        msg = f"补齐并转写完成：成功 {s} 个，失败 {f} 个"
        status = "COMPLETED" if s > 0 else "FAILED"

        await _complete_task(
            task_id,
            "recover_aweme_transcribe",
            msg,
            status=status,
            error_msg=(subtasks[0].get("error") if status == "FAILED" and subtasks else None),
            result_summary={"success": s, "failed": f, "skipped": 0, "total": total},
            subtasks=subtasks,
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError, ValueError, TypeError) as e:
        await _complete_task(task_id, "recover_aweme_transcribe", str(e), status="FAILED", error_msg=str(e))
    finally:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass
```

- [ ] **Step 6: Run test to verify it passes**

```bash
.venv/bin/python -m pytest -q tests/api/test_tasks_recover_aweme_transcribe.py::test_trigger_recover_aweme_creates_new_task
```
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/media_tools/api/schemas.py src/media_tools/api/routers/tasks.py src/media_tools/workers/aweme_recover_worker.py tests/api/test_tasks_recover_aweme_transcribe.py
git commit -m "feat(tasks): add recover-aweme download+transcribe task"
```

---

## Task 3: 前端 subtasks “补齐并转写”按钮（创建新任务）

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/components/layout/TaskMonitorPanel/TaskItem.tsx`

- [ ] **Step 1: Add API call**

In `frontend/src/lib/api.ts` add:

```ts
export const recoverAwemeAndTranscribe = async (creatorUid: string, awemeId: string, title: string) => {
  const response = await apiClient.post('/tasks/recover/aweme', { creator_uid: creatorUid, aweme_id: awemeId, title });
  return response.data as { task_id: string; status: string };
};
```

- [ ] **Step 2: Render action button for manual_required**

In `TaskItem.tsx` inside subtasks rendering, when `sub.status === 'manual_required'` show a button “补齐并转写”:
- 点击后调用 `recoverAwemeAndTranscribe(task.creator_uid or parsed.creator_uid, sub.aweme_id, sub.title)`（creator_uid 从 payload 或 task 字段取，若缺则禁止按钮并提示）
- 成功后 toast “已创建补齐任务”，并触发 `fetchInitialTasks()` 刷新任务中心

Data contract for subtasks item (前端解析时扩展):
`{ title: string; status: string; error?: string; aweme_id?: string; creator_uid?: string }`

- [ ] **Step 3: Manual UI check**

Run dev server,触发一次下载任务产生 `manual_required` 子项，确认：
- 子项行出现按钮
- 点击后任务中心出现新任务 `recover_aweme_transcribe`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/components/layout/TaskMonitorPanel/TaskItem.tsx
git commit -m "feat(ui): add recover-and-transcribe action for missing videos"
```

---

## Task 4: End-to-End verification

- [ ] **Step 1: Backend full test**

```bash
.venv/bin/python -m pytest -q
```
Expected: PASS

- [ ] **Step 2: Frontend tests**

```bash
cd frontend && npm test --silent
```
Expected: exit code 0

- [ ] **Step 3: Manual run**
- 运行一次“下载并转写”任务，制造 1 条缺失（可通过断网/限制环境模拟），确认：
  - 原任务 subtasks 中出现 `manual_required` 的标题项
  - 点击“补齐并转写”能创建新任务并执行

