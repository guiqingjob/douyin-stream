# B 站（UP 主投稿）全量下载 + 自动转写 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 Media Tools 项目中新增 bilibili（仅 UGC 投稿）UP 主全量/增量下载，并与现有任务系统与自动转写链路无缝对接。

**Architecture:** 以 `yt-dlp` 作为下载与解析引擎，新增 `media_tools/bilibili` 模块实现 URL 归一化、同步清单生成、下载与进度回调；在 `pipeline/worker.py` 与 `api/routers/*` 处做最小侵入的“多平台路由”，复用现有任务表与转写 orchestrator。

**Tech Stack:** Python 3.11, FastAPI, sqlite3, yt-dlp, ffmpeg（外部依赖）, pytest/unittest

---

## 本地执行约束（必须先满足）

- 本项目代码使用了 Python 3.11+ 语法与标准库能力（如 `str | None`、`datetime.UTC`），因此测试与运行必须使用 Python 3.11+。
- 下面所有命令默认在项目根目录执行，并使用本地 venv（`.venv/`）来保证 Python 版本与依赖一致。

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -r requirements.txt
```

## File Map（将创建/修改的文件）

**Backend**
- Create: `src/media_tools/bilibili/__init__.py`
- Create: `src/media_tools/bilibili/core/__init__.py`
- Create: `src/media_tools/bilibili/core/models.py`
- Create: `src/media_tools/bilibili/core/url_parser.py`
- Create: `src/media_tools/bilibili/core/sync.py`
- Create: `src/media_tools/bilibili/core/downloader.py`
- Create: `src/media_tools/bilibili/utils/__init__.py`
- Create: `src/media_tools/bilibili/utils/naming.py`
- Create: `src/media_tools/bilibili/utils/cookies.py`
- Create: `src/media_tools/pipeline/download_router.py`
- Modify: `src/media_tools/pipeline/worker.py`
- Modify: `src/media_tools/api/routers/creators.py`
- Modify: `src/media_tools/api/routers/tasks.py`
- Modify: `src/media_tools/api/routers/settings.py`
- Modify: `src/media_tools/db/core.py`（如需新增索引/字段，尽量避免；优先复用现有结构）

**Frontend**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/Creators.tsx`
- Modify: `frontend/src/pages/Settings.tsx`

**Tests**
- Create: `tests/bilibili/test_url_parser.py`
- Create: `tests/bilibili/test_naming.py`
- Create: `tests/bilibili/test_download_router.py`
- Modify: `tests/test_pipeline_worker.py`
- Modify: `tests/api/test_creators.py`

---

### Task 1: Add yt-dlp dependency + checkpoint

**Files:**
- Modify: `requirements.txt`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dependency to requirements.txt**

Add one line:

```text
yt-dlp>=2025.1.1
```

- [ ] **Step 2: Add dependency to pyproject.toml**

Add one entry inside `[project].dependencies`:

```toml
"yt-dlp>=2025.1.1",
```

- [ ] **Step 3: Run unit tests**

Run:

```bash
.venv/bin/python -m pytest -q
```

Expected: PASS（若失败，先修复再继续后续任务）

- [ ] **Step 4: Commit**

```bash
git add requirements.txt pyproject.toml
git commit -m "feat: add yt-dlp dependency"
```

---

### Task 2: Implement bilibili URL normalization + tests

**Files:**
- Create: `src/media_tools/bilibili/core/models.py`
- Create: `src/media_tools/bilibili/core/url_parser.py`
- Create: `tests/bilibili/test_url_parser.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest

from media_tools.bilibili.core.url_parser import normalize_bilibili_url, BilibiliUrlKind


def test_normalize_space_url() -> None:
    parsed = normalize_bilibili_url("https://space.bilibili.com/123456")
    assert parsed.kind is BilibiliUrlKind.SPACE
    assert parsed.mid == "123456"


def test_normalize_video_url() -> None:
    parsed = normalize_bilibili_url("https://www.bilibili.com/video/BV1xx411c7mD")
    assert parsed.kind is BilibiliUrlKind.VIDEO
    assert parsed.bvid == "BV1xx411c7mD"


def test_normalize_short_url_is_detected() -> None:
    parsed = normalize_bilibili_url("https://b23.tv/abcd")
    assert parsed.kind is BilibiliUrlKind.SHORT
    assert parsed.original_url == "https://b23.tv/abcd"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest -q tests/bilibili/test_url_parser.py
```

