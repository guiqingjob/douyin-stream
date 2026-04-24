# Media Tools 功能优化与重构方案

## 一、当前全部功能盘点

### 核心功能（你在用的）

| 功能 | 说明 | 状态 |
|------|------|------|
| 关注创作者 | 添加抖音/B站博主到关注列表 | ✅ 核心 |
| 全量同步 | 下载博主所有视频 + 自动转写 | ✅ 核心 |
| 增量同步 | 只下载博主更新的视频 + 自动转写 | ✅ 核心 |
| 本地转写 | 选择本地视频/音频文件进行转写 | ✅ 核心 |
| 设置管理 | 自动转写开关、并发数、账号配置 | ✅ 核心 |

### 辅助功能（可能用得上）

| 功能 | 说明 | 建议 |
|------|------|------|
| 任务中心 | 查看下载/转写进度 | ✅ 保留，但需优化显示 |
| 素材搜索 | 搜索已下载视频的标题/转写内容 | ⚠️ 保留，但简化 |
| 导出转写 | 批量导出 markdown 文件 | ✅ 保留 |
| 全量同步（批量） | 一键同步所有关注的博主 | ⚠️ 保留，但简化 |
| 定时同步 | 定时自动执行全量/增量同步 | ❌ 建议删除 |

### 冗余功能（建议删除）

| 功能 | 说明 | 建议 |
|------|------|------|
| 收件箱 | 已删除 | ✅ 已处理 |
| 发现页面 | 搜索抖音/B站视频 | ❌ 建议删除 |
| 单 URL 下载 | 粘贴单个视频链接下载 | ❌ 建议删除 |
| 批量 URL 下载 | 粘贴多个视频链接下载 | ❌ 建议删除 |
| 仅下载（不转写） | 只下载视频不做转写 | ❌ 建议删除 |
| 转写对账 | 检查哪些视频没有转写 | ❌ 建议删除 |
| 文件夹扫描转写 | 扫描文件夹批量转写 | ⚠️ 合并到本地转写 |
| 素材标记 | 已读/收藏标记 | ❌ 建议删除 |
| 批量标记 | 批量已读/收藏 | ❌ 建议删除 |
| 素材清理 | 清理已删除的视频记录 | ❌ 建议删除 |
| 多 Qwen 账号 | 多个 Qwen 账号轮询 | ⚠️ 简化为单账号 |
| 多抖音账号 | 多个抖音 Cookie 账号 | ⚠️ 简化为单账号 |
| 多 B站账号 | 多个 B站 Cookie 账号 | ⚠️ 简化为单账号 |
| 账号备注 | 给账号添加备注 | ❌ 建议删除 |
| 自动重试 | 任务失败后自动重试 | ❌ 建议删除 |
| 暂停/恢复 | 暂停正在进行的任务 | ❌ 建议删除 |
| 任务重试 | 用新任务 ID 重试 | ❌ 建议删除 |
| 任务继续 | 用同一任务 ID 断点续传 | ❌ 建议删除 |

---

## 二、为什么功能变得冗余

### 问题 1：功能堆砌

项目最初可能只是一个简单的"下载 + 转写"工具，但随着时间推移，不断添加新功能：
- 加了定时同步
- 加了多账号支持
- 加了发现页面
- 加了素材管理
- 加了任务重试/暂停/恢复

每个功能单独看都有用，但**加起来导致代码复杂度指数级增长**。

### 问题 2：功能耦合

本来简单的功能被过度设计：

```
下载一个视频
├── 先要创建任务
├── 任务要写入数据库
├── 要启动 WebSocket 广播
├── 要支持取消/暂停/恢复
├── 要支持自动重试
├── 下载完成后要自动转写
├── 转写完成后要更新数据库
├── 要通知前端刷新
└── 要处理各种异常状态
```

实际上用户只想：点击下载 → 下载完成 → 自动转写。就这么简单。

### 问题 3：过度抽象

为了支持"所有可能的场景"，代码中到处都是条件分支：

```python
if task_type == 'pipeline':
    ...
elif task_type == 'download':
    ...
elif task_type == 'local_transcribe':
    ...
elif task_type == 'creator_sync_incremental':
    ...
elif task_type == 'creator_sync_full':
    ...
elif task_type == 'full_sync_incremental':
    ...
elif task_type == 'full_sync_full':
    ...
```

8 种任务类型，每种都有不同的处理逻辑，导致 `tasks.py` 膨胀到 1735 行。

---

## 三、优化后的功能清单

### 保留的 6 个核心功能

