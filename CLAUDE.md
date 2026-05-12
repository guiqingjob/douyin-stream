# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目性质

单机本地 Web 工作站：抖音/B站批量下载 → 通义千问云端转写 → 本地阅读管理。**没有部署、没有团队、没有 SLA** —— 不要套用"生产服务"的工程标准（CI/CD、Docker、覆盖率门槛在这里都是负收益）。优先级永远是**业务可靠性 > 工程规范**。

> **文档状态(2026-05-12)**：本文档经过多轮代码迭代后存在过时点，已做两轮事实校准（标注 *2026-05-11* / *2026-05-12 修订*）。仍然可能漂移的部分以代码 + `git log` 为最终依据，本文档只做"心智模型导航"。
> 已知历史描述与实际不符的点：
> - DDD/领域驱动架构那一节描述的是**当时的设计意图**，并非现状全貌。`presentation/api/v2/` 路由的 cancel/cleanup/progress 都没接通 worker 协程，**已在 2026-05-12 暂时撤掉 app.py 的 v2_router include**（等真要切换到 v2 时再恢复）。`migration/__init__.py` 工厂存在但只被 v2 路由用，旧服务并未接入。**新功能要选这条路前先确认 v2 已补全**。
> - 前端苹果设计风格那一节是阶段性记录，遇到不一致以前端代码为准。

## 常用命令

```bash
./run.sh                # 同时启动后端 (8000) 和前端 (5173)
./run.sh backend        # 只启后端
./run.sh frontend       # 只启前端
./run.sh build          # 前端生产构建到 frontend/dist/
```

> README/CONTRIBUTING 里写的 `./run.sh setup` 和 `./run.sh test` **并不存在**，是文档残留。下面是真命令。

```bash
# 测试（pyproject.toml 已配 pythonpath=src, testpaths=tests）
pytest                                              # 全量
pytest tests/test_flow_resume.py                    # 单文件
pytest tests/test_flow_resume.py::test_xxx          # 单用例
pytest -k "transcribe and resume"                   # 关键字过滤
pytest -x --ff                                      # 失败立刻停 + 上次失败的先跑

# Lint（无 CI，但 ruff 已在 .ruff_cache 中用过）
ruff check src/
ruff format src/

# 前端
cd frontend && npm run dev
cd frontend && npm run build
cd frontend && npm run lint
cd frontend && npx vitest                           # 前端测试（vitest.config.ts 已配）
```

后端入口：`PYTHONPATH=src python -m uvicorn media_tools.api.app:app --reload`。

## 架构核心（必须先理解）

### 真相源分层
1. **业务真相源** = `data/media_tools.db`（SQLite, WAL）。`media_assets` 表的 `transcript_status` / `download_status` 才决定业务是否完成；任务（`task_queue`）只是"一次执行尝试"。
2. **运行时配置真相源** = `SystemSettings` 表（KV）。`auto_transcribe`、`auto_delete`、`api_key`、`export_format` 全在这里，**不要回去读 `config.yaml`**。`config.yaml` 只剩 `cookie` / `download_path` / `naming` 这种启动期常量。
3. **并发控制**（多层 gate，谁是瓶颈看场景）：
   - `config.concurrency`：进 `transcribe_batch` 时再套一层 `asyncio.Semaphore`（orchestrator.py 末尾）。这个值在 `run_pipeline_for_user` / `run_batch_pipeline` 路径上**真实生效**。`run_local_transcribe` 不走 batch，直接用它作为协程并发上限。
   - **入口闸门** `_effective_concurrency = 2 * n_accounts`：由 `_adjust_gates_to_account_pool()` 在账号池初始化后设置，跟随账号数量自动伸缩。
   - **上传互斥** `_upload_locks: dict[str, asyncio.Lock]`：per-account 上传锁。Qwen 平台约束同账号同时只允许 1 个文件上传，多余请求服务端会隐式排队；客户端用 Lock 显式串行，避免占额度空等。`AccountPool` 已去掉余额加权随机，纯轮询 + 排除集。
   - **导出不限流**：export/download 阶段取消 Semaphore，平台无明显并发约束。
