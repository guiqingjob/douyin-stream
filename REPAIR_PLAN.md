# Media Tools 修复计划

## 修复原则

- **保持所有功能不变**，只修复 bug 和改善代码结构
- 每完成一个修复项 → 测试验收 → git commit
- 从优先级 1 开始，逐步推进

---

## 优先级 1：修复当前 Bug（先解决你遇到的最痛的问题）

### 修复 1：统一配置系统

**问题**：前端设置页面的"自动转写"开关保存到 SystemSettings 表，但后端 Worker 读取的是 config.yaml，两边不同步。

**修改内容**：
1. 修改 `src/media_tools/api/routers/tasks.py`
   - `_background_creator_download_worker` 中 Bilibili 和 Douyin 分支
   - 用 `_get_global_setting_bool("auto_transcribe")` 替代 `get_config().is_auto_transcribe()`
   - 用 `_get_global_setting_bool("auto_delete")` 替代 `config.is_auto_delete_video()`

2. 修改 `_transcribe_files` 函数签名
   - 从 `config` 对象改为 `auto_delete: bool` 参数

**验收标准**：
- [ ] 在前端设置页面关闭"自动转写"
- [ ] 执行创作者同步，下载完成后**不**自动转写
- [ ] 在前端设置页面开启"自动转写"
- [ ] 执行创作者同步，下载完成后**自动**转写
- [ ] `pytest tests/ -q` 全部通过

**git commit**：`fix: 统一自动转写配置源，前端设置正确生效`

---

### 修复 2：任务中心显示转写阶段

**问题**：任务中心只显示总体进度，用户看不到当前是"下载中"还是"转写中"。

**修改内容**：

1. 后端 `src/media_tools/api/routers/tasks.py`
   - `_transcribe_files` 函数中，调用 `_progress_fn` 时传入 `stage="transcribing"`
   - `_background_creator_download_worker` 中，下载阶段传入 `stage="downloading"`

2. 后端 WebSocket 消息
   - `notify_task_update` 添加 `stage` 字段

3. 前端 `frontend/src/components/layout/TaskMonitorPanel.tsx`
   - 显示当前阶段标签（下载中 / 转写中 / 已完成）
   - 进度条上方显示阶段名称

**验收标准**：
- [ ] 创作者同步时，任务卡片显示"下载中"
- [ ] 下载完成后，任务卡片显示"转写中"
- [ ] 转写完成后，任务卡片显示"已完成"
- [ ] WebSocket 消息包含 `stage` 字段

**git commit**：`feat: 任务中心显示当前阶段（下载/转写）`

---

### 修复 3：增量同步逻辑明确化

**问题**：用户不清楚增量同步是怎么判断"新视频"的。

**修改内容**：

1. 后端 `src/media_tools/douyin/core/downloader.py`
   - `download_by_url` 的 `skip_existing` 参数逻辑
   - 记录每次同步的 `last_sync_time`

2. 后端 `src/media_tools/api/routers/tasks.py`
   - `_background_creator_download_worker` 中
   - 增量模式时，先查询 `creator.last_fetch_time`
   - 只下载该时间之后发布的视频

3. 前端 `frontend/src/pages/Creators.tsx`
   - 创作者卡片显示"上次同步：X 小时前"
   - 增量同步按钮显示"同步（新增）"

4. 数据库
   - 确保 `creators` 表有 `last_fetch_time` 字段

**验收标准**：
- [ ] 创作者卡片显示上次同步时间
- [ ] 全量同步下载所有视频
- [ ] 增量同步只下载新视频（跳过已存在的）
- [ ] 同步完成后更新 `last_fetch_time`
- [ ] 下次增量同步时，只下载上次同步之后的新视频

**git commit**：`feat: 增量同步显示上次同步时间，逻辑更清晰`

---

## 优先级 2：改善代码结构（为后续重构打基础）

### 修复 4：添加 Repository 层（Part 1：任务相关）

**目标**：把 `tasks.py` 中的数据库访问提取到 Repository。

**修改内容**：

1. 新建 `src/media_tools/repositories/__init__.py`
2. 新建 `src/media_tools/repositories/task_repository.py`