```
1. 创作者管理
   ├── 添加创作者（粘贴主页链接）
   ├── 删除创作者
   └── 查看创作者列表

2. 全量同步
   ├── 选择创作者
   ├── 点击"全量同步"
   ├── 下载所有视频
   └── 自动转写所有视频

3. 增量同步
   ├── 选择创作者
   ├── 点击"增量同步"
   ├── 检查是否有新视频
   ├── 下载新视频
   └── 自动转写新视频

4. 本地转写
   ├── 选择本地视频/音频文件
   ├── 上传到 Qwen
   ├── 自动转写
   └── 保存为 markdown

5. 素材管理
   ├── 查看已下载的视频列表
   ├── 查看转写内容
   ├── 搜索标题/转写内容
   └── 导出转写文件

6. 设置
   ├── 开启/关闭自动转写
   ├── 设置并发数
   ├── 配置 Qwen Cookie
   ├── 配置抖音 Cookie
   └── 配置 B站 Cookie
```

### 删除的功能清单

```
❌ 发现页面（搜索视频）
❌ 单 URL 下载
❌ 批量 URL 下载
❌ 仅下载（不转写）
❌ 定时同步
❌ 转写对账
❌ 文件夹扫描转写（合并到本地转写）
❌ 素材标记（已读/收藏）
❌ 批量标记
❌ 素材清理
❌ 多账号支持（简化为单账号）
❌ 账号备注
❌ 自动重试
❌ 暂停/恢复
❌ 任务重试
❌ 任务继续（断点续传）
```

---

## 四、重构后的架构

### 后端架构（精简版）

```
src/media_tools/
├── api/
│   └── routers/
│       ├── creators.py      # 创作者管理（3 个接口）
│       ├── tasks.py         # 任务管理（简化）
│       ├── assets.py        # 素材管理（简化）
│       └── settings.py      # 设置管理（简化）
├── services/
│   ├── creator_service.py   # 创作者业务逻辑
│   ├── download_service.py  # 下载业务逻辑
│   ├── transcribe_service.py # 转写业务逻辑
│   └── asset_service.py     # 素材业务逻辑
├── repositories/
│   ├── creator_repo.py      # 创作者数据访问
│   ├── task_repo.py         # 任务数据访问
│   └── settings_repo.py     # 设置数据访问
├── core/
│   ├── config.py            # 统一配置
│   └── workflow.py          # 工作流定义
├── douyin/
│   └── core/
│       └── downloader.py    # 抖音下载器（只返回新文件列表）
├── bilibili/
│   └── core/
│       └── downloader.py    # B站下载器（只返回新文件列表）
├── pipeline/
│   └── orchestrator.py      # 下载+转写编排（简化）
├── transcribe/
│   └── flow.py              # 转写流程
└── db/
    └── core.py              # 数据库（4 张表）
```

### 数据库 Schema（精简版）

```sql
-- 1. 创作者表（用户手动管理）
CREATE TABLE creators (
    uid TEXT PRIMARY KEY,           -- 唯一标识
    platform TEXT,                  -- douyin | bilibili
    homepage_url TEXT,              -- 主页链接
    nickname TEXT,                  -- 昵称
    last_sync_time TIMESTAMP        -- 上次同步时间（增量同步用）
);

-- 2. 任务表（临时状态，完成后可删除）
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    creator_uid TEXT,               -- 关联创作者
    type TEXT,                      -- full_sync | incremental_sync | local_transcribe
    status TEXT,                    -- pending | running | completed | failed
    progress REAL DEFAULT 0.0,      -- 0.0 ~ 1.0
    message TEXT,                   -- 当前状态描述
    result_summary JSON,            -- {success: N, failed: N, total: N}
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 3. 设置表
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- 4. 账号表（合并所有平台）
CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    platform TEXT,                  -- douyin | bilibili | qwen
    type TEXT,                      -- cookie | api_key
    data TEXT                       -- 加密存储
);
```

**为什么只有 4 张表？**

- `media_assets` 删除了 → 素材信息从文件系统扫描获取
- `video_metadata` 删除了 → F2 库的缓存存为 .json 文件
- `user_info_web` 删除了 → 同上
- `scheduled_tasks` 删除了 → 定时同步功能删除
- `auth_credentials` 删除了 → 合并到 accounts

---

## 五、任务状态机（简化版）

```
          用户点击同步
               |
               v
        +-------------+
        |   PENDING   |  <-- 任务创建，等待执行
        +-------------+
               |
               | 开始执行
               v
        +-------------+
        |   RUNNING   |  <-- 正在下载/转写
        +-------------+
               |
       +-------+-------+
       |               |
       v               v
+-------------+  +-------------+
|  COMPLETED  |  |   FAILED    |
+-------------+  +-------------+
```

**删除的状态：**
- `PAUSED` → 暂停功能删除
- `CANCELLED` → 取消功能简化（直接标记为失败）

**删除的操作：**
- 暂停/恢复
- 自动重试
- 断点续传
- 任务重试

---

## 六、工作流（简化版）