4. **转写阶段真相源** = `transcribe_runs` 表（2026-05 新加）。每行 = 某 asset 在某账号上的一次完整尝试，stage 推进序：`queued → uploaded → transcribing → exporting → downloading → saved`。

### 重构脉络
[docs/pipeline_reliability_refactor.md](docs/pipeline_reliability_refactor.md) 是 pipeline 改造的完整设计文档，**第一到第四阶段全部落地（2026-05-05）**：视频级状态治理 → 可恢复转写流水线 → 可观测性（失败聚合 / 健康检查 / PARTIAL_FAILED / 日志归档）。改 pipeline / orchestrator / transcribe 前必读，尤其是第 156-189 行的"Phase 3 已完成机制"——续传不变量在那里。

### 续传 fast-path（重要不变量）
`find_resumable(asset_id, account_id)` 命中条件：`gen_record_id` 已持久化，且 stage ∈ RESUMABLE_STAGES，**或** stage='failed' 但 `error_stage` ∈ RESUMABLE_STAGES（同时 error_type 不能是 `service_unavailable` / `unsupported_format` 这类已是云端终态的）。命中后：
- 已有 `export_url` → 直接 download，**0 调用 Qwen**
- 已有 `gen_record_id` → 跳过上传，从 `poll_until_done` 继续
- **不支持跨账号续传**（Qwen 的 `genRecordId` 与账号绑定）
- **续传失败回退**（2026-05-11 修订）：resume 分支抛异常时,先 `await delete_record(api, [old_record_id])` 把云端旧记录清掉,再 `update_stage(run_id, "queued")`,最后让 `_do_flow` 接管。否则 `_do_flow` 会拿新 token 覆盖 `gen_record_id`,旧记录变成 Qwen 端孤儿(额度已扣)。
- state.json 文件已**按 task_id 隔离**(2026-05-11 修订),`run_pipeline_for_user` / `run_batch_pipeline` / `run_local_transcribe` / `transcribe_files`(creator_sync 路径)入口都用 `.pipeline_state_{task_id}.json`,避免并发任务共享同一份 JSON 把对方正在跑的视频误判成"上次崩溃残留"重新入队 → 双开 → 双倍 Qwen 额度。

### 模块布局（big-picture）

```
api/app.py            FastAPI 入口：lifespan 里做 init_db / FTS 填充 / 启动 scheduler /
                      cleanup_stale_tasks(is_startup=True)（重启后用特定错误信息标记孤儿任务）/ WS 半开扫除
api/routers/          8 个路由：creators assets tasks settings douyin scheduler metrics search
api/websocket_manager 任务进度推送 + 心跳保活 + stale_connection_sweeper

pipeline/orchestrator.py  单创作者下载+转写主调度，账号池决策 + 重试 + 续传
pipeline/worker.py            后台 worker（run_pipeline_for_user / run_batch_pipeline / run_local_transcribe）
pipeline/error_types.py       8 种错误分类 → 决定重试策略
pipeline/state_manager.py     Pipeline 断点续传状态管理（state.json 按 task_id 隔离）
transcribe/flow.py            Qwen 实际转写流程；resume 失败回退会清云端旧 record（2026-05-11）
transcribe/error_classifier.py 错误分类器：提供友好错误消息和操作建议
transcribe/db_account_pool    Qwen 账号池（DB 持久化）

core/cookie_manager.py  统一 Cookie 管理接口（三平台读取/轮换/标记）
core/secure_storage.py  Fernet 对称加密（Cookie 加密能力已就绪，暂未启用）

repositories/         数据访问层（task / creator / asset / transcribe_run）
services/             业务逻辑层；task_ops / cleanup / auto_retry / qwen_status / reconciler / media_asset_service / local_asset_service
services/pipeline_progress.py 进度构建：标准化 API 响应结构（阶段标签/图标/消息）
workers/              一次性后台任务（creator_sync / full_sync / local_transcribe ...）
core/config.py        运行时配置 = SystemSettings；不要绕过
core/background.py    后台 task registry（shutdown 时统一 cancel_all）
core/exceptions.py    AppError / NotFoundError / ValidationError → 统一 JSON 响应
db/core.py            连接（线程级缓存 + WAL）+ 标识符白名单（防 SQL 注入）
                      _VALID_TABLES 白名单：新加表必须加进去
```

