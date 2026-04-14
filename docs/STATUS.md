# Media Tools — 项目现状文档

> 最后更新：2026-04-15

---

## 一、项目概况

抖音视频批量下载 + 通义千问（Qwen）自动转写的一体化本地工作站。

| 维度 | 现状 |
|------|------|
| 后端 | FastAPI + Uvicorn，SQLite3（无 ORM），APScheduler 定时任务 |
| 前端 | React 19 + Vite 8 + Tailwind 4 + shadcn/ui + Zustand 5 |
| 视频抓取 | F2 库（抖音 API 封装） |
| 转写引擎 | Playwright 驱动通义千问 Web 端 |
| 实时通信 | WebSocket 推送任务进度 |
| Python | >= 3.11 |
| 启动方式 | `./run.sh`（同时拉起后端 8000 + 前端 5173） |

---

## 二、后端 API 端点清单

### 2.1 创作者 `/api/v1/creators`

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/v1/creators/` | 列出所有创作者及资产统计 |
| POST | `/api/v1/creators/` | 通过抖音主页链接添加创作者 |
| DELETE | `/api/v1/creators/{uid}` | 删除创作者及全部关联资产 |

### 2.2 素材 `/api/v1/assets`

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/v1/assets/` | 按创作者 UID 过滤素材列表 |
| GET | `/api/v1/assets/{asset_id}/transcript` | 获取转写文稿内容 |
| DELETE | `/api/v1/assets/{asset_id}` | 删除单个素材（含本地文件） |

### 2.3 任务 `/api/v1/tasks`

| 方法 | 路径 | 用途 |
|------|------|------|
| WebSocket | `/api/v1/tasks/ws` | 实时任务进度推送 |
| POST | `/api/v1/tasks/pipeline` | 单创作者下载+转写全流水线 |
| POST | `/api/v1/tasks/pipeline/batch` | 批量视频 URL 下载+转写 |
| POST | `/api/v1/tasks/download/batch` | 批量仅下载 |
| POST | `/api/v1/tasks/download/creator` | 按创作者下载（增量/全量） |
| POST | `/api/v1/tasks/download/full-sync` | 全量同步所有关注创作者 |
| GET | `/api/v1/tasks/active` | 获取活跃任务列表 |
| GET | `/api/v1/tasks/history` | 获取最近 50 条任务历史 |
| GET | `/api/v1/tasks/{task_id}` | 查询单任务状态 |

### 2.4 设置 `/api/v1/settings`

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/v1/settings/` | 获取系统设置总览 |
| POST | `/api/v1/settings/douyin` | 添加抖音账号到账号池 |
| DELETE | `/api/v1/settings/douyin/{account_id}` | 移除抖音账号 |
| POST | `/api/v1/settings/global` | 更新全局设置（并发/自动删除/自动转写） |
| POST | `/api/v1/settings/qwen` | 保存 Qwen Cookie |

### 2.5 抖音元数据 `/api/v1/douyin`

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/v1/douyin/metadata` | 获取创作者主页视频预览列表 |

### 2.6 定时任务 `/api/v1/scheduler`

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/v1/scheduler/` | 列出所有定时任务 |
| POST | `/api/v1/scheduler/` | 添加定时同步（cron 表达式） |
| PUT | `/api/v1/scheduler/{task_id}/toggle` | 启用/禁用定时任务 |
| DELETE | `/api/v1/scheduler/{task_id}` | 删除定时任务 |
| POST | `/api/v1/scheduler/run_now` | 立即手动触发全量同步 |

### 2.7 其他

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/health` | 健康检查 |

---

## 三、前端页面/路由清单

| 路由 | 页面组件 | 功能 |
|------|---------|------|
| `/` | → 重定向到 `/creators` | — |
| `/overview` | → 重定向到 `/creators` | 旧路由兼容 |
| `/creators` | `Creators.tsx` | 创作者管理：添加/删除创作者、单个同步、全量同步、定时同步开关 |
| `/discover` | `Discovery.tsx` | 发现页：粘贴主页链接预览视频、勾选后下载或转写 |
| `/inbox` | `Inbox.tsx` | 收件箱：按创作者浏览素材、阅读转写文稿、删除素材 |
| `/settings` | `Settings.tsx` | 设置页：抖音账号池、Qwen Cookie、全局参数（并发/自动转写/自动删除） |