### 全量同步

```
用户点击"全量同步"
    |
    v
创建任务（status=PENDING）
    |
    v
标记任务为 RUNNING
    |
    v
下载所有视频（跳过已存在的）
    |
    v
如果开启了自动转写：
    逐个转写新下载的视频
    |
    v
标记任务为 COMPLETED
    |
    v
更新 creator.last_sync_time
```

### 增量同步

```
用户点击"增量同步"
    |
    v
创建任务（status=PENDING）
    |
    v
获取 creator.last_sync_time
    |
    v
下载器只获取该时间之后的视频
    |
    v
如果开启了自动转写：
    逐个转写新下载的视频
    |
    v
标记任务为 COMPLETED
    |
    v
更新 creator.last_sync_time
```

### 本地转写

```
用户选择本地文件
    |
    v
创建任务（status=PENDING）
    |
    v
上传到 Qwen OSS
    |
    v
Playwright 自动转写
    |
    v
保存为 markdown 文件
    |
    v
标记任务为 COMPLETED
```

---

## 七、前端页面（简化版）

```
frontend/src/
├── pages/
│   ├── Creators.tsx           # 创作者列表（关注/取消关注/同步）
│   └── Settings.tsx           # 设置页面
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx        # 侧边栏（创作者/设置）
│   │   └── TaskMonitor.tsx    # 任务进度（简化版）
│   └── features/
│       ├── CreatorCard.tsx    # 创作者卡片
│       ├── SyncButton.tsx     # 同步按钮（全量/增量）
│       └── TaskProgress.tsx   # 任务进度条
├── services/
│   ├── creators.ts            # 创作者 API
│   ├── tasks.ts               # 任务 API
│   └── settings.ts            # 设置 API
└── store/
    ├── useCreatorsStore.ts    # 创作者状态
    └── useTasksStore.ts       # 任务状态
```

**删除的页面：**
- ❌ Inbox（已删除）
- ❌ Discovery（发现页面）

---

## 八、删除功能后的代码量估算

| 模块 | 当前行数 | 删除后估算 | 减少 |
|------|---------|-----------|------|
| `api/routers/tasks.py` | 1735 | ~400 | 77% |
| `api/routers/assets.py` | 500 | ~200 | 60% |
| `api/routers/settings.py` | 396 | ~150 | 62% |
| `api/routers/scheduler.py` | 218 | 0（删除）| 100% |
| `frontend/Settings.tsx` | 798 | ~200 | 75% |
| `frontend/TaskMonitorPanel.tsx` | 521 | ~150 | 71% |
| **总计** | **~12400** | **~5000** | **~60%** |

---

## 九、实施步骤

### Step 1：功能冻结（1 天）

- [ ] 明确删除的功能清单
- [ ] 备份当前代码
- [ ] 建立 feature flag（可选）

### Step 2：删除冗余功能（2-3 天）

- [ ] 删除定时同步（scheduler）
- [ ] 删除发现页面（Discovery）
- [ ] 删除单 URL/批量 URL 下载
- [ ] 删除仅下载（不转写）
- [ ] 删除转写对账
- [ ] 删除素材标记/批量标记/清理
- [ ] 删除多账号支持（简化为单账号）
- [ ] 删除暂停/恢复/重试/断点续传
- [ ] 简化任务类型（只保留 3 种）

### Step 3：精简数据库（1 天）

- [ ] 删除冗余表
- [ ] 合并 accounts 表
- [ ] 删除 media_assets 表（改用文件系统索引）

### Step 4：重构后端（3-4 天）

- [ ] 添加 Repository 层
- [ ] 添加 Service 层
- [ ] 简化 API Router
- [ ] 统一配置系统

### Step 5：重构前端（2-3 天）

- [ ] 删除 Discovery 页面
- [ ] 简化 Settings 页面
- [ ] 简化 TaskMonitorPanel
- [ ] 拆分 Store

### Step 6：验证（1-2 天）

- [ ] 全量同步测试
- [ ] 增量同步测试
- [ ] 本地转写测试
- [ ] 设置修改测试

---

## 十、风险与回滚

| 风险 | 缓解措施 |
|------|---------|
| 删除功能后用户需要 | 保留备份分支，可随时恢复 |
| 数据库迁移出错 | 导出数据 → 重建数据库 → 导入数据 |
| 增量同步逻辑错误 | 保留 `last_sync_time` 日志，可追溯 |
| 文件系统索引性能差 | 缓存索引结果，定时刷新 |

---

## 总结

**当前问题：** 功能堆砌 + 过度设计 → 代码臃肿 + 难以维护

**解决方案：** 删除 16 个冗余功能，保留 6 个核心功能，代码量减少 60%

**核心原则：** 只做"下载 + 转写"这两件事，其他都是干扰
