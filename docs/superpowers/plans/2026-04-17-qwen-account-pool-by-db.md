# Qwen Account Pool (DB-Backed) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Qwen 账号池以 DB `Accounts_Pool(platform='qwen')` 为唯一来源，并实现：账号列表展示剩余小时、转写按剩余小时优先用号、手动/定时领取遍历 DB 全账号、Cookie 过期标记失效且可更新恢复。

**Architecture:** 后端为每个 DB 账号维护独立 `auth_state_path`（storageState 文件）；`/settings/qwen/status` 与 `/settings/qwen/claim` 改为从 DB 账号池枚举账号；Pipeline 转写阶段改为按账号池顺序尝试不同 `auth_state_path`（优先剩余小时）；前端 Settings 页把额度展示合并进账号列表（只显示剩余小时）。

**Tech Stack:** FastAPI + sqlite3（后端），Playwright request API（抓额度/领取），React + TypeScript（前端），pytest（测试）。

---

## File Map

**Backend**
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/db/core.py](file:///Users/gq/Projects/media-tools/src/media_tools/db/core.py)
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/api/routers/settings.py](file:///Users/gq/Projects/media-tools/src/media_tools/api/routers/settings.py)
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/api/routers/scheduler.py](file:///Users/gq/Projects/media-tools/src/media_tools/api/routers/scheduler.py)
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/pipeline/orchestrator_v2.py](file:///Users/gq/Projects/media-tools/src/media_tools/pipeline/orchestrator_v2.py)
- Create: `/Users/gq/Projects/media-tools/src/media_tools/transcribe/db_account_pool.py`
- Test: `/Users/gq/Projects/media-tools/tests/test_qwen_account_pool_db.py`

**Frontend**
- Modify: [/Users/gq/Projects/media-tools/frontend/src/pages/Settings.tsx](file:///Users/gq/Projects/media-tools/frontend/src/pages/Settings.tsx)
- Modify: [/Users/gq/Projects/media-tools/frontend/src/lib/api.ts](file:///Users/gq/Projects/media-tools/frontend/src/lib/api.ts)

---

### Task 1: DB Schema Add `auth_state_path` for Accounts_Pool

**Files:**
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/db/core.py](file:///Users/gq/Projects/media-tools/src/media_tools/db/core.py)
- Create: `/Users/gq/Projects/media-tools/tests/test_qwen_account_pool_db.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_qwen_account_pool_db.py`:

```python
from __future__ import annotations

import sqlite3


def test_db_init_adds_accounts_pool_auth_state_path(tmp_path) -> None:
    from media_tools.db.core import init_db

    db_path = tmp_path / "t.db"
    init_db(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cols = [row[1] for row in conn.execute("PRAGMA table_info(Accounts_Pool)").fetchall()]
    assert "auth_state_path" in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest -q tests/test_qwen_account_pool_db.py::test_db_init_adds_accounts_pool_auth_state_path
```

Expected: FAIL（列不存在）

- [ ] **Step 3: Implement migration**

In `init_db(...)` add:

```python
_ensure_column(conn, "Accounts_Pool", "auth_state_path", "TEXT DEFAULT ''")
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest -q tests/test_qwen_account_pool_db.py::test_db_init_adds_accounts_pool_auth_state_path
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/db/core.py tests/test_qwen_account_pool_db.py
git commit -m "feat(db): add auth_state_path to qwen accounts pool"
```

---

### Task 2: Add DB Account Pool Helper Module

**Files:**
- Create: `/Users/gq/Projects/media-tools/src/media_tools/transcribe/db_account_pool.py`
- Test: `/Users/gq/Projects/media-tools/tests/test_qwen_account_pool_db.py`

- [ ] **Step 1: Write failing test (compute auth_state_path)**

Append to `tests/test_qwen_account_pool_db.py`:

```python
def test_build_qwen_auth_state_path_for_account() -> None:
    from media_tools.transcribe.db_account_pool import build_qwen_auth_state_path_for_account

    p = build_qwen_auth_state_path_for_account("abc123")
    assert p.name == "qwen-storage-state-abc123.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest -q tests/test_qwen_account_pool_db.py::test_build_qwen_auth_state_path_for_account
```

Expected: FAIL（模块不存在）

- [ ] **Step 3: Implement minimal helper**

Create `src/media_tools/transcribe/db_account_pool.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import sqlite3

from media_tools.db.core import get_db_connection
from media_tools.transcribe.quota import get_daily_quota_record, has_claimed_equity_today


@dataclass(frozen=True, slots=True)
class DbQwenAccount:
    account_id: str
    remark: str
    status: str
    cookie_data: str
    auth_state_path: str


def build_qwen_auth_state_path_for_account(account_id: str) -> Path:
    safe = str(account_id).strip()
    return Path(".auth") / f"qwen-storage-state-{safe}.json"


def load_qwen_accounts_from_db() -> list[DbQwenAccount]:
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT account_id, remark, status, cookie_data, auth_state_path FROM Accounts_Pool WHERE platform='qwen'",
        ).fetchall()
    accounts: list[DbQwenAccount] = []
    for row in rows:
        accounts.append(
            DbQwenAccount(
                account_id=str(row["account_id"]),
                remark=str(row["remark"] or ""),
                status=str(row["status"] or "active"),
                cookie_data=str(row["cookie_data"] or ""),
                auth_state_path=str(row["auth_state_path"] or ""),
            )
        )
    return accounts
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest -q tests/test_qwen_account_pool_db.py::test_build_qwen_auth_state_path_for_account
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/transcribe/db_account_pool.py tests/test_qwen_account_pool_db.py
git commit -m "feat(qwen): add db account pool helpers"
```

---

### Task 3: Store Per-Account StorageState When Adding/Updating Qwen Accounts

**Files:**
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/api/routers/settings.py](file:///Users/gq/Projects/media-tools/src/media_tools/api/routers/settings.py)
- Modify: `/Users/gq/Projects/media-tools/src/media_tools/transcribe/db_account_pool.py`
- Test: `/Users/gq/Projects/media-tools/tests/test_qwen_account_pool_db.py`

- [ ] **Step 1: Write failing test (add account writes auth_state_path column)**

Append:

```python
def test_add_qwen_account_sets_auth_state_path(monkeypatch) -> None:
    import sqlite3
    from media_tools.api.routers import settings as settings_router

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE Accounts_Pool(account_id TEXT PRIMARY KEY, platform TEXT, cookie_data TEXT, remark TEXT, status TEXT DEFAULT 'active', auth_state_path TEXT DEFAULT '')"
    )
    conn.commit()
    monkeypatch.setattr("media_tools.api.routers.settings.get_db_connection", lambda: conn)

    called = {}
    def _fake_save(cookie_string: str, auth_state_path, **kwargs):  # noqa: ANN001
        called["auth_state_path"] = str(auth_state_path)
        return {}
    monkeypatch.setattr("media_tools.api.routers.settings.save_qwen_cookie_string", _fake_save)

    req = settings_router.QwenAccountRequest(cookie_string="x=y", remark="r")
    result = settings_router.add_qwen_account(req)
    account_id = result["account_id"]
    row = conn.execute("SELECT auth_state_path FROM Accounts_Pool WHERE account_id=?", (account_id,)).fetchone()
    assert row is not None
    assert row[0]
    assert "qwen-storage-state-" in row[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest -q tests/test_qwen_account_pool_db.py::test_add_qwen_account_sets_auth_state_path
```

Expected: FAIL（当前实现会写默认 auth_state 且不写 auth_state_path）

- [ ] **Step 3: Implement**

In `settings.py`:
- In `add_qwen_account`:
  - Generate `account_id = uuid.uuid4()`
  - Build `auth_state_path = build_qwen_auth_state_path_for_account(account_id)`
  - Call `save_qwen_cookie_string(req.cookie_string, auth_state_path, sync_db=False)`
  - Insert into Accounts_Pool including `auth_state_path`
- Add a new endpoint to update cookie:
  - `PUT /settings/qwen/accounts/{account_id}/cookie`
  - Body: `{ cookie_string: str }`
  - Load row, reuse existing `auth_state_path` (or build if empty), save cookie, set status='active'

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest -q tests/test_qwen_account_pool_db.py::test_add_qwen_account_sets_auth_state_path
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/api/routers/settings.py src/media_tools/transcribe/db_account_pool.py tests/test_qwen_account_pool_db.py
git commit -m "feat(settings): persist per-account qwen auth state"
```

---

### Task 4: Make `/settings/qwen/status` Use DB Account Pool and Return Remaining Hours

**Files:**
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/api/routers/settings.py](file:///Users/gq/Projects/media-tools/src/media_tools/api/routers/settings.py)
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/transcribe/quota.py](file:///Users/gq/Projects/media-tools/src/media_tools/transcribe/quota.py)
- Test: `/Users/gq/Projects/media-tools/tests/test_qwen_account_pool_db.py`

- [ ] **Step 1: Write failing test (status returns remaining_hours per DB account)**

Append:

```python
def test_qwen_status_returns_remaining_hours_from_db(monkeypatch) -> None:
    import sqlite3
    import asyncio
    from media_tools.api.routers import settings as settings_router

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE Accounts_Pool(account_id TEXT PRIMARY KEY, platform TEXT, cookie_data TEXT, remark TEXT, status TEXT DEFAULT 'active', auth_state_path TEXT DEFAULT '')"
    )
    conn.execute(
        "INSERT INTO Accounts_Pool(account_id, platform, cookie_data, remark, status, auth_state_path) VALUES(?,?,?,?,?,?)",
        ("a1", "qwen", "x=y", "r", "active", ".auth/qwen-storage-state-a1.json"),
    )
    conn.commit()
    monkeypatch.setattr("media_tools.api.routers.settings.get_db_connection", lambda: conn)

    async def _fake_get_snapshot(*, auth_state_path, referer=""):  # noqa: ANN001
        class _S:
            remaining_upload = 60 * 375
            used_upload = 0
            total_upload = 0
            raw = {}
            gratis_upload = False
            free = True
        return _S()
    monkeypatch.setattr("media_tools.api.routers.settings.get_quota_snapshot", _fake_get_snapshot)

    result = asyncio.run(settings_router.get_qwen_status())
    assert result["status"] == "success"
    assert result["accounts"][0]["remaining_hours"] == 375
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest -q tests/test_qwen_account_pool_db.py::test_qwen_status_returns_remaining_hours_from_db
```

Expected: FAIL（当前 status 走 accounts.json）

- [ ] **Step 3: Implement remaining_hours**

In `quota.py`, add helper:

```python
def remaining_hours_from_snapshot(snapshot: QuotaSnapshot) -> int:
    return max(0, number_value(snapshot.remaining_upload) // 60)
```

In `settings.py /get_qwen_status`:
- Load DB accounts (`load_qwen_accounts_from_db`)
- For each account with status != 'active': return remaining_hours=0 and mark status
- For active: call `get_quota_snapshot(auth_state_path=Path(auth_state_path))`
- Return `remaining_hours` via helper and include `accountLabel` = remark or account_id

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest -q tests/test_qwen_account_pool_db.py::test_qwen_status_returns_remaining_hours_from_db
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/api/routers/settings.py src/media_tools/transcribe/quota.py tests/test_qwen_account_pool_db.py
git commit -m "feat(qwen): show remaining hours for db account pool"
```

---

### Task 5: Make `/settings/qwen/claim` Use DB Account Pool (All Accounts)

**Files:**
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/api/routers/settings.py](file:///Users/gq/Projects/media-tools/src/media_tools/api/routers/settings.py)
- Test: `/Users/gq/Projects/media-tools/tests/test_qwen_account_pool_db.py`

- [ ] **Step 1: Write failing test (claim iterates db accounts)**

Append:

```python
def test_qwen_claim_iterates_db_accounts(monkeypatch) -> None:
    import sqlite3
    import asyncio
    from media_tools.api.routers import settings as settings_router

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE Accounts_Pool(account_id TEXT PRIMARY KEY, platform TEXT, cookie_data TEXT, remark TEXT, status TEXT DEFAULT 'active', auth_state_path TEXT DEFAULT '')"
    )
    conn.execute(
        "INSERT INTO Accounts_Pool(account_id, platform, cookie_data, remark, status, auth_state_path) VALUES(?,?,?,?,?,?)",
        ("a1", "qwen", "x=y", "r", "active", ".auth/qwen-storage-state-a1.json"),
    )
    conn.commit()
    monkeypatch.setattr("media_tools.api.routers.settings.get_db_connection", lambda: conn)

    monkeypatch.setattr("media_tools.api.routers.settings.has_claimed_equity_today", lambda account_id: False)

    called = {"count": 0}
    async def _fake_claim(*, account_id, auth_state_path):  # noqa: ANN001
        called["count"] += 1
        class _R:
            claimed = True
            skipped = False
            reason = ""
        return _R()
    monkeypatch.setattr("media_tools.api.routers.settings.claim_equity_quota", _fake_claim)

    result = asyncio.run(settings_router.claim_qwen_quota_endpoint())
    assert result["status"] == "success"
    assert called["count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest -q tests/test_qwen_account_pool_db.py::test_qwen_claim_iterates_db_accounts
```

Expected: FAIL（当前 claim 走 resolve_status_targets）

- [ ] **Step 3: Implement**

In `settings.py` `claim_qwen_quota_endpoint`:
- Replace `resolve_status_targets()` with DB accounts iteration.
- Use each account's `account_id` and `auth_state_path`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest -q tests/test_qwen_account_pool_db.py::test_qwen_claim_iterates_db_accounts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/api/routers/settings.py tests/test_qwen_account_pool_db.py
git commit -m "feat(qwen): claim quota for db account pool"
```

---

### Task 6: Update Scheduler Auto-Claim to Use DB Account Pool

**Files:**
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/api/routers/scheduler.py](file:///Users/gq/Projects/media-tools/src/media_tools/api/routers/scheduler.py)

- [ ] **Step 1: Implement**

Replace `resolve_status_targets()` usage with:
- `from media_tools.transcribe.db_account_pool import load_qwen_accounts_from_db`
- Iterate active accounts, call `has_claimed_equity_today(account_id)` then `claim_equity_quota(account_id=..., auth_state_path=...)`

- [ ] **Step 2: Manual verification**

Start backend and check log at startup (job registered), then manually invoke the function by temporarily calling it in a REPL if needed.

- [ ] **Step 3: Commit**

```bash
git add src/media_tools/api/routers/scheduler.py
git commit -m "feat(scheduler): auto-claim qwen quota from db pool"
```

---

### Task 7: Pipeline Uses DB Account Pool and Prefers Higher Remaining Hours

**Files:**
- Modify: [/Users/gq/Projects/media-tools/src/media_tools/pipeline/orchestrator_v2.py](file:///Users/gq/Projects/media-tools/src/media_tools/pipeline/orchestrator_v2.py)
- Test: `/Users/gq/Projects/media-tools/tests/test_qwen_account_pool_db.py`

- [ ] **Step 1: Write failing test (orchestrator tries multiple auth_state_path)**

Append:

```python
def test_orchestrator_tries_multiple_qwen_accounts(monkeypatch, tmp_path) -> None:
    import asyncio
    from pathlib import Path
    from media_tools.pipeline.orchestrator_v2 import OrchestratorV2
    from media_tools.pipeline.config import PipelineConfig

    class _AuthErr(Exception):
        pass

    calls: list[str] = []
    async def _fake_run_real_flow(*, file_path, auth_state_path, **kwargs):  # noqa: ANN001
        calls.append(str(auth_state_path))
        if len(calls) == 1:
            raise _AuthErr("401 unauthorized")
        class _R:
            export_path = tmp_path / "o.md"
            record_id = "r"
            gen_record_id = "g"
            remote_deleted = True
        return _R()

    monkeypatch.setattr("media_tools.pipeline.orchestrator_v2.run_real_flow", _fake_run_real_flow)

    cfg = PipelineConfig(account_id="")
    orch = OrchestratorV2(config=cfg, auth_state_path=Path("dummy.json"))

    # monkeypatch a resolver on orchestrator to return two accounts
    orch._resolve_qwen_execution_accounts = lambda: [  # type: ignore[attr-defined]
        {"account_id": "a1", "auth_state_path": Path("a1.json")},
        {"account_id": "a2", "auth_state_path": Path("a2.json")},
    ]

    p = tmp_path / "a.mp3"
    p.write_bytes(b"ok")
    result = asyncio.run(orch._transcribe_single_video(p))
    assert result.success is True
    assert calls == ["a1.json", "a2.json"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest -q tests/test_qwen_account_pool_db.py::test_orchestrator_tries_multiple_qwen_accounts
```

Expected: FAIL（当前 orchestrator 只用单一 auth_state_path）

- [ ] **Step 3: Implement minimal**

In `OrchestratorV2`:
- Add a method `_resolve_qwen_execution_accounts()` default implementation that loads DB accounts and orders them by remaining_hours (from last quota record), then returns list of dicts `{account_id, auth_state_path}`.
- In `_transcribe_single_video`, instead of calling `run_real_flow` once with `self.auth_state_path`, wrap with loop:
  - for each candidate:
    - call `run_real_flow(... auth_state_path=candidate_path, account_id=candidate_id)`
    - on auth error: mark DB status invalid and continue
    - on success: mark_account_success(candidate_id) and return

Auth error detection:
- Use existing `classify_error` result == `ErrorType.AUTH` (string matching covers 401/403/unauthorized) OR catch `AuthenticationRequiredError` if present.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest -q tests/test_qwen_account_pool_db.py::test_orchestrator_tries_multiple_qwen_accounts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/pipeline/orchestrator_v2.py tests/test_qwen_account_pool_db.py
git commit -m "feat(pipeline): use qwen db account pool for transcribe"
```

---

### Task 8: Frontend Settings Show Remaining Hours in Qwen Account Rows

**Files:**
- Modify: [/Users/gq/Projects/media-tools/frontend/src/pages/Settings.tsx](file:///Users/gq/Projects/media-tools/frontend/src/pages/Settings.tsx)
- Modify: [/Users/gq/Projects/media-tools/frontend/src/lib/api.ts](file:///Users/gq/Projects/media-tools/frontend/src/lib/api.ts)

- [ ] **Step 1: Update `getQwenStatus` typing**

Adjust the shape to include:

```ts
accounts: Array<{ accountId: string; accountLabel?: string; remaining_hours: number; status: string }>
```

- [ ] **Step 2: Merge status into qwen account list UI**

In Settings page:
- Build a map from `accountId -> remaining_hours/status`
- In each row of `settings.qwen_accounts`, show a small right-side mono text: `剩余 {hours} 小时` (or `--` if unknown)
- Remove/minimize the separate "转写额度" card block (or keep but empty), since you want it in list.

- [ ] **Step 3: Build frontend**

Run:

```bash
cd frontend && npm run build
```

Expected: build success

- [ ] **Step 4: Commit in frontend repo**

```bash
cd frontend
git add src/pages/Settings.tsx src/lib/api.ts
git commit -m "feat(settings): show qwen remaining hours in account list"
cd ..
git add frontend
git commit -m "chore: update frontend"
```

---

### Task 9: Full Test Run

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

