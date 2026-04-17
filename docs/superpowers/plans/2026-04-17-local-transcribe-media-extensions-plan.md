# Local Transcribe MEDIA_EXTENSIONS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 本地目录扫描与本地转写统一支持音频+视频（新增 mp3），并复用同一份后缀集合，确保扫描 mp3 后可提交转写任务并产出转录稿。

**Architecture:** 抽取共享常量 `MEDIA_EXTENSIONS`（音频+视频）到独立模块；扫描接口与本地转写过滤逻辑都引用该模块；前端仅更新文案提示为“音视频文件”。

**Tech Stack:** FastAPI + Python 3.11，React + Vite + TypeScript，pytest，fastapi.testclient

---

## File Map

**Backend**
- Create: `src/media_tools/pipeline/media_extensions.py`
- Modify: `src/media_tools/api/routers/tasks.py`
- Modify: `src/media_tools/pipeline/worker.py`
- Test: `tests/test_local_media_extensions.py`

**Frontend**
- Modify: `frontend/src/pages/Discovery.tsx`

---

### Task 1: Add shared MEDIA_EXTENSIONS module (TDD)

**Files:**
- Create: `src/media_tools/pipeline/media_extensions.py`
- Test: `tests/test_local_media_extensions.py`

- [ ] **Step 1: Write failing tests for MEDIA_EXTENSIONS**

```python
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from media_tools.api.app import app
from media_tools.pipeline.media_extensions import MEDIA_EXTENSIONS


client = TestClient(app)


def test_media_extensions_contains_mp3() -> None:
    assert ".mp3" in MEDIA_EXTENSIONS


def test_scan_directory_returns_mp3_files() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
        mp3_path = Path(temp_dir) / "a.mp3"
        mp3_path.write_bytes(b"fake mp3 content")

        response = client.post("/api/v1/tasks/transcribe/scan", json={"directory": temp_dir})
        assert response.status_code == 200
        payload = response.json()
        paths = {f["path"] for f in payload["files"]}
        assert str(mp3_path) in paths
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest -q tests/test_local_media_extensions.py
```

Expected: FAIL（`ModuleNotFoundError: media_tools.pipeline.media_extensions` 或 `.mp3` 未包含 / 扫描接口不返回 mp3）

- [ ] **Step 3: Implement MEDIA_EXTENSIONS**

Create `src/media_tools/pipeline/media_extensions.py`:
```python
MEDIA_EXTENSIONS: set[str] = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".flv",
    ".webm",
    ".mp3",
}
```

- [ ] **Step 4: Run tests again to confirm they still fail on scan behavior**

Run:
```bash
pytest -q tests/test_local_media_extensions.py::test_scan_directory_returns_mp3_files
```

Expected: FAIL（扫描接口仍未返回 mp3）

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/pipeline/media_extensions.py tests/test_local_media_extensions.py
git commit -m "feat: add shared MEDIA_EXTENSIONS for local media"
```

---

### Task 2: Use MEDIA_EXTENSIONS in local scan endpoint

**Files:**
- Modify: `src/media_tools/api/routers/tasks.py`
- Test: `tests/test_local_media_extensions.py`

- [ ] **Step 1: Update scan endpoint to use MEDIA_EXTENSIONS**

In `src/media_tools/api/routers/tasks.py`, update `/tasks/transcribe/scan`:
```python
from media_tools.pipeline.media_extensions import MEDIA_EXTENSIONS

extensions = MEDIA_EXTENSIONS
```

- [ ] **Step 2: Run scan test to verify it passes**

Run:
```bash
pytest -q tests/test_local_media_extensions.py::test_scan_directory_returns_mp3_files
```

Expected: PASS

- [ ] **Step 3: Run full test suite**

Run:
```bash
pytest -q
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/media_tools/api/routers/tasks.py
git commit -m "feat: include mp3 in local scan via shared extensions"
```

---

### Task 3: Use MEDIA_EXTENSIONS in local transcribe filter (TDD for filtering)

**Files:**
- Modify: `src/media_tools/pipeline/worker.py`
- Update: `tests/test_local_media_extensions.py`

- [ ] **Step 1: Add a failing unit test for local transcribe filtering**

Append to `tests/test_local_media_extensions.py`:
```python
from media_tools.pipeline.worker import filter_supported_media_paths


