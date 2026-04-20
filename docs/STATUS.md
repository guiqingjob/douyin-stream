# Media Tools — 项目现状文档

> 最后更新：2026-04-20

---

## 最近更新（2026-04-20）

### 任务中心重构

**已完成的改进：**

| 功能 | 描述 |
|------|------|
| 清除历史优化 | 清除后不再从数据库恢复（前端 historyCleared 标记） |
| WebSocket 断连提示 | 红色提示条 + 侧边栏红点 |
| 简化重试按钮 | 失败任务只显示一个"重试"按钮 |
| 展开详情面板 | 点击任务卡片展开，显示详细信息 |
| 子任务列表 | 展示成功/失败/进行中的视频列表 |
| 状态标签友好化 | "可能中断"替代"已过期"等 |
| 后端 payload 结构化 | 支持 `result_summary` 和 `subtasks` 字段 |

**数据流架构：**

```
用户创建任务
     ↓
后端存储 payload（含 subtasks 列表）
     ↓
WebSocket 广播进度更新（含 result_summary）
     ↓
前端展示：成功 X / 失败 Y / 子任务列表
```

### 代码质量优化

**异常处理改进：**

| 指标 | 改进前 | 改进后 |
|------|--------|--------|
| 宽泛异常捕获 | 56 处 | 9 处 |
| 减少比例 | - | 84% |

**改进的异常类型：**

| 文件 | 改进 |
|------|------|
| `tasks.py` | sqlite3.Error, json.JSONDecodeError |
| `assets.py` | OSError, ValueError |
| `creators.py` | sqlite3.Error, OSError, ValueError |
| `db/core.py` | sqlite3.Error |
| `orchestrator_v2.py` | sqlite3.Error |
| `preview.py` | OSError, zipfile.BadZipFile, ET.ParseError |
| `downloader*.py` | OSError, ImportError, IOError |

**剩余 9 处合理保留：**
- Playwright 自动化（多种浏览器/网络异常）
- 数据库事务回滚（需要捕获所有异常确保回滚）
- 后台任务日志记录（已有 logger.exception）

### Inbox 三栏布局

- Apple Mail Pro 风格：创作者列表 + 素材列表 + 即时预览
- **本地素材独立入口**：黄色徽章标识，与博主列表分离
- 本地文件夹分组显示，支持展开/折叠
- 进入页面自动同步文件系统与数据库
- 主题切换按钮（深色/浅色模式）

### 素材来源

| 来源 | 说明 |
|------|------|
| 抖音创作者 | 通过主页 URL 添加，自动下载该创作者的视频 |
| B站 UP 主 | 通过空间链接添加，自动下载视频 |
| 本地素材 | 通过「本地转写」上传，**独立入口显示**，按文件夹分组 |

---

## 一、项目概况

抖音/B站视频批量下载 + 通义千问（Qwen）自动转写的 **Web 工作站**。

> **注意**：项目已完全迁移到 Web 界面，不再提供 CLI 交互模式。

| 维度 | 现状 |
|------|------|
| 后端 | FastAPI + Uvicorn，SQLite3（无 ORM），APScheduler 定时任务 |
| 前端 | React 19 + Vite 8 + Tailwind 4 + shadcn/ui + Zustand 5 |
| 视频抓取 | F2 库（抖音）+ yt-dlp（B站） |
| 转写引擎 | Playwright 驱动通义千问 Web 端 |
| 实时通信 | WebSocket 推送任务进度 |
| Python | >= 3.11 |
| 启动方式 | `./run.sh`（后端 8000 + 前端 5173） |

### 素材来源

| 来源 | 说明 |
|------|------|
| 抖音创作者 | 通过主页 URL 添加，自动下载该创作者的视频 |
| B站 UP 主 | 通过空间链接添加，自动下载视频 |
| 本地文件 | 通过「本地转写」上传，**独立存储于文件夹分组中**，不归属于创作者 |

---

## 二、后端 API 端点清单

### 2.1 创作者 `/api/v1/creators`

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/v1/creators/` | 列出所有创作者及资产统计 |
| POST | `/api/v1/creators/` | 通过主页链接添加创作者（抖音/B站） |
| DELETE | `/api/v1/creators/{uid}` | 删除创作者及全部关联资产 |

### 2.2 素材 `/api/v1/assets`

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/v1/assets/` | 按创作者 UID 过滤素材列表 |
| GET | `/api/v1/assets/search` | 全文搜索素材 |
| GET | `/api/v1/assets/{asset_id}/transcript` | 获取转写文稿内容 |
| DELETE | `/api/v1/assets/{asset_id}` | 删除单个素材（含本地文件） |
| POST | `/api/v1/assets/bulk_delete` | 批量删除素材 |
| POST | `/api/v1/assets/bulk_mark` | 批量标记已读/收藏 |
| POST | `/api/v1/assets/export` | 导出转写文稿（ZIP） |