### 错误处理模式
- 业务异常抛 `AppError` 子类（[core/exceptions.py](src/media_tools/core/exceptions.py)），由 `app_error_handler` 转 JSON。
- 路由里**不要**写宽泛 `try/except Exception` —— `UnhandledApiErrorsMiddleware` 已统一兜底 `sqlite3.Error / OSError / RuntimeError`。
- 捕获就要写具体异常类型，别加宽泛 `except Exception`。

### 硬约束（被测试强制）
- **不准用 `print`** —— [test_no_print_in_src.py](tests/test_no_print_in_src.py) 会全仓扫描，用 `media_tools.logger.get_logger`。
- **不准引入 Playwright** —— [test_no_playwright_dependency.py](tests/test_no_playwright_dependency.py) 扫 `pyproject.toml` / `requirements.txt` / 全部 src import。Qwen 转写已迁移成纯 HTTP，不要回退。（README 里"Playwright 驱动通义千问 Web 端"是过时描述。）
- 新增表必须加进 `db/core.py` 的 `_VALID_TABLES` 白名单。

### 任务状态机要点
- 任务 `RUNNING` ≠ 业务进行中。重启时所有内存 worker 丢失，但 DB 还残留 `RUNNING` —— `cleanup_stale_tasks(is_startup=True)` 在 startup 把它们标 FAILED，错误信息为"服务重启导致任务中断，请点击重试恢复。"，前端会显示琥珀色醒目横幅和一键重试按钮。
- 子任务（subtasks）才是业务真相，任务状态由子任务聚合。
- **PARTIAL_FAILED 的实际行为**（多次澄清后的最终版）：
  - 由 `local_transcribe_worker` / `creator_sync` / `creator_transcribe_worker` / `pipeline_worker`（`run_pipeline_for_user` / `run_batch_pipeline`）四个 worker 在"部分成功部分失败"时显式设置（2026-05-12 起 pipeline_worker 已对齐）。
  - SQL 层双重保护：`_fail_task` 和 `_complete_task` 的 WHERE 子句都把 `PARTIAL_FAILED` 当终态保护，不允许被任何状态覆盖。
  - 前端在 PARTIAL 任务上显示"重试失败子任务"按钮，**不**触发整任务 auto_retry（避免重跑成功子任务）。
- **auto_retry 字段的真实行为**：`task_queue.auto_retry` 列默认 `0`，**只有用户主动调用 `/api/v1/tasks/{task_id}/auto-retry` 启用后才会触发**。`schedule_auto_retry` 在任何 FAILED 任务上都会被调度，但 `handle_auto_retry` 内部先查这个字段，默认 0 时立即 return。换言之，文档里历史描述的"FAILED 自动重试整任务"在默认配置下根本不触发。

## 协作约定

- 中文注释、中文 commit message（仓库现有风格：`feat(transcribe): ...`、`fix(pipeline): ...`）。
- 注释只解释 **WHY**，不解释 WHAT。
- 别为还没出现的需求做抽象。三行重复优于过早抽象。
- 改 pipeline / orchestrator / transcribe 前先看 [docs/pipeline_reliability_refactor.md](docs/pipeline_reliability_refactor.md) 第 156-189 行的"已完成机制"，确认你的改动不破坏续传不变量。
- [docs/STATUS.md](docs/STATUS.md) 已同步到 2026-05-05（含 Phase 3/4 细节）；任何文档都可能再次漂移，涉及当前进度的判断以代码 + `git log` 为准。