### 布局组件

| 组件 | 位置 | 功能 |
|------|------|------|
| `Sidebar` | 全局左侧 w-64 | 导航 + 主题切换 + 任务监控入口 |
| `TaskMonitorPanel` | Sidebar 底部弹出 | 任务中心 Dialog：查看所有任务状态/进度/错误 |
| `TaskStatusBanner` | 页面内嵌 | 行内任务状态条（运行中/成功/失败） |

---

## 四、数据库表结构（SQLite3，7 张表）

| 表名 | 所属域 | 定义位置 | 说明 |
|------|--------|---------|------|
| `creators` | 创作者 | `db/core.py` | 用户 UID、昵称、头像、同步状态 |
| `media_assets` | 素材 | `db/core.py` | 视频/转写状态、本地路径 |
| `task_queue` | 任务 | `db/core.py` | 任务类型、进度、状态 |
| `auth_credentials` | 认证 | `db/core.py` | 平台认证数据（Qwen） |
| `Accounts_Pool` | 账号池 | `settings.py` / `f2_helper.py` | 抖音 Cookie 账号池 |
| `SystemSettings` | 设置 | `settings.py` | KV 形式全局设置 |
| `scheduled_tasks` | 定时任务 | `scheduler.py` | Cron 表达式、启用状态 |

---

## 五、当前最痛的问题

### 5.1 工程基础设施

| 严重度 | 问题 | 影响 |
|--------|------|------|
| **P0** | `frontend/` 是 gitlink 但缺少 `.gitmodules`，子模块配置损坏 | 新人 clone 无法拉取前端 |
| **P0** | `__main__.py` 导入不存在的 `cli_main` 模块 | `python -m media_tools` 直接 ImportError |
| **P0** | `scheduler.py` 未加入 git，但 `app.py` 已引用 | 提交后应用启动即崩溃 |
| **P0** | `pyproject.toml` 缺少 `fastapi` / `uvicorn` 依赖声明 | `pip install .` 后 API 无法启动 |
| **P1** | 19 个文件 +696/-451 行未提交 | 大批量改动存在丢失风险 |
| **P1** | `pyproject.toml` 写 `f2>=0.0.1.0`，`requirements.txt` 写 `f2>=1.0.0` | 版本约束矛盾 |

### 5.2 安全问题

| 严重度 | 问题 | 位置 |
|--------|------|------|
| **P0** | `config/config.yaml` 含明文抖音 Cookie（session_id 等） | 若已提交到 Git 则已泄露 |
| **P1** | CORS `allow_origins=["*"]` + `allow_credentials=True` | `app.py` |

### 5.3 后端代码质量

| 问题 | 位置 | 说明 |
|------|------|------|
| 数据库连接管理不统一 | 各 router 各自 `get_db_connection()` | 部分在连接函数中执行 DDL |
| 表定义散落多处 | `settings.py`、`f2_helper.py`、`scheduler.py` | 应统一到 `db/core.py` |
| `INSERT OR REPLACE` 覆盖任务字段 | `tasks.py:93` | 应改用 `UPDATE` 或 `UPSERT` |
| `conn` 可能未赋值 | `db/core.py:115-119` finally 块 | `sqlite3.connect()` 异常时 NameError |
| 两套 orchestrator 共存 | `orchestrator.py` + `orchestrator_v2.py` | DB 更新逻辑重复，V1 已过时 |
| `print()` 代替 logger | `creators.py`、`assets.py` | API 服务中日志丢失 |
| 异常静默吞没 | `list_creators()` / `list_assets()` | `except Exception: return []` 掩盖严重错误 |
| `@router.on_event` 已弃用 | `scheduler.py` | 应改用 `lifespan` 上下文管理器 |
| stale task 清理在 GET 中执行 | `tasks.py` | 读操作触发写操作，并发时可能锁争用 |

### 5.4 前端代码质量