```python
class TaskRepository:
    def create(self, task_id: str, task_type: str, payload: dict) -> None:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO task_queue (task_id, task_type, status, payload, create_time, update_time) VALUES (?, ?, 'PENDING', ?, ?, ?)",
                (task_id, task_type, json.dumps(payload), now, now)
            )

    def update_progress(self, task_id: str, progress: float, message: str) -> None:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE task_queue SET progress = ?, payload = json_set(payload, '$.msg', ?), update_time = ? WHERE task_id = ?",
                (progress, message, now, task_id)
            )

    def mark_completed(self, task_id: str, message: str, result_summary: dict | None = None) -> None:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE task_queue SET status = 'COMPLETED', progress = 1.0, payload = ?, update_time = ? WHERE task_id = ?",
                (json.dumps({"msg": message, "result_summary": result_summary}), now, task_id)
            )

    def mark_failed(self, task_id: str, error: str) -> None:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE task_queue SET status = 'FAILED', error_msg = ?, update_time = ? WHERE task_id = ?",
                (error, now, task_id)
            )

    def find_by_id(self, task_id: str) -> dict | None:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_all(self) -> list[dict]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM task_queue ORDER BY update_time DESC")
            return [dict(row) for row in cursor.fetchall()]

    def delete(self, task_id: str) -> None:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM task_queue WHERE task_id = ?", (task_id,))

    def clear_history(self) -> None:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM task_queue WHERE status IN ('COMPLETED', 'FAILED')")
```

3. 修改 `src/media_tools/api/routers/tasks.py`
   - 用 `TaskRepository` 替代所有 `conn.execute(...)`

**验收标准**：
- [ ] `tasks.py` 中无 `conn.execute` 调用
- [ ] 所有任务 CRUD 操作通过 TaskRepository
- [ ] `pytest tests/ -q` 全部通过
- [ ] 任务创建/更新/完成/失败功能正常

**git commit**：`refactor: 提取 TaskRepository，集中任务数据访问`

---

### 修复 5：添加 Repository 层（Part 2：创作者相关）

**目标**：把 `creators.py` 和 `assets.py` 中的数据库访问提取到 Repository。

**修改内容**：

1. 新建 `src/media_tools/repositories/creator_repository.py`
2. 新建 `src/media_tools/repositories/asset_repository.py`

3. 修改 `src/media_tools/api/routers/creators.py`
4. 修改 `src/media_tools/api/routers/assets.py`

**验收标准**：
- [ ] `creators.py` 和 `assets.py` 中无 `conn.execute` 调用
- [ ] 创作者和素材的 CRUD 通过 Repository
- [ ] `pytest tests/ -q` 全部通过

**git commit**：`refactor: 提取 CreatorRepository 和 AssetRepository`

---

### 修复 6：拆分 tasks.py（Part 1：提取 Workers）

**目标**：把 `tasks.py` 中的后台 Worker 提取到独立模块。

**修改内容**：

1. 新建 `src/media_tools/workers/__init__.py`
2. 新建 `src/media_tools/workers/creator_sync.py`
   - 从 `tasks.py` 迁移 `_background_creator_download_worker`

3. 新建 `src/media_tools/workers/full_sync.py`
   - 从 `tasks.py` 迁移 `_background_full_sync_worker`

4. 新建 `src/media_tools/workers/pipeline.py`
   - 从 `tasks.py` 迁移 `_background_pipeline_worker` 和 `_background_batch_worker`

5. 新建 `src/media_tools/workers/local_transcribe.py`
   - 从 `tasks.py` 迁移 `_background_local_transcribe_worker`

6. 新建 `src/media_tools/workers/transcribe.py`
   - 从 `tasks.py` 迁移 `_transcribe_files`

7. 修改 `src/media_tools/api/routers/tasks.py`
   - 从各 Worker 模块导入
   - 保留 API 路由定义，业务逻辑委托给 Workers

**验收标准**：
- [ ] `tasks.py` 行数从 1735 → <500
- [ ] 所有 Worker 功能正常
- [ ] 创作者同步 / 全量同步 / 本地转写 都正常工作
- [ ] `pytest tests/ -q` 全部通过

**git commit**：`refactor: 拆分后台 Workers 到独立模块`