## 领域驱动架构（2026-05 新增，与上方模块布局并存）

> **注意**：上方"模块布局"描述的是按功能域组织的传统目录（`api/`、`pipeline/`、`services/` 等），下方 DDD 架构描述的是新增的分层目录（`domain/`、`infrastructure/`、`application/`、`presentation/`）。两套目录**同时存在**于 `src/media_tools/` 下。新功能优先使用 DDD 架构，旧功能通过 `migration/` 适配层桥接。

### 架构分层

| 层级 | 职责 | 特点 |
|------|------|------|
| **core** | 核心基础设施 | 配置、日志、异常处理；无外部依赖 |
| **domain** | 领域层 | 实体、仓储接口、领域服务；仅依赖 core |
| **infrastructure** | 基础设施层 | 数据库实现、外部 API 集成；依赖 domain + core |
| **application** | 应用层 | 业务管道、工作流编排；依赖 domain + core |
| **presentation** | 表示层 | REST API、WebSocket；依赖 application + domain |

### 核心优势

- **职责分离**：实体、仓储、服务明确分离，单一职责原则
- **依赖倒置**：高层模块不依赖低层模块，两者都依赖抽象接口
- **可测试性**：依赖注入设计，易于 Mock 测试
- **可扩展性**：插件化架构，易于添加新功能和替换实现
- **向后兼容**：通过迁移适配层实现平滑过渡

### 领域层结构

```
domain/
├── entities/           # 领域实体（富领域模型）
│   ├── Asset          # 素材实体（含业务方法）
│   ├── Creator        # 创作者实体
│   ├── Task           # 任务实体
│   └── Transcript     # 转写实体
├── repositories/       # 仓储接口（抽象数据访问）
│   ├── AssetRepository
│   ├── CreatorRepository
│   ├── TaskRepository
│   └── TranscriptRepository
└── services/           # 领域服务（封装业务逻辑）
    ├── AssetDomainService
    ├── CreatorDomainService
    └── TaskDomainService
```

### 领域实体

**Asset（素材实体）** - 核心业务模型：
- `mark_downloaded()` - 标记下载完成
- `mark_transcribed()` - 标记转写完成
- `mark_failed()` - 标记失败状态

**Creator（创作者实体）** - 创作者信息：
- `increment_downloaded()` - 增加下载计数
- `increment_transcript()` - 增加转写计数

**Task（任务实体）** - 任务管理：
- `start()` / `complete()` / `fail()` / `cancel()` - 状态转换
- `update_progress()` - 更新任务进度

### 仓储接口

定义数据访问抽象，不依赖具体实现：

```python
class AssetRepository(ABC):
    def save(self, asset: Asset) -> None: ...
    def find_by_id(self, asset_id: str) -> Optional[Asset]: ...
    def find_by_creator(self, creator_uid: str) -> List[Asset]: ...
    def delete(self, asset_id: str) -> None: ...
```

### 领域服务

封装跨实体的业务逻辑，不包含基础设施细节：

```python
class AssetDomainService:
    def __init__(self, asset_repo: AssetRepository, creator_repo: CreatorRepository): ...
    def create_asset(self, creator_uid: str, title: str) -> Asset: ...
    def mark_downloaded(self, asset_id: str, video_path: Path) -> None: ...
    def mark_transcribed(self, asset_id: str, transcript_path: Path, preview: str) -> None: ...
```

### 基础设施层

```
infrastructure/
└── db/                 # SQLite 仓储实现
    ├── create_asset_repository()
    ├── create_creator_repository()
    ├── create_task_repository()
    └── create_transcript_repository()
```