Expected: FAIL（module/function not found）

- [ ] **Step 3: Implement models + parser**

Create `src/media_tools/bilibili/core/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BilibiliUrlKind(str, Enum):
    SPACE = "space"
    VIDEO = "video"
    SHORT = "short"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NormalizedBilibiliUrl:
    kind: BilibiliUrlKind
    original_url: str
    mid: str | None = None
    bvid: str | None = None
```

Create `src/media_tools/bilibili/core/url_parser.py`:

```python
from __future__ import annotations

from urllib.parse import urlparse

from .models import BilibiliUrlKind, NormalizedBilibiliUrl


def normalize_bilibili_url(url: str) -> NormalizedBilibiliUrl:
    raw = (url or "").strip()
    if not raw:
        return NormalizedBilibiliUrl(kind=BilibiliUrlKind.UNKNOWN, original_url=url)

    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = f"https://{raw}"

    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    if host in {"b23.tv", "www.b23.tv"}:
        return NormalizedBilibiliUrl(kind=BilibiliUrlKind.SHORT, original_url=raw)

    if host.endswith("bilibili.com"):
        if host == "space.bilibili.com":
            mid = path.strip("/").split("/")[0] if path.strip("/") else ""
            if mid.isdigit():
                return NormalizedBilibiliUrl(kind=BilibiliUrlKind.SPACE, original_url=raw, mid=mid)
            return NormalizedBilibiliUrl(kind=BilibiliUrlKind.UNKNOWN, original_url=raw)

        if path.startswith("/video/"):
            parts = path.split("/")
            bvid = parts[2] if len(parts) > 2 else ""
            if bvid.startswith("BV"):
                return NormalizedBilibiliUrl(kind=BilibiliUrlKind.VIDEO, original_url=raw, bvid=bvid)
            return NormalizedBilibiliUrl(kind=BilibiliUrlKind.UNKNOWN, original_url=raw)

    return NormalizedBilibiliUrl(kind=BilibiliUrlKind.UNKNOWN, original_url=raw)
```

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/python -m pytest -q tests/bilibili/test_url_parser.py
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/bilibili/core/models.py src/media_tools/bilibili/core/url_parser.py tests/bilibili/test_url_parser.py
git commit -m "feat: add bilibili url normalization"
```

---

### Task 3: Implement naming + asset_id rules + tests

**Files:**
- Create: `src/media_tools/bilibili/utils/naming.py`
- Create: `tests/bilibili/test_naming.py`

- [ ] **Step 1: Write failing tests**

```python
from __future__ import annotations

from media_tools.bilibili.utils.naming import build_bilibili_creator_uid, build_bilibili_asset_id, sanitize_filename


def test_creator_uid_prefix() -> None:
    assert build_bilibili_creator_uid("123") == "bilibili:123"


def test_asset_id_single() -> None:
    assert build_bilibili_asset_id("BV1xx411c7mD", None) == "bilibili:BV1xx411c7mD"


def test_asset_id_multip() -> None:
    assert build_bilibili_asset_id("BV1xx411c7mD", 2) == "bilibili:BV1xx411c7mD:p2"


def test_sanitize_filename() -> None:
    assert sanitize_filename('a/b:c*?"<>|') == "abc"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest -q tests/bilibili/test_naming.py
```

Expected: FAIL

- [ ] **Step 3: Implement naming helpers**

Create `src/media_tools/bilibili/utils/naming.py`:

```python
from __future__ import annotations

import re


def build_bilibili_creator_uid(mid: str) -> str:
    return f"bilibili:{mid}"


def build_bilibili_asset_id(bvid: str, p_index: int | None) -> str:
    if p_index is None:
        return f"bilibili:{bvid}"
    return f"bilibili:{bvid}:p{p_index}"


def sanitize_filename(name: str) -> str:
    value = name or ""
    value = re.sub(r'[<>:"/\\\\|?*]', "", value)
    value = re.sub(r"\\s+", " ", value).strip()
    return value
