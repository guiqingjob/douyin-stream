# 剩余重构任务

## Phase 3: Workers 与 Pipeline 拆分

### Task 12b: transcribe/ 吞并 pipeline/ 核心
- [x] git mv pipeline/orchestrator.py → transcribe/service.py
- [x] git mv pipeline/models.py → transcribe/models.py
- [x] git mv pipeline/error_types.py → transcribe/error_types.py
- [x] git mv pipeline/helpers.py → transcribe/helpers.py
- [x] git mv pipeline/config.py → transcribe/config.py
- [x] git mv pipeline/preview.py → transcribe/preview.py
- [x] git mv pipeline/preview_backfill.py → transcribe/preview_backfill.py
- [x] 更新所有跨模块 import
- [x] 跑测试验证

### Task 13: download/ 域
- [x] 创建 download/__init__.py
- [x] 从 pipeline_worker.py 提取 DownloadWorker → download/worker.py
- [x] 从 transcribe/download_router.py 提取调度逻辑 → download/service.py
- [x] 更新 import
- [x] 跑测试验证

### Task 14: creators/ 域
- [x] 创建 creators/__init__.py
- [x] git mv repositories/creator_repository.py → creators/repository.py
- [x] git mv workers/creator_sync.py → creators/sync.py
- [x] 合并 services/ 中创作者相关业务逻辑 → creators/service.py
- [x] 更新 import

## Phase 4: 平台模块合并

### Task 15: platform/ 合并 douyin/ + bilibili/
- [x] 创建 platform/__init__.py, platform/base.py
- [x] 合并 douyin/core/ 核心逻辑 → platform/douyin.py
- [x] 合并 bilibili/core/ 核心逻辑 → platform/bilibili.py
- [x] 更新 api/routers/douyin.py 等路由 import
- [x] 跑测试验证

## Phase 5: API 路由整理

### Task 16: API 路由瘦身
- [x] 清理 api/routers/ 中过时的路由（删除 pipeline/ 相关死代码）
- [x] 统一错误响应格式（已在前期重构中完成）
- [x] 跑测试验证

## Phase 6: 配置/日志/测试/清理

### Task 17: 配置统一
- [x] 核心配置已集中到 core/config.py
- [x] 域专属配置保留在各自域（transcribe/config.py, douyin/utils/config.py）

### Task 18: 日志统一
- [x] 空 f2-trace 日志文件已删除
- [x] logs/ 目录已清理

### Task 19: 测试清理
- [x] 删除废弃测试（pipeline/ 相关）
- [x] 修复 import 路径（task_repository, transcribe_run_repository 等）
- [x] 全量测试通过（302 passed, 3 skipped）

### Task 20: 最终清理
- [x] 删除空目录（repositories/, pipeline/）
- [x] 删除未引用文件（transcribe/download_router.py）
- [x] 清理向后兼容 shim（services/__init__.py）
- [x] 验证无 import error
- [x] 全量测试通过

---

**状态：全部完成。** 当前分支 ahead of origin/main 46 commits。