### 应用层

```
application/
└── pipelines/          # 业务管道
    ├── VideoDownloadPipeline
    ├── TranscribePipeline
    └── ExportPipeline
```

### 表示层

```
presentation/
├── api/
│   └── v2/             # v2 API 路由
│       ├── assets.py
│       ├── creators.py
│       └── tasks.py
└── websocket/          # WebSocket 管理
    └── manager.py
```

### 迁移适配层

`migration/__init__.py` 提供旧服务到新架构的桥接，保持向后兼容：

```python
# 旧服务调用新架构的适配层
from media_tools.migration import migrate_asset_service
asset_service = migrate_asset_service()  # 返回适配后的服务
```

### 迁移策略

旧服务层（`services/task_service.py`、`services/creator_service.py`、`services/asset_service.py`）已通过迁移适配层调用新架构，保持向后兼容。新代码应直接使用领域服务：

```python
# 新代码使用方式
from media_tools.domain.services import AssetDomainService
from media_tools.infrastructure.db import create_asset_repository, create_creator_repository

asset_service = AssetDomainService(
    create_asset_repository(),
    create_creator_repository(),
)
asset = asset_service.get_asset(asset_id)
```

### v2 API

新的 v2 API 路由已注册到主应用，路径前缀 `/api/v2/`，包括：
- `/api/v2/assets` - 素材管理
- `/api/v2/creators` - 创作者管理  
- `/api/v2/tasks` - 任务管理

### 新代码开发规范

1. **新功能**：直接使用 `domain/services` + `infrastructure/db`
2. **修改旧功能**：优先迁移到新架构，保持适配层兼容
3. **测试**：对领域服务进行单元测试，Mock 仓储接口
4. **依赖注入**：通过工厂函数创建仓储实例，避免硬编码

---

## 前端苹果设计风格重构（2026-05）

### 设计规范

#### 色彩系统

| 色彩类型 | 浅色模式 | 深色模式 | 说明 |
|---------|---------|---------|------|
| **背景** | `#F5F5F7` | `#1C1C1E` | Apple 标志性背景色 |
| **卡片** | `#FFFFFF` | `#2C2C2E` | 毛玻璃效果容器 |
| **主色** | `#007AFF` | `#0A84FF` | Apple 蓝 |
| **成功** | `#34C759` | `#30D158` | 绿色强调 |
| **警告** | `#FF9F0A` | `#FFD60A` | 橙色强调 |
| **危险** | `#FF3B30` | `#FF453A` | 红色强调 |
| **文字主色** | `#1D1D1F` | `rgba(255,255,255,0.9)` | 主体文字 |
| **文字次要** | `#86868B` | `rgba(255,255,255,0.55)` | 辅助文字 |

#### 字体层级

| 层级 | 大小 | 字重 | 行高 | 用途 |
|-----|------|------|------|------|
| H1 | 28px | 600 | 1.2 | 页面标题 |
| H2 | 22px | 600 | 1.25 | 区块标题 |
| H3 | 17px | 600 | 1.3 | 卡片标题 |
| Body | 15px | 400 | 1.4 | 正文内容 |
| Caption | 13px | 400 | 1.4 | 辅助说明 |
| Small | 11px | 500 | 1.5 | 标签/状态 |

#### 圆角规范

| 组件类型 | 圆角值 |
|---------|--------|
| 按钮/输入框 | 10px |
| 卡片 | 14px |
| 弹窗/模态框 | 20px |
| 圆形按钮 | 9999px |

#### 动画曲线

- **Spring 弹性**：`cubic-bezier(0.34, 1.56, 0.64, 1)` - 用于突出的交互动画
- **Subtle**：`cubic-bezier(0.25, 0.1, 0.25, 1)` - 用于次要过渡

### 组件重构