```

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/python -m pytest -q tests/bilibili/test_naming.py
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/bilibili/utils/naming.py tests/bilibili/test_naming.py
git commit -m "feat: add bilibili naming helpers"
```

---

### Task 4: Add download router (multi-platform) + tests

**Files:**
- Create: `src/media_tools/pipeline/download_router.py`
- Create: `tests/bilibili/test_download_router.py`
- Modify: `src/media_tools/pipeline/worker.py`
- Modify: `tests/test_pipeline_worker.py`

- [ ] **Step 1: Write failing test for router**

Create `tests/bilibili/test_download_router.py`:

```python
from __future__ import annotations

from unittest.mock import patch

import pytest

from media_tools.pipeline.download_router import resolve_platform


def test_resolve_platform_bilibili() -> None:
    assert resolve_platform("https://space.bilibili.com/123") == "bilibili"


def test_resolve_platform_douyin() -> None:
    assert resolve_platform("https://www.douyin.com/user/xxx") == "douyin"
```

- [ ] **Step 2: Run failing test**

Run:

```bash
.venv/bin/python -m pytest -q tests/bilibili/test_download_router.py
```

Expected: FAIL

- [ ] **Step 3: Implement router**

Create `src/media_tools/pipeline/download_router.py`:

```python
from __future__ import annotations


def resolve_platform(url: str) -> str:
    value = (url or "").lower()
    if "bilibili.com" in value or "b23.tv" in value:
        return "bilibili"
    return "douyin"


def download_by_url(url: str, max_counts: int | None, disable_auto_transcribe: bool, skip_existing: bool):
    platform = resolve_platform(url)
    if platform == "bilibili":
        from media_tools.bilibili.core.downloader import download_up_by_url
        return download_up_by_url(url, max_counts=max_counts, skip_existing=skip_existing)
    from media_tools.douyin.core.downloader import download_by_url as douyin_download_by_url
    return douyin_download_by_url(url, max_counts=max_counts, disable_auto_transcribe=disable_auto_transcribe, skip_existing=skip_existing)
```

- [ ] **Step 4: Refactor pipeline worker to use router**

In `src/media_tools/pipeline/worker.py` replace direct import/call of douyin downloader with router call. The key expectation is: `download_router.download_by_url()` returns the same dict shape `{success: bool, new_files: list[str]}`.

Minimal patch target in `run_pipeline_for_user()`:

```python
from media_tools.pipeline.download_router import download_by_url
```

And ensure the threaded call still works:

```python
dl_result = await asyncio.to_thread(download_by_url, url, max_counts, True, True)
```

- [ ] **Step 5: Update existing pipeline worker test**

Update `tests/test_pipeline_worker.py` to patch `media_tools.pipeline.download_router.download_by_url` instead of `media_tools.douyin.core.downloader.download_by_url` and update asserted args accordingly.

- [ ] **Step 6: Run tests**

Run:

```bash
.venv/bin/python -m pytest -q tests/bilibili/test_download_router.py tests/test_pipeline_worker.py
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/media_tools/pipeline/download_router.py src/media_tools/pipeline/worker.py tests/bilibili/test_download_router.py tests/test_pipeline_worker.py
git commit -m "feat: route download pipeline by platform"
```

---

### Task 5: Bilibili downloader wrapper (yt-dlp) with progress hook (mocked tests)

**Files:**
- Create: `src/media_tools/bilibili/core/downloader.py`
- Create: `src/media_tools/bilibili/utils/cookies.py`

- [ ] **Step 1: Implement cookie resolver (DB-backed pool + config fallback)**

Create `src/media_tools/bilibili/utils/cookies.py`:

```python
from __future__ import annotations

from media_tools.db.core import get_db_connection


def get_bilibili_cookie_string() -> str:
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT cookie_data FROM Accounts_Pool WHERE platform='bilibili' AND status='active' ORDER BY last_used DESC NULLS LAST, create_time DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row and row[0]:
            return str(row[0])
    return ""
```

- [ ] **Step 2: Implement downloader with a single public API**