---

## 优先级 3：前端改善

### 修复 7：任务中心显示统计

**问题**：任务中心没有显示成功/失败数量。

**修改内容**：

1. 后端 `src/media_tools/api/routers/tasks.py`
   - 确保任务完成时 `result_summary` 包含正确的统计

2. 前端 `frontend/src/components/layout/TaskMonitorPanel.tsx`
   - 统计卡片显示：进行中 / 成功 / 失败 / 总计
   - 每个任务卡片显示 `result_summary`

**验收标准**：
- [ ] 任务完成后显示"成功 X 个，失败 Y 个"
- [ ] 统计卡片数字正确
- [ ] 前端类型检查通过

**git commit**：`feat: 任务中心显示成功/失败统计`

---

### 修复 8：拆分前端组件

**目标**：把过大的组件拆分为可维护的子组件。

**修改内容**：

1. 新建 `frontend/src/components/layout/TaskMonitorPanel/TaskStats.tsx`
2. 新建 `frontend/src/components/layout/TaskMonitorPanel/TaskFilterTabs.tsx`
3. 新建 `frontend/src/components/layout/TaskMonitorPanel/TaskList.tsx`
4. 新建 `frontend/src/components/layout/TaskMonitorPanel/TaskItem.tsx`

5. 修改 `frontend/src/components/layout/TaskMonitorPanel/index.tsx`
   - 从 521 行 → ~100 行

**验收标准**：
- [ ] 每个子组件 <200 行
- [ ] TaskMonitorPanel 功能不变
- [ ] `npx tsc --noEmit` 通过

**git commit**：`refactor: 拆分 TaskMonitorPanel 为子组件`

---

## 优先级 4：可维护性

### 修复 9：添加集成测试

**目标**：测试完整的用户工作流。

**修改内容**：

1. 新建 `tests/integration/test_creator_sync.py`

```python
import pytest
import sqlite3

class TestCreatorSync:
    def test_full_sync_downloads_all_videos(self, test_db):
        """全量同步下载所有视频"""
        pass

    def test_incremental_sync_downloads_only_new(self, test_db):
        """增量同步只下载新视频"""
        pass

    def test_auto_transcribe_runs_after_download(self, test_db):
        """开启自动转写时，下载完成后自动转写"""
        pass

    def test_task_progress_updates_correctly(self, test_db):
        """任务进度正确更新"""
        pass
```

2. 新建 `tests/integration/test_local_transcribe.py`

**验收标准**：
- [ ] 至少 5 个集成测试通过
- [ ] `pytest tests/integration/ -v` 输出详细结果

**git commit**：`test: 添加集成测试，覆盖核心工作流`

---

### 修复 10：统一错误处理

**目标**：前后端错误处理一致。

**修改内容**：

1. 后端 `src/media_tools/api/app.py`
   - 添加全局异常处理中间件
   - AppError 返回结构化错误
   - 未知异常返回通用错误

2. 前端 `frontend/src/lib/api.ts`
   - 统一错误处理
   - 显示用户友好的错误消息

**验收标准**：
- [ ] 后端错误返回 `{code, message, details}` 格式
- [ ] 前端正确显示错误信息
- [ ] 不暴露内部敏感信息

**git commit**：`feat: 统一前后端错误处理`

---

## 执行顺序

```
Week 1: 修复 1 + 修复 2 + 修复 3
        （先解决你最痛的问题：自动转写 + 任务显示）

Week 2: 修复 4 + 修复 5 + 修复 6
        （代码结构改善：Repository + Workers 拆分）

Week 3: 修复 7 + 修复 8 + 修复 9 + 修复 10
        （前端改善 + 测试 + 错误处理）
```

---

## 每步验收流程

1. **修改代码**
2. **运行测试**：`pytest tests/ -q`
3. **运行后端**：`./run.sh backend`
4. **手动验证**：打开浏览器测试功能
5. **git commit**
6. **下一步**

---

## 回滚策略

如果某步出问题：
1. `git log` 找到上一步的 commit hash
2. `git revert <hash>` 回滚
3. 或者 `git checkout <hash>` 回到上一步
4. 修复问题后继续