#### Button 组件
- 添加新变体：`ghostDestructive`、`linkSecondary`
- 添加新尺寸：`iconSm`、`iconLg`
- 添加按压缩放效果（`active:scale-[0.96]`）
- 使用 Spring 动画曲线

#### Card 组件
- 添加 `hoverable` 属性控制悬停效果
- 添加 `glass` 属性启用毛玻璃效果
- 悬停时上移并增强阴影

#### Input 组件
- 添加 `showClear` 属性支持一键清除
- 聚焦时添加光晕效果
- 优化 padding 和圆角

#### Switch 组件（新增）
- 苹果风格圆润滑块设计
- 平滑过渡动画

#### Badge 组件
- 优化字体大小（11px）
- 添加 `size` 变体
- 药丸形状设计

### 布局组件

#### Sidebar
- 毛玻璃背景效果（`backdrop-blur-2xl`）
- 品牌图标（渐变背景）
- 选中状态发光效果
- 优化导航项间距

#### AppLayout
- 页面过渡动画（`apple-slide-in-right`）
- 玻璃效果头部
- 统一页面标题样式

### 页面优化

#### CreatorCard
- 使用 Card 组件
- 图标统计（素材/已转写/待处理）
- 列表项悬停效果

#### GlobalSettingsSection
- 使用 Card 组件
- 苹果风格列表项
- Switch 开关组件

#### AccountPoolSection
- 使用 Card 组件
- 列表项悬停效果
- 优化状态标签

### 工具类

```css
/* 毛玻璃效果 */
.apple-glass-sidebar
.apple-glass-card  
.apple-glass-modal
.apple-glass-bar

/* 阴影效果 */
.apple-shadow-xs/sm/md/lg/xl

/* 动画效果 */
.apple-fade-in
.apple-slide-in-right  
.apple-scale-in
.apple-slide-up

/* 交互效果 */
.apple-press
.apple-card-hover
.apple-active-glow
.apple-list-item
```

### 响应式适配

- **Touch 目标**：按钮最小尺寸 44px
- **Safe area**：移动端底部安全区域适配
- **Toast 定位**：移动端全屏宽度

### 开发规范

1. **新组件**：使用苹果设计风格变量
2. **旧组件升级**：逐步迁移到新样式
3. **动画**：使用 Spring 曲线实现自然动效
4. **一致性**：保持视觉风格和交互模式统一

---

## 2026-05-11 修订记录

针对本次代码审计发现的隐藏 bug，做了以下修复，落库后 CLAUDE.md 同步更新：

| Bug | 文件 | 修法 |
|-----|------|------|
| 跨任务共享 `.pipeline_state.json` 导致同一文件被双开转写 | `pipeline/worker.py`、`workers/transcribe.py`、`workers/local_transcribe_worker.py`、`workers/creator_transcribe_worker.py` | 所有 worker 入口改成传 `state_file=.pipeline_state_{task_id}.json`，按 task 隔离 |
| `_fail_task` / `_complete_task` 的 SQL WHERE 漏挡 `PARTIAL_FAILED`，可能被错误覆盖触发 auto_retry | `services/task_ops.py` | WHERE 子句加上 `PARTIAL_FAILED`，把它当作终态保护 |
| `services/task_service.py` 是 dead code，且内含 `_mark_task_cancelled(task_id)` 缺参数的 TypeError 隐患 | 删除 `services/task_service.py`、清理 `tests/test_exception_handling.py` 相关测试 | 直接删除文件 |
| resume 回退把旧 `gen_record_id` 丢失，旧云端记录变成 Qwen 端孤儿（额度已扣但 DB 找不回 record_id） | `transcribe/flow.py` | resume 失败回退时先调 `delete_record(api, [old_record_id])` 清云端，再 `update_stage(queued)` |
| v2 cancel 路由对已 CANCELLED/COMPLETED 任务重复调 cancel 会触发 `Task.cancel()` 的 ValueError → 500 | `presentation/api/v2/__init__.py` | 加状态前置检查，终态任务返回 409 |