Create `src/media_tools/bilibili/core/downloader.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any

from media_tools.douyin.core.config_mgr import get_config
from media_tools.logger import get_logger

from media_tools.bilibili.core.url_parser import normalize_bilibili_url, BilibiliUrlKind
from media_tools.bilibili.utils.cookies import get_bilibili_cookie_string
from media_tools.bilibili.utils.naming import sanitize_filename

logger = get_logger("bilibili")

ProgressCallback = Callable[[float, str], Any]


def _build_output_template(base_dir: Path, creator_folder: str, series_folder: str) -> str:
    safe_creator = sanitize_filename(creator_folder) or "bilibili"
    safe_series = sanitize_filename(series_folder) or "全部投稿"
    target_dir = base_dir / safe_creator / safe_series
    target_dir.mkdir(parents=True, exist_ok=True)
    return str(target_dir / "%(title)s__%(id)s__%(format_id)s.%(ext)s")


def download_up_by_url(url: str, max_counts: int | None = None, skip_existing: bool = True, progress_cb: ProgressCallback | None = None) -> dict:
    parsed = normalize_bilibili_url(url)
    if parsed.kind not in {BilibiliUrlKind.SPACE, BilibiliUrlKind.VIDEO, BilibiliUrlKind.SHORT}:
        raise RuntimeError("Invalid bilibili url")

    config = get_config()
    downloads_path = config.get_download_path()

    cookie = get_bilibili_cookie_string()

    def hook(d: dict):
        if not progress_cb:
            return
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            p = (downloaded / total) if total else 0.0
            progress_cb(min(max(p, 0.0), 1.0), "下载中")
        elif status == "finished":
            progress_cb(1.0, "下载完成")

    ydl_opts: dict[str, Any] = {
        "noplaylist": False,
        "ignoreerrors": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "overwrites": False,
        "continuedl": True,
        "consoletitle": False,
        "outtmpl": _build_output_template(downloads_path, "bilibili", "全部投稿"),
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
    }
    if cookie:
        ydl_opts["http_headers"] = {"Cookie": cookie}

    try:
        from yt_dlp import YoutubeDL
    except Exception as exc:
        raise RuntimeError(f"yt-dlp not available: {exc}") from exc

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    new_files: list[str] = []
    if isinstance(info, dict):
        requested = info.get("requested_downloads") or []
        for item in requested:
            fp = item.get("filepath")
            if fp and Path(fp).exists():
                new_files.append(str(Path(fp)))

    return {"success": True, "new_files": new_files}
```

- [ ] **Step 3: Run fast unit tests (no network)**

Run:

```bash
.venv/bin/python -m pytest -q tests/bilibili/test_url_parser.py tests/bilibili/test_naming.py
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/media_tools/bilibili/core/downloader.py src/media_tools/bilibili/utils/cookies.py
git commit -m "feat: add bilibili yt-dlp downloader wrapper"
```

---

### Task 6: Creator add endpoint supports bilibili URL

**Files:**
- Modify: `src/media_tools/api/routers/creators.py`
- Modify: `tests/api/test_creators.py`

- [ ] **Step 1: Update creators router to detect bilibili**

In `create_creator()` add a platform switch:

- If url contains `bilibili.com` or `b23.tv`:
  - parse mid (space URL) or fallback to a minimal placeholder creator record
  - insert into `creators` table with platform `bilibili`

Minimal insertion snippet (no extra dependencies):

```python
from media_tools.db.core import get_db_connection
from media_tools.bilibili.utils.naming import build_bilibili_creator_uid
from media_tools.bilibili.core.url_parser import normalize_bilibili_url, BilibiliUrlKind

parsed = normalize_bilibili_url(req.url)
if parsed.kind is BilibiliUrlKind.SPACE and parsed.mid:
    uid = build_bilibili_creator_uid(parsed.mid)
    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO creators (uid, nickname, platform, sec_user_id, sync_status) VALUES (?, ?, 'bilibili', ?, 'active')",
            (uid, uid, parsed.mid),
        )
        conn.commit()
    return {"status": "created", "creator": {"uid": uid, "nickname": uid, "sec_user_id": parsed.mid, "sync_status": "active"}}
```

If already exists, return `exists`.

- [ ] **Step 2: Update test_creators.py**

Extend existing API smoke test to ensure endpoint still returns list; add an extra call that posts a bilibili space URL and expects 200.

