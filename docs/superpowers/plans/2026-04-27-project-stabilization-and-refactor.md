# Project Stabilization & Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让项目恢复“可控、可预测、可扩展”的状态：关键链路稳定、并发/配置一致、重复实现收敛、可观测性与测试覆盖到位。

**Architecture:** 以“稳定优先”的方式做增量重构：先统一配置与任务边界（API→Service→Worker→Pipeline→Transcribe），然后把高风险同步 IO 从 API 移到后台，最后清理重复/死代码并补齐集成测试。

**Tech Stack:** FastAPI, sqlite3, asyncio, pytest, requests（Qwen 纯 API）, 前端 React（仅做必要适配）

---

## 现状问题（用来校准目标）

- 并发与配置来源不统一：Pipeline 读 env，Settings 写 DB，导致“我以为并发=10，实际=1”
- 关键链路缺少“可回滚/可清理”策略：上传/转写失败时残留 Qwen record
- Router 做太多重活（磁盘扫描/长耗时 IO），导致偶发卡顿被当成 bug
- 重复实现/死代码残留：同一职责多处实现，修 bug 时容易遗漏路径
- 测试更多是单元层，缺少关键链路的契约/集成验证

---

## 交付标准（Definition of Done）

- Settings 页面里的 concurrency 能明确控制“转写并发”，且有测试覆盖
- `/tasks/transcribe/creator` 返回迅速，不会因磁盘扫描阻塞
- 单文件失败可 best-effort 清理：OSS 分片 + Qwen record（符合“失败不留脏数据”）
- 删除重复/死代码后：全量测试通过、核心链路手动验证通过、无明显回归

---

## 任务拆分

### Task 1: 统一并发配置来源（Settings 为准）