## 2026-05-12 修订记录

第一轮修完后又拍板了几个"设计偏差"，全部处理：

| 偏差 | 文件 | 修法 |
|------|------|------|
| `pipeline_worker` 在混合成败时仍用 FAILED 而非 PARTIAL_FAILED，跟其他三个 worker 不一致 | `workers/pipeline_worker.py` | 两处 status 判定加 `elif f_count > 0 and s_count > 0: status = "PARTIAL_FAILED"`，跟其他 worker 对齐 |
| v2 路由是半成品（cancel 不中断 worker 等），但已 include 到 app | `api/app.py` | 注释掉 `app.include_router(v2_router)`。等真要启用 DDD 时再恢复 |
| `services/asset_service.py` / `services/creator_service.py` 也是迁移过渡层 dead code | 删除两个文件 + `tests/test_services.py` + `tests/test_exception_handling.py` 中的 `TestAssetServiceExceptionHandling` | 直接删 |
| `AccountPool.acquire_upload_slot` / `release_upload_slot` 等 per-account 上传槽位代码定义了但从未接线 | `pipeline/models.py` + 删 `tests/test_account_pool_upload_slots.py` | 删未接线代码（保留全局 `_upload_gate`，依赖 Qwen 平台自身排队）|

### 第二轮（本轮）

| 事项 | 文件 | 修法 |
|------|------|------|
| 额度领取假成功 | `quota.py`, `qwen_status.py`, `scheduler.py` | trigger 后查 before/after delta，额度没增加就返回 `claimed=False`，避免"显示领取成功但实际未到账" |
| 并发模型重设计 | `pipeline/orchestrator.py`, `pipeline/models.py`, `transcribe/flow.py` | 全局 `Semaphore(n_accounts)` → `dict[account_id, asyncio.Lock]` per-account 上传互斥；删除 `export_gate`；入口闸门 = `2*n_accounts`；AccountPool 去掉余额加权随机，纯轮询+排除集 |
| OSS part_size 调优 | `transcribe/oss_upload.py` | 默认 `part_size` 1MB → 5MB，减少 HTTP 往返；part 级并发 benchmark 证明带宽已饱和，回退串行 |
| 测试适配 | `tests/test_orchestrator_transcribe_runs.py`, `tests/test_qwen_account_pool_db.py` | AccountPool 构造函数去掉余额参数；PipelineConfig 去掉已废弃的 `remove_video`/`keep_original`；`asyncio.Lock()` 懒加载避免 sync 测试实例化报错 |

> 额度领取真接口（`/equity` 页面的实际 POST）仍待替换，当前 delta 兜底足够防御假成功。

### 第三轮（代码审查修复）

| 事项 | 文件 | 修法 |
|------|------|------|
| `_current_account_id` 竞态条件 | `pipeline/orchestrator.py` | 移除实例变量，改为参数传递；并发场景下避免 cleanup 用错 cookie、进度回调显示错误账号 |
| `_cleanup_failed_cloud_records` 跨账号删除 | `pipeline/orchestrator.py` + `repositories/transcribe_run_repository.py` | `find_failed_record_ids` 增加 `account_id` 过滤；cleanup 只删当前账号记录，避免用其他账号 cookie 删失败 |
| `KeyboardInterrupt` 被吞掉 | `pipeline/orchestrator.py` | `gather(return_exceptions=True)` 后遍历 results，遇到 `BaseException`（KeyboardInterrupt/CancelledError）重新 raise |
| resume `record_id` 缺失孤儿记录 | `transcribe/flow.py` | `_try_resume_export_only` 入口检查 `record_id`，缺失时跳过 resume 走完整 flow，避免回退时无法清理 |

至此 5 个 P0-P2 bug + 4 个设计偏差 + 本轮 3 项改动 + 代码审查 4 项修复全部清理完毕。