```python
def test_add_bilibili_creator_smoke():
    response = client.post("/api/v1/creators/", json={"url": "https://space.bilibili.com/123456"})
    assert response.status_code == 200
```

- [ ] **Step 3: Run tests**

Run:

```bash
.venv/bin/python -m pytest -q tests/api/test_creators.py
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/media_tools/api/routers/creators.py tests/api/test_creators.py
git commit -m "feat: allow adding bilibili creators"
```

---

### Task 7: Task runner supports bilibili creator download + optional transcribe

**Files:**
- Modify: `src/media_tools/api/routers/tasks.py`

- [ ] **Step 1: Add creator lookup by DB**

Add helper:

```python
def _get_creator_row(uid: str) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.execute("SELECT uid, nickname, platform, sec_user_id FROM creators WHERE uid=?", (uid,))
        row = cur.fetchone()
        return dict(row) if row else None
```

- [ ] **Step 2: Update _background_creator_download_worker to route by platform**

Pseudo structure (implement exactly in code):

```python
creator = _get_creator_row(uid)
if not creator:
    raise RuntimeError(f"Creator not found: {uid}")

platform = creator.get("platform") or "douyin"
name = creator.get("nickname") or uid

if platform == "bilibili":
    from media_tools.bilibili.core.downloader import download_up_by_url
    await _progress_fn(0.05, f"开始同步 {name} 的投稿视频（{mode}）...")
    result = await asyncio.to_thread(download_up_by_url, f"https://space.bilibili.com/{creator.get('sec_user_id')}", None, mode != "full")
else:
    (keep existing douyin logic)
```

Persist completion message exactly like existing douyin code path.

- [ ] **Step 3: Run API smoke tests**

Run:

```bash
.venv/bin/python -m pytest -q tests/api/test_tasks.py
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/media_tools/api/routers/tasks.py
git commit -m "feat: support bilibili creator download tasks"
```

---

### Task 8: Settings API supports bilibili cookie pool + frontend UI wiring

**Files:**
- Modify: `src/media_tools/api/routers/settings.py`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Add bilibili account request model**

Add:

```python
class BilibiliAccountRequest(BaseModel):
    cookie_string: str
    remark: str = ""
```

- [ ] **Step 2: Add endpoints**

Add:

```python
@router.post("/bilibili")
def add_bilibili_account(req: BilibiliAccountRequest):
    account_id = str(uuid.uuid4())
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO Accounts_Pool (account_id, platform, cookie_data, remark) VALUES (?, 'bilibili', ?, ?)",
            (account_id, req.cookie_string, req.remark),
        )
        conn.commit()
    return {"status": "success", "account_id": account_id}

@router.delete("/bilibili/{account_id}")
def delete_bilibili_account(account_id: str):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM Accounts_Pool WHERE account_id=? AND platform='bilibili'", (account_id,))
        conn.commit()
    return {"status": "success"}

@router.put("/bilibili/{account_id}/remark")
def update_bilibili_account_remark(account_id: str, req: RemarkRequest):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Accounts_Pool SET remark=? WHERE account_id=? AND platform='bilibili'", (req.remark, account_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Account not found")
        conn.commit()
    return {"status": "success"}
```

Also update `get_settings()` to return `bilibili_accounts` list.

- [ ] **Step 3: Frontend api.ts: add API calls + types**

Add functions:

```ts
export const addBilibiliAccount = async (cookieString: string, remark?: string) => {
  const response = await apiClient.post('/settings/bilibili', { cookie_string: cookieString, remark: remark || '' });
  return response.data;
};

export const deleteBilibiliAccount = async (accountId: string) => {
  const response = await apiClient.delete(`/settings/bilibili/${accountId}`);
  return response.data;
};

export const updateBilibiliAccountRemark = async (accountId: string, remark: string) => {
  const response = await apiClient.put(`/settings/bilibili/${accountId}/remark`, { remark });
  return response.data;
};
```

Extend `getSettings()` return type with `bilibili_accounts`.

- [ ] **Step 4: Settings.tsx: render a new “Bilibili 账号池” section**

Follow existing douyin/qwen section UI patterns:
- password input + remark + add button
- list rows with remark edit + delete