| 问题 | 位置 | 说明 |
|------|------|------|
| `Toggle` 组件重复定义 | `Creators.tsx` + `Settings.tsx` | 应抽取到 `components/ui/` |
| 双重 Toast 错误提示 | `api.ts` 拦截器 + 各页面 catch | 每个失败请求弹两次 Toast |
| 5 个 API 函数从未使用 | `api.ts` | `triggerPipeline`、`getTaskStatus`、`getActiveTasks`、`deleteSchedule`、`runScheduleNow` |
| `CardAction` 组件从未使用 | `card.tsx` | 死代码 |
| `@fontsource-variable/geist` 从未导入 | `package.json` | 无用依赖 |
| `"use client"` 指令 | `dialog.tsx` | Next.js 产物，Vite 项目无效 |
| Inbox 素材列表未虚拟化 | `Inbox.tsx` | 素材多时性能差（创作者列表已用 Virtuoso） |
| Discovery 底部栏硬编码 sidebar 偏移 | `Discovery.tsx` | `left-[calc(50%+8rem)]` 与 sidebar 宽度耦合 |
| 并发数输入无程序化上限校验 | `Settings.tsx` | HTML `max=10` 不强制执行 |
| store 中 `(taskUpdate as any).msg` | `useStore.ts:49` | 类型安全逃逸 |
| 零测试 | `tests/web/` 为空 | 前端无任何测试 |

### 5.5 遗留垃圾

| 文件/目录 | 说明 |
|-----------|------|
| `douyin_users.db` | 旧数据库 |
| `.streamlit/` | 旧 Streamlit 配置 |
| 根目录 `config.yaml` | 与 `config/config.yaml` 重复 |
| 根目录 `following.json` | 运行时产物泄漏到根目录 |
| 根目录 `__pycache__/` | 临时测试脚本的编译缓存 |
| `.github/` | 空目录（CI 已移除） |
| `docs/` | 空目录（仅 `.DS_Store`） |

---

## 六、前后端对接情况

### 前端已对接的后端接口

| 前端函数 | 后端接口 | 使用页面 |
|---------|---------|---------|
| `getCreators()` | GET `/creators/` | Discovery, Inbox, Creators |
| `addCreator(url)` | POST `/creators/` | Discovery, Creators |
| `deleteCreator(uid)` | DELETE `/creators/{uid}` | Inbox, Creators |
| `getAssetsByCreator(uid)` | GET `/assets/` | Inbox |
| `getAssetTranscript(id)` | GET `/assets/{id}/transcript` | Inbox |
| `deleteAsset(id)` | DELETE `/assets/{id}` | Inbox |
| `getTaskHistory()` | GET `/tasks/history` | Store (初始化) |
| `fetchMetadata(url)` | GET `/douyin/metadata` | Discovery |
| `triggerBatchPipeline(urls)` | POST `/tasks/pipeline/batch` | Discovery |
| `triggerDownloadBatch(urls)` | POST `/tasks/download/batch` | Discovery |
| `triggerCreatorDownload(uid)` | POST `/tasks/download/creator` | Creators |
| `triggerFullSyncFollowing()` | POST `/tasks/download/full-sync` | Creators |
| `getSettings()` | GET `/settings/` | Store (初始化) |
| `addDouyinAccount(cookie)` | POST `/settings/douyin` | Settings |
| `deleteDouyinAccount(id)` | DELETE `/settings/douyin/{id}` | Settings |
| `updateQwenKey(cookie)` | POST `/settings/qwen` | Settings |
| `updateGlobalSettings(...)` | POST `/settings/global` | Settings |
| `getSchedules()` | GET `/scheduler/` | Creators |
| `addSchedule(cron)` | POST `/scheduler/` | Creators |
| `toggleSchedule(id)` | PUT `/scheduler/{id}/toggle` | Creators |
| WebSocket | `/tasks/ws` | Store (实时推送) |

### 前端已声明但从未调用的接口（死代码）

| 前端函数 | 后端接口 | 原因 |
|---------|---------|------|
| `triggerPipeline(url)` | POST `/tasks/pipeline` | 被 batch 版本替代 |
| `getTaskStatus(id)` | GET `/tasks/{id}` | WebSocket 替代了轮询 |
| `getActiveTasks()` | GET `/tasks/active` | 同上 |
| `deleteSchedule(id)` | DELETE `/scheduler/{id}` | 前端只做 toggle，无删除 UI |
| `runScheduleNow()` | POST `/scheduler/run_now` | 用 `triggerFullSyncFollowing` 替代 |