### 2.3 任务 `/api/v1/tasks`

| 方法 | 路径 | 用途 |
|------|------|------|
| WebSocket | `/api/v1/tasks/ws` | 实时任务进度推送 |
| POST | `/api/v1/tasks/pipeline` | 单创作者下载+转写全流水线 |
| POST | `/api/v1/tasks/pipeline/batch` | 批量视频 URL 下载+转写 |
| POST | `/api/v1/tasks/download/batch` | 批量仅下载 |
| POST | `/api/v1/tasks/download/creator` | 按创作者下载（增量/全量） |
| POST | `/api/v1/tasks/download/full-sync` | 全量同步所有关注创作者 |
| POST | `/api/v1/tasks/transcribe/local` | 本地文件转写 |
| POST | `/api/v1/tasks/reconcile-transcripts` | 同步文件系统与数据库 |
| GET | `/api/v1/tasks/active` | 获取活跃任务列表 |
| GET | `/api/v1/tasks/history` | 获取最近 50 条任务历史 |
| DELETE | `/api/v1/tasks/history` | 清除历史任务 |

### 2.4 设置 `/api/v1/settings`

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/v1/settings/` | 获取系统设置总览 |
| POST | `/api/v1/settings/douyin` | 添加抖音账号到账号池 |
| DELETE | `/api/v1/settings/douyin/{account_id}` | 移除抖音账号 |
| POST | `/api/v1/settings/bilibili/accounts` | 添加B站账号 |
| POST | `/api/v1/settings/qwen` | 保存 Qwen Cookie |
| POST | `/api/v1/settings/global` | 更新全局设置（并发/自动删除/自动转写） |

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

---

## 三、前端页面/路由清单

| 路由 | 页面组件 | 功能 |
|------|---------|------|
| `/` | → 重定向到 `/inbox` | — |
| `/inbox` | `Inbox.tsx` | 收件箱：三栏布局，自动同步，文件夹分组 |
| `/discover` | `Discovery.tsx` | 发现页：粘贴链接预览视频、批量下载 |
| `/creators` | `Creators.tsx` | 创作者管理：添加/删除、同步、定时任务 |
| `/settings` | `Settings.tsx` | 设置页：账号池、Cookie、全局参数 |

### 布局组件

| 组件 | 位置 | 功能 |
|------|------|------|
| `Sidebar` | 全局左侧 | 导航 + 主题切换 + 任务监控入口 |
| `TaskMonitorPanel` | Sidebar 底部弹出 | 任务中心：状态/进度/子任务列表 |
| `InboxAuthorList` | Inbox 左侧 | 创作者列表（含未读计数） |

---

## 四、数据库表结构（SQLite3）

| 表名 | 说明 |
|------|------|
| `creators` | 创作者信息（UID、昵称、平台、同步状态） |
| `media_assets` | 素材（视频/转写状态、本地路径、已读/收藏） |
| `task_queue` | 任务队列（类型、进度、状态、payload） |
| `auth_credentials` | 平台认证数据 |
| `Accounts_Pool` | 账号池（抖音/B站/Qwen Cookie） |
| `SystemSettings` | KV 形式全局设置 |
| `scheduled_tasks` | 定时任务（Cron 表达式、启用状态） |
| `assets_fts` | FTS5 全文搜索索引 |

---

## 五、已完成的改进

### 2026-04-20

- [x] 任务中心重构（清除历史、断连提示、子任务列表）
- [x] 异常处理优化（56 → 9 处，减少 84%）
- [x] Inbox 三栏布局 + 自动同步
- [x] 主题切换功能
- [x] 清理未使用文件

### 2026-04-15

- [x] 收件箱三栏布局重构
- [x] 本地文件夹分组
- [x] 数据库自动同步
- [x] Apple 设计语言
- [x] 双向同步完善
- [x] 批量操作优化

### 更早期

- [x] 统一数据库层
- [x] 清理 orchestrator（移除 V1）
- [x] 用 logger 替换 print
- [x] 修复双重 Toast
- [x] 清理死代码
- [x] CORS 收紧
- [x] 用 lifespan 替换 on_event

---

## 六、待改进项

### P2 — 中期优化

- [ ] **前端测试**：补充 Vitest + React Testing Library
- [ ] **Store 类型安全**：消除 `(taskUpdate as any).msg`
- [ ] **Settings 并发数校验**：程序化 clamp 到 1-10

### P3 — 长期愿景

- [ ] **Docker 化**：编写 Dockerfile + docker-compose.yml
- [ ] **CI/CD 恢复**：添加 lint + test + build 流水线
- [ ] **数据库迁移**：考虑 SQLAlchemy 或 migration 机制
- [ ] **多平台支持**：为小红书等平台预留扩展点
- [ ] **移动端适配**：响应式处理
- [ ] **Playwright 替代方案**：探索 Qwen API 官方接口