def test_filter_supported_media_paths_keeps_mp3() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
        mp3_path = Path(temp_dir) / "b.mp3"
        mp3_path.write_bytes(b"fake")
        paths = filter_supported_media_paths([str(mp3_path)])
        assert paths == [mp3_path]
```

- [ ] **Step 2: Run the new test to verify it fails**

Run:
```bash
pytest -q tests/test_local_media_extensions.py::test_filter_supported_media_paths_keeps_mp3
```

Expected: FAIL（`ImportError`/`AttributeError`：函数不存在）

- [ ] **Step 3: Implement filter_supported_media_paths and wire it into run_local_transcribe**

In `src/media_tools/pipeline/worker.py`:
```python
from media_tools.pipeline.media_extensions import MEDIA_EXTENSIONS

def filter_supported_media_paths(file_paths: list[str]) -> list[Path]:
    valid_paths: list[Path] = []
    for p in file_paths:
        path = Path(p)
        if path.exists() and path.suffix.lower() in MEDIA_EXTENSIONS:
            valid_paths.append(path)
    return valid_paths
```

And in `run_local_transcribe(...)`, replace the current filtering block with:
```python
valid_paths = filter_supported_media_paths(file_paths)
```

- [ ] **Step 4: Run the filtering test to verify it passes**

Run:
```bash
pytest -q tests/test_local_media_extensions.py::test_filter_supported_media_paths_keeps_mp3
```

Expected: PASS

- [ ] **Step 5: Run full test suite**

Run:
```bash
pytest -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/media_tools/pipeline/worker.py tests/test_local_media_extensions.py
git commit -m "feat: allow mp3 in local transcribe via shared extensions"
```

---

### Task 4: Update frontend copy to “音视频文件”

**Files:**
- Modify: `frontend/src/pages/Discovery.tsx`

- [ ] **Step 1: Update copy strings**

In `frontend/src/pages/Discovery.tsx`, update:
- `该目录下没有找到视频文件` -> `该目录下没有找到音视频文件`
- `找到 {scannedFiles.length} 个视频文件` -> `找到 {scannedFiles.length} 个音视频文件`

- [ ] **Step 2: Run frontend typecheck/build**

Run:
```bash
cd frontend && npm test
```

If `npm test` is not configured, run instead:
```bash
cd frontend && npm run build
```

Expected: PASS（无 TS 错误）

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Discovery.tsx
git commit -m "chore: update local scan copy for audio+video"
```

---

### Task 5: Manual verification (API + UI)

**Files:**
- No code changes

- [ ] **Step 1: Start API**

Run:
```bash
./run.sh
```

Expected: API listens on `http://localhost:8000`

- [ ] **Step 2: Start frontend**

Run:
```bash
cd frontend && npm run dev
```

Expected: Vite dev server starts

- [ ] **Step 3: Verify local scan + transcribe for mp3**

1) 在“发现”页本地扫描输入一个包含 `*.mp3` 的目录（建议 `/tmp/...`）
2) 点击“扫描”能列出 mp3
3) 勾选 mp3 点击“转写”
4) 任务中心显示 `本地转写` 进度并最终完成

---

## Plan Self-Review

- 覆盖需求：后端扫描与本地转写统一支持 mp3，且通过共享 `MEDIA_EXTENSIONS` 避免重复改动；前端文案同步更新。
- 无占位符：每一步均提供具体文件、代码与命令。
- 类型一致性：`MEDIA_EXTENSIONS` 为 `set[str]`；`filter_supported_media_paths` 返回 `list[Path]`，测试与实现一致。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-17-local-transcribe-media-extensions-plan.md`. Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session, batch execution with checkpoints

Which approach?