- [ ] **Step 5: Run tests**

Backend:

```bash
.venv/bin/python -m pytest -q tests/api/test_settings.py
```

Frontend typecheck:

```bash
cd frontend
npx tsc --noEmit
```

- [ ] **Step 6: Commit**

```bash
git add src/media_tools/api/routers/settings.py frontend/src/lib/api.ts frontend/src/pages/Settings.tsx
git commit -m "feat: add bilibili cookie pool settings"
```

---

### Task 9: Creators UI supports platform display + per-platform readiness

**Files:**
- Modify: `src/media_tools/api/routers/creators.py`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/Creators.tsx`

- [ ] **Step 1: Backend: include platform in list_creators response**

In `list_creators()` query add `c.platform` and include in GROUP BY.

- [ ] **Step 2: Frontend: extend Creator type**

Add:

```ts
platform: 'douyin' | 'bilibili';
```

- [ ] **Step 3: Creators.tsx: per creator enable/disable**

Replace global `douyinReady` gating with per creator gating:
- douyin creator requires douyinReady
- bilibili creator always enabled

Also update placeholder text to mention B 站。

- [ ] **Step 4: Run frontend typecheck**

```bash
cd frontend
npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/api/routers/creators.py frontend/src/lib/api.ts frontend/src/pages/Creators.tsx
git commit -m "feat: support bilibili creators in UI"
```

---

### Task 10: End-to-end smoke run (manual)

- [ ] **Step 1: Real extractor smoke test（只抽取，不下载）**

```bash
.venv/bin/python -m pip install -U yt-dlp
mkdir -p /tmp/bili_smoke
yt-dlp -J "https://space.bilibili.com/596133959?spm_id_from=333.1007.tianma.1-1-1.click" > /tmp/bili_smoke/up.json
.venv/bin/python -c "import json; d=json.load(open('/tmp/bili_smoke/up.json')); print('type=', d.get('_type')); print('entries=', len(d.get('entries') or [])); print('uploader=', d.get('uploader') or d.get('uploader_id'))"
```

Expected:
- `type` 为 playlist 或等价类型
- `entries` > 0
- `uploader/uploader_id` 有值

- [ ] **Step 2: Real download smoke test（只下载 1-3 条，验证 1080P 优先 + 自动降级）**

```bash
mkdir -p /tmp/bili_smoke/downloads
yt-dlp \
  -o "/tmp/bili_smoke/downloads/%(title)s__%(id)s.%(ext)s" \
  --playlist-items 1-3 \
  -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" \
  --merge-output-format mp4 \
  "https://space.bilibili.com/596133959?spm_id_from=333.1007.tianma.1-1-1.click"
ls -la /tmp/bili_smoke/downloads | head -n 20
rm -rf /tmp/bili_smoke/downloads
```

Expected:
- 产出 mp4 文件（无 Cookie 情况下，允许自动降级到可用清晰度）
- 结尾 `rm -rf /tmp/bili_smoke/downloads` 用于清理测试下载内容，避免占用磁盘

- [ ] **Step 3: Start backend + frontend**

```bash
./run.sh
```

- [ ] **Step 4: Add a bilibili UP 主（space 链接）**

Expected: Creators 列表出现该创作者（平台 bilibili）

- [ ] **Step 5: Trigger 全量同步**

Expected:
- 任务面板出现进度
- 下载目录生成 `<UP>/<合集或全部投稿>/...`

- [ ] **Step 6: Validate auto_transcribe**

Turn on Settings 的自动转写并确保 Qwen 可用，重新同步一次：
- Expected: 下载后触发转写，`transcripts/` 生成 markdown
- 建议同时开启“自动删除源视频”（`auto_delete_video=true`），确保全流程结束后不保留下载视频文件

- [ ] **Step 7: Commit any final fixes**

```bash
git status -sb
```

If needed:

```bash
git add -A
git commit -m "fix: bilibili e2e polish"
```

---

## Self-review checklist (plan completeness)

- URL 归一化、命名、平台路由、任务下载、Settings cookie、Creators UI、转写对接均有对应任务覆盖
- 所有步骤都有明确文件路径、命令与示例代码
