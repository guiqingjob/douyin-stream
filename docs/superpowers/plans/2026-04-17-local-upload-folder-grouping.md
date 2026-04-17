# Local Upload Folder Grouping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按“发现页输入的扫描目录”为根，把“本地上传”素材在 Inbox 中按文件夹分组展示，避免全部堆在同一列表里。

**Architecture:** 后端为本地素材写入 `media_assets.folder_path`（相对扫描根目录的父目录路径），并在 assets 列表接口返回该字段；前端在选中 `local:upload` 创作者时按 `folder_path` 分组渲染可折叠列表。扫描目录通过本地转写请求一起传给后端。

**Tech Stack:** FastAPI + sqlite3（后端），React + TypeScript（前端），pytest（后端测试）。

---

## File Map

**Backend**
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/db/core.py](file:///Users/gq/Projects/media-tools/src/media_tools/db/core.py)
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/api/routers/tasks.py](file:///Users/gq/Projects/media-tools/src/media_tools/api/routers/tasks.py)
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/api/routers/assets.py](file:///Users/gq/Projects/media-tools/src/media_tools/api/routers/assets.py)
- Create: `/Users/gq/Projects/media-tools/tests/test_local_folder_grouping.py`

**Frontend**
- Modify: [/Users/gq/Projects/media-tools/frontend/src/lib/api.ts](file:///Users/gq/Projects/media-tools/frontend/src/lib/api.ts)
- Modify: [/Users/gq/Projects/media-tools/frontend/src/pages/Discovery.tsx](file:///Users/gq/Projects/media-tools/frontend/src/pages/Discovery.tsx)
- Modify: [/Users/gq/Projects/media-tools/frontend/src/pages/Inbox.tsx](file:///Users/gq/Projects/media-tools/frontend/src/pages/Inbox.tsx)

---

### Task 1: Add `folder_path` Column to `media_assets`

**Files:**
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/db/core.py](file:///Users/gq/Projects/media-tools/src/media_tools/db/core.py)
- Test: `/Users/gq/Projects/media-tools/tests/test_local_folder_grouping.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_local_folder_grouping.py`:

```python
from __future__ import annotations

import sqlite3


def test_db_init_adds_media_assets_folder_path(tmp_path) -> None:
    from media_tools.db.core import init_db

    db_path = tmp_path / "t.db"
    init_db(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cols = [row[1] for row in conn.execute("PRAGMA table_info(media_assets)").fetchall()]
    assert "folder_path" in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest -q tests/test_local_folder_grouping.py::test_db_init_adds_media_assets_folder_path
```

Expected: FAIL（`folder_path` 不存在）

- [ ] **Step 3: Implement minimal DB migration**

In `init_db(...)` add:

```python
_ensure_column(conn, "media_assets", "folder_path", "TEXT DEFAULT ''")
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest -q tests/test_local_folder_grouping.py::test_db_init_adds_media_assets_folder_path
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/db/core.py tests/test_local_folder_grouping.py
git commit -m "feat(db): add media_assets folder_path"
```

---

### Task 2: Pass Scan Root Into Local Transcribe Request

**Files:**
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/api/routers/tasks.py](file:///Users/gq/Projects/media-tools/src/media_tools/api/routers/tasks.py)
- Modify: [/Users/gq/Projects/media-tools/frontend/src/lib/api.ts](file:///Users/gq/Projects/media-tools/frontend/src/lib/api.ts)
- Modify: [/Users/gq/Projects/media-tools/frontend/src/pages/Discovery.tsx](file:///Users/gq/Projects/media-tools/frontend/src/pages/Discovery.tsx)
- Test: `/Users/gq/Projects/media-tools/tests/test_local_folder_grouping.py`

- [ ] **Step 1: Write the failing test (API request model accepts directory_root)**

Append to `tests/test_local_folder_grouping.py`:

```python
def test_local_transcribe_request_accepts_directory_root() -> None:
    from media_tools.api.routers.tasks import LocalTranscribeRequest

    req = LocalTranscribeRequest(file_paths=["/tmp/a.mp3"], delete_after=False, directory_root="/tmp")
    assert req.directory_root == "/tmp"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest -q tests/test_local_folder_grouping.py::test_local_transcribe_request_accepts_directory_root
```

Expected: FAIL（模型不接受 `directory_root`）

- [ ] **Step 3: Implement request + frontend client changes**

Backend `LocalTranscribeRequest` add field:

```python
from typing import Optional

class LocalTranscribeRequest(BaseModel):
    file_paths: List[str]
    delete_after: bool = False
    directory_root: Optional[str] = None
```

Frontend API `triggerLocalTranscribe` signature becomes:

```ts
export const triggerLocalTranscribe = async (
  filePaths: string[],
  deleteAfter: boolean,
  directoryRoot?: string
): Promise<{task_id: string}> => {
  const response = await apiClient.post('/tasks/transcribe/local', {
    file_paths: filePaths,
    delete_after: deleteAfter,
    directory_root: directoryRoot || null,
  });
  return response.data;
};
```

Discovery page call:

```ts
await triggerLocalTranscribe(Array.from(selectedLocalFiles), deleteAfterTranscribe, localDir.trim());
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest -q tests/test_local_folder_grouping.py::test_local_transcribe_request_accepts_directory_root
```

Expected: PASS

- [ ] **Step 5: Build frontend**

Run:

```bash
cd frontend && npm run build
```

Expected: build success

- [ ] **Step 6: Commit**

```bash
git add src/media_tools/api/routers/tasks.py frontend/src/lib/api.ts frontend/src/pages/Discovery.tsx tests/test_local_folder_grouping.py
git commit -m "feat(local): send directory_root for local transcribe"
```

---

### Task 3: Compute and Store `folder_path` for Local Assets

**Files:**
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/api/routers/tasks.py](file:///Users/gq/Projects/media-tools/src/media_tools/api/routers/tasks.py)
- Test: `/Users/gq/Projects/media-tools/tests/test_local_folder_grouping.py`

- [ ] **Step 1: Write the failing test (folder_path derived from directory_root)**

Append to `tests/test_local_folder_grouping.py`:

```python
def test_register_local_assets_writes_folder_path(tmp_path, monkeypatch) -> None:
    from media_tools.api.routers import tasks as tasks_router

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE creators (
          uid TEXT PRIMARY KEY,
          sec_user_id TEXT,
          nickname TEXT,
          avatar TEXT,
          bio TEXT,
          platform TEXT,
          sync_status TEXT,
          last_fetch_time DATETIME
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE media_assets (
          asset_id TEXT PRIMARY KEY,
          creator_uid TEXT,
          source_url TEXT,
          title TEXT,
          duration INTEGER,
          video_path TEXT,
          video_status TEXT,
          transcript_path TEXT,
          transcript_status TEXT,
          folder_path TEXT DEFAULT '',
          is_read BOOLEAN DEFAULT 0,
          is_starred BOOLEAN DEFAULT 0,
          create_time DATETIME,
          update_time DATETIME
        )
        """
    )
    conn.commit()

    root = tmp_path / "root"
    sub = root / "chapter1"
    sub.mkdir(parents=True)
    f = sub / "a.mp3"
    f.write_bytes(b"ok")

    monkeypatch.setattr("media_tools.api.routers.tasks.get_db_connection", lambda: conn)

    tasks_router._register_local_assets([str(f)], delete_after=False, directory_root=str(root))

    row = conn.execute("SELECT folder_path FROM media_assets").fetchone()
    assert row["folder_path"] == "chapter1"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest -q tests/test_local_folder_grouping.py::test_register_local_assets_writes_folder_path
```

Expected: FAIL（`_register_local_assets` 未接收/未写入 folder_path）

- [ ] **Step 3: Implement folder_path computation + write**

In `tasks.py`:
- Update `_register_local_assets` signature:

```python
def _register_local_assets(file_paths: list[str], delete_after: bool, directory_root: str | None = None) -> None:
    ...
```

- Compute `folder_path`:

```python
def _compute_folder_path(file_path: Path, directory_root: str | None) -> str:
    if not directory_root:
        return ""
    try:
        root = Path(directory_root).resolve()
        p = file_path.resolve()
        rel = p.parent.relative_to(root)
        return rel.as_posix() if str(rel) != "." else ""
    except Exception:
        return "(其他)"
```

- Include in INSERT:

```python
folder_path = _compute_folder_path(path, directory_root)
conn.execute(
    """
    INSERT OR IGNORE INTO media_assets
    (asset_id, creator_uid, source_url, title, video_status, transcript_status, folder_path, create_time, update_time)
    VALUES (?, ?, ?, ?, 'downloaded', 'pending', ?, ?, ?)
    """,
    (asset_id, LOCAL_CREATOR_UID, str(path.resolve()), path.stem, folder_path, now, now),
)
```

- Wire from endpoint:

```python
_register_local_assets(req.file_paths, req.delete_after, req.directory_root)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest -q tests/test_local_folder_grouping.py::test_register_local_assets_writes_folder_path
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/api/routers/tasks.py tests/test_local_folder_grouping.py
git commit -m "feat(local): store folder_path for local assets"
```

---

### Task 4: Return `folder_path` in Assets API

**Files:**
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/api/routers/assets.py](file:///Users/gq/Projects/media-tools/src/media_tools/api/routers/assets.py)
- Test: `/Users/gq/Projects/media-tools/tests/test_local_folder_grouping.py`

- [ ] **Step 1: Write failing test (list_assets includes folder_path)**

Append:

```python
def test_list_assets_returns_folder_path(monkeypatch) -> None:
    from media_tools.api.routers import assets as assets_router

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE media_assets (
          asset_id TEXT PRIMARY KEY,
          creator_uid TEXT,
          title TEXT,
          video_status TEXT,
          transcript_status TEXT,
          transcript_path TEXT,
          folder_path TEXT DEFAULT '',
          is_read BOOLEAN DEFAULT 0,
          is_starred BOOLEAN DEFAULT 0
        )
        """
    )
    conn.execute(
        "INSERT INTO media_assets(asset_id, creator_uid, title, video_status, transcript_status, transcript_path, folder_path, is_read, is_starred) VALUES(?,?,?,?,?,?,?,?,?)",
        ("a1", "local:upload", "t", "downloaded", "pending", None, "chapter1", 0, 0),
    )
    conn.commit()
    monkeypatch.setattr("media_tools.api.routers.assets.get_db_connection", lambda: conn)

    rows = assets_router.list_assets(creator_uid="local:upload")
    assert rows[0]["folder_path"] == "chapter1"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest -q tests/test_local_folder_grouping.py::test_list_assets_returns_folder_path
```

Expected: FAIL（当前 SELECT 未返回该字段）

- [ ] **Step 3: Implement**

Update SELECT list in `assets.py` list_assets:

```python
"SELECT asset_id, creator_uid, title, video_status, transcript_status, transcript_path, folder_path, is_read, is_starred FROM media_assets ..."
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest -q tests/test_local_folder_grouping.py::test_list_assets_returns_folder_path
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/api/routers/assets.py tests/test_local_folder_grouping.py
git commit -m "feat(assets): return folder_path for grouping"
```

---

### Task 5: Group Local Upload Assets by Folder in Inbox UI

**Files:**
- Modify: [/Users/gq/Projects/media-tools/frontend/src/pages/Inbox.tsx](file:///Users/gq/Projects/media-tools/frontend/src/pages/Inbox.tsx)
- Modify: [/Users/gq/Projects/media-tools/frontend/src/lib/api.ts](file:///Users/gq/Projects/media-tools/frontend/src/lib/api.ts)

- [ ] **Step 1: Extend Asset type to include folder_path**

In `frontend/src/lib/api.ts`, extend `Asset` interface (locate the existing interface and add field):

```ts
folder_path?: string;
```

- [ ] **Step 2: Add grouping helpers**

In `Inbox.tsx` add:

```ts
type AssetGroup = { key: string; title: string; items: Asset[] };

function groupLocalAssetsByFolder(items: Asset[]): AssetGroup[] {
  const map = new Map<string, Asset[]>();
  for (const a of items) {
    const key = (a.folder_path || '').trim();
    const list = map.get(key) || [];
    list.push(a);
    map.set(key, list);
  }
  const groups = Array.from(map.entries()).map(([key, list]) => ({
    key,
    title: key === '' ? '根目录' : key,
    items: list,
  }));
  groups.sort((a, b) => (a.key === '' ? -1 : b.key === '' ? 1 : a.title.localeCompare(b.title)));
  return groups;
}
```

- [ ] **Step 3: Render grouped UI for local creator**

Detect local creator:

```ts
const isLocalCreator = selectedCreatorUid === 'local:upload';
```

If `isLocalCreator`, render grouped list instead of flat `VirtuosoGrid`. Use simple collapsible state:

```ts
const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({});
const toggleFolder = (k: string) => setOpenFolders((p) => ({ ...p, [k]: !p[k] }));
```

Render:
- folder header row clickable
- if open, render the existing `renderAssetCard` for each asset in that group

- [ ] **Step 4: Build frontend**

Run:

```bash
cd frontend && npm run build
```

Expected: build success

- [ ] **Step 5: Manual verification**

Run:
- 在“发现”页输入一个包含子目录的本地根目录，扫描后全选并提交本地转写
- 打开 Inbox，选择“本地上传”，确认按文件夹分组显示且可展开

- [ ] **Step 6: Commit**

```bash
cd frontend
git add src/lib/api.ts src/pages/Inbox.tsx
git commit -m "feat(inbox): group local uploads by folder"
cd ..
git add frontend
git commit -m "chore: update frontend"
```

---

### Task 6: Full Test Run

**Files:** none

- [ ] **Step 1: Run backend tests**

```bash
.venv/bin/pytest -q
```

Expected: PASS

- [ ] **Step 2: Build frontend**

```bash
cd frontend && npm run build
```

Expected: build success