---

## 七、未来规划与改进方向

### 7.1 P0 — 必须立即修复

- [ ] **修复子模块配置**：添加 `.gitmodules` 或将 frontend 改为 monorepo 结构
- [ ] **删除或修复 `__main__.py`**：移除对不存在的 `cli_main` 的引用
- [ ] **将 `scheduler.py` 纳入版本控制**：`git add` 并与 `app.py` 一起提交
- [ ] **补全 `pyproject.toml` 依赖**：添加 `fastapi`、`uvicorn`、`pydantic`
- [ ] **统一版本约束**：`pyproject.toml` 与 `requirements.txt` 中 `f2` 版本对齐
- [ ] **移除明文 Cookie**：`config/config.yaml` 中的敏感信息替换为占位符，确保 `.gitignore` 覆盖

### 7.2 P1 — 短期改进（1-2 周）

- [ ] **统一数据库层**：所有表定义集中到 `db/core.py`，统一连接工厂，用 `with` 管理连接
- [ ] **清理 orchestrator**：移除 V1（`orchestrator.py`），只保留 V2
- [ ] **用 logger 替换 print**：所有 router 中的 `print()` 改用 `logging`
- [ ] **修复 tasks.py 的 `INSERT OR REPLACE`**：改为 `UPDATE` + `INSERT ... ON CONFLICT`
- [ ] **抽取 Toggle 组件**：从 `Creators.tsx`/`Settings.tsx` 提取到 `components/ui/toggle.tsx`
- [ ] **修复双重 Toast**：移除 Axios 拦截器中的 `toast.error`，由各页面自行处理
- [ ] **清理死代码**：移除 5 个未使用的 API 函数、`CardAction`、`"use client"` 指令
- [ ] **Inbox 素材列表虚拟化**：对 assets grid 使用 `VirtuosoGrid`
- [ ] **提交当前改动**：19 个文件的未提交变更尽快入库
- [ ] **清理遗留文件**：`douyin_users.db`、`.streamlit/`、根目录 `config.yaml`、`following.json`、根目录 `__pycache__/`

### 7.3 P2 — 中期优化（1-2 月）

- [ ] **CORS 收紧**：`allow_origins` 限定为实际前端地址
- [ ] **用 `lifespan` 替换 `on_event`**：scheduler 的 startup/shutdown 迁移到 FastAPI lifespan
- [ ] **Discovery 底部栏去硬编码**：用 CSS 变量或相对定位替代 `calc(50%+8rem)` 硬编码偏移
- [ ] **Settings 并发数校验**：程序化 clamp 到 1-10 范围
- [ ] **Store 类型安全**：消除 `(taskUpdate as any).msg` 类型逃逸
- [ ] **异常处理改进**：`list_creators()` / `list_assets()` 不再静默吞异常
- [ ] **前端测试**：为核心页面补充 Vitest + React Testing Library 用例
- [ ] **后端测试补全**：`tests/web/` 目录为空，API 集成测试覆盖度待提升
- [ ] **Stale task 清理**：从 GET 请求中移出，改为后台定时清理

### 7.4 P3 — 长期愿景

- [ ] **Docker 化**：编写 `Dockerfile` + `docker-compose.yml`，一键部署
- [ ] **CI/CD 恢复**：在 `.github/workflows/` 添加 lint + test + build 流水线
- [ ] **数据库迁移**：考虑从裸 SQLite3 迁移到 SQLAlchemy 或至少加入 migration 机制
- [ ] **多平台支持**：架构上为 B 站、小红书等平台预留扩展点
- [ ] **用户认证**：如果需要多人使用，添加基本的用户登录
- [ ] **OSS/CDN 集成**：转写结果可选上传到对象存储，生成分享链接
- [ ] **移动端适配**：当前 UI 未对小屏做响应式处理
- [ ] **Playwright 转写替代方案**：探索 Qwen API 官方接口替代浏览器自动化，提升稳定性