**Files:**
- Modify: [core/config.py](file:///Users/gq/Projects/media-tools/src/media_tools/core/config.py)
- Modify: [test_local_transcribe_concurrency.py](file:///Users/gq/Projects/media-tools/tests/test_local_transcribe_concurrency.py)

- [ ] **Step 1: 写一个失败的测试（Settings 并发会影响 PipelineConfig.concurrency）**

```python
def test_pipeline_config_concurrency_uses_system_settings(monkeypatch, tmp_path) -> None:
    import sqlite3
    from contextlib import contextmanager
    from media_tools.pipeline.config import load_pipeline_config

    conn = sqlite3.connect(str(tmp_path / "settings.db"))
    conn.execute("CREATE TABLE SystemSettings (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO SystemSettings (key, value) VALUES ('concurrency', '3')")
    conn.commit()

    @contextmanager
    def _get_conn():
        yield conn

    monkeypatch.setattr("media_tools.core.config.get_db_connection", _get_conn)
    monkeypatch.delenv("PIPELINE_CONCURRENCY", raising=False)
    assert load_pipeline_config().concurrency == 3
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest -q tests/test_local_transcribe_concurrency.py::test_pipeline_config_concurrency_uses_system_settings -q`
Expected: FAIL（实际仍为默认值/环境值）

- [ ] **Step 3: 最小实现（env 可覆盖，默认读 SystemSettings）**

```python
    @property
    def concurrency(self) -> int:
        if self._concurrency is not None:
            return self._concurrency
        env_value = os.environ.get("PIPELINE_CONCURRENCY", "").strip()
        if env_value:
            return int(env_value)
        return get_runtime_setting_int("concurrency", 10)
```

- [ ] **Step 4: 运行全量测试**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/core/config.py tests/test_local_transcribe_concurrency.py
git commit -m "fix(config): use settings concurrency for pipeline"
```

---

### Task 2: /transcribe/creator 改为后台扫描（消除 API 阻塞）

**Files:**
- Modify: [tasks.py](file:///Users/gq/Projects/media-tools/src/media_tools/api/routers/tasks.py)
- Create: [creator_transcribe_worker.py](file:///Users/gq/Projects/media-tools/src/media_tools/workers/creator_transcribe_worker.py)
- Modify: [task_repository.py](file:///Users/gq/Projects/media-tools/src/media_tools/repositories/task_repository.py)
- Test: `tests/test_creator_transcribe_submit_returns.py`

- [ ] **Step 1: 写失败测试（接口立即返回 task_id 并注册后台协程）**

```python
def test_creator_transcribe_submits_background_task(monkeypatch) -> None:
    from media_tools.api.routers import tasks as tasks_router
    import asyncio

    created = {}

    async def _fake_create_task(task_id: str, task_type: str, request_params: dict):
        created["task_type"] = task_type

    async def _fake_bg(task_id: str, uid: str):
        created["bg_uid"] = uid

    def _fake_register(task_id: str, coro):
        created["registered"] = True
        created["coro"] = coro

    monkeypatch.setattr(tasks_router, "_create_task", _fake_create_task)
    monkeypatch.setattr(tasks_router, "_register_background_task", _fake_register)
    monkeypatch.setattr("media_tools.workers.creator_transcribe_worker.background_creator_transcribe_worker", _fake_bg)

    req = tasks_router.CreatorTranscribeRequest(uid="u1")
    result = asyncio.run(tasks_router.trigger_creator_transcribe(req))
    assert result["status"] == "started"
    assert created["task_type"] == "local_transcribe"
    asyncio.run(created["coro"])
    assert created["bg_uid"] == "u1"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest -q tests/test_creator_transcribe_submit_returns.py -q`
Expected: FAIL（因为当前实现还在路由里扫盘）

- [ ] **Step 3: 最小实现**
  - 路由只做：创建任务 + 注册后台 worker + 返回 task_id
  - worker 才做：扫描 DB/磁盘、补齐 DB、调用 local_transcribe

- [ ] **Step 4: 跑全量测试**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/api/routers/tasks.py src/media_tools/workers/creator_transcribe_worker.py src/media_tools/repositories/task_repository.py tests/test_creator_transcribe_submit_returns.py
git commit -m "perf(tasks): move creator scan to background"
```

---

### Task 3: 失败自动清理 Qwen record（best-effort）

**Goal:** 满足“上传/转写中间失败不留脏记录”的期望。

**Files:**
- Modify: [flow.py](file:///Users/gq/Projects/media-tools/src/media_tools/transcribe/flow.py)
- Test: `tests/test_qwen_cleanup_on_failure.py`（新增）

- [ ] **Step 1: 写失败测试（模拟 start 失败时会调用 delete_record）**

```python
import asyncio
from pathlib import Path

def test_run_real_flow_deletes_record_on_failure(monkeypatch, tmp_path):
    from media_tools.transcribe.flow import run_real_flow

    called = {"deleted": False}

    class _Api:
        async def dispose(self): ...

    async def _fake_api_json(api, url, payload, headers=None):
        if "oss/token/get" in url:
            return {"data": {"genRecordId":"g","recordId":"r","getLink":"u","sts":{"bucket":"b","endpoint":"e","fileKey":"k","accessKeyId":"i","accessKeySecret":"s","securityToken":"t"}}}
        if "record/start" in url:
            raise RuntimeError("boom")
        return {"data": {}}

    async def _fake_upload(*args, **kwargs): 
        return

    async def _fake_delete(api, record_ids):
        called["deleted"] = True
        return True

    monkeypatch.setattr("media_tools.transcribe.flow.api_json", _fake_api_json)
    monkeypatch.setattr("media_tools.transcribe.flow.upload_file_to_oss", _fake_upload)
    monkeypatch.setattr("media_tools.transcribe.flow.delete_record", _fake_delete)
    monkeypatch.setattr("media_tools.transcribe.flow.RequestsApiContext", lambda cookie_string: _Api())
    monkeypatch.setattr("media_tools.transcribe.flow.get_quota_snapshot", lambda **kwargs: asyncio.sleep(0, result=type("Q",(),{"remaining_upload":0,"total_upload":0})()))
    monkeypatch.setattr("media_tools.transcribe.flow.resolve_qwen_cookie_string", lambda **kwargs: "c")

    p = tmp_path / "a.mp4"
    p.write_bytes(b"0"*1024)
    try:
        asyncio.run(run_real_flow(file_path=p, auth_state_path="x", download_dir=tmp_path, export_config=type("E",(),{"file_type":"md","label":"md"})(), should_delete=True))
    except RuntimeError:
        pass
    assert called["deleted"] is True
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest -q tests/test_qwen_cleanup_on_failure.py -q`
Expected: FAIL（当前失败路径不清理 record）

- [ ] **Step 3: 最小实现**
  - 在 `run_real_flow` 内部保存 `recordId`，在异常分支 best-effort 调 `delete_record`
  - 不打印 cookie/敏感信息

- [ ] **Step 4: 跑全量测试**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/media_tools/transcribe/flow.py tests/test_qwen_cleanup_on_failure.py
git commit -m "fix(transcribe): cleanup qwen record on failure"
```

---

### Task 4: 配置/职责收敛与死代码清理（持续进行）

**Files:**
- Delete（确认无引用后）：`src/media_tools/services/task_service.py`, `src/media_tools/services/task_utils.py` 等
- Modify：引用方（router/scheduler/app）统一调用 task_ops/repository

- [ ] **Step 1: grep 全仓确认无引用**
Run: `rg "task_service|task_utils" -n src`
Expected: 0 matches

- [ ] **Step 2: 删除文件**
- [ ] **Step 3: 全量测试**
- [ ] **Step 4: Commit（chore/refactor）**

---

## 执行策略（强烈建议）

- 每个任务都按 TDD：先写失败测试 → 最小实现 → 全量测试 → 小步提交
- 每次只动一个“职责面”，不要跨层大改
- 每完成 1 个任务就手动跑一次关键链路（最少：单文件转写、博主批量转写、下载后转写）

