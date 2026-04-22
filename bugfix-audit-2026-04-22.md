# Bug 审查报告 2026-04-22

## 概述

对项目后端（Python/FastAPI）和前端（React/TypeScript）进行全面代码审查，共发现 **46 个问题**。

| 严重级别 | 数量 |
|---------|------|
| CRITICAL | 3 |
| HIGH | 9 |
| MEDIUM | 22 |
| LOW | 12 |

---

## CRITICAL — 3 个

### C1. Cookie 临时文件在 yt-dlp 使用前被删除
- **文件**: `src/media_tools/douyin/core/downloader_ytdlp.py:446-448`
- **问题**: `download_by_url()` 中，cookie 内容在 `with managed_temp_file(...)` 块内写入，块退出后文件被删除。但 `cookiefile` 路径指向已删除文件，yt-dlp 读取时文件不存在，下载将无 Cookie 认证。

### C2. 同一 bug 出现在 `download_by_url_pausable`
- **文件**: `src/media_tools/douyin/core/downloader_ytdlp.py:632-635`
- **问题**: 与 C1 相同，cookie 临时文件在子进程使用前被删除。

### C3. `finally` 块引用未定义变量 `cookie_file`
- **文件**: `src/media_tools/douyin/core/downloader_ytdlp.py:779-783`
- **问题**: `download_by_url_pausable()` 的 finally 块引用 `cookie_file`，但该变量从未在函数作用域中定义，实际变量名为 `cookie_path`。运行时抛出 `NameError`。

---

## HIGH — 9 个

### H1. 获取文稿时若文件不存在会删除整条资产记录
- **文件**: `src/media_tools/api/routers/assets.py:225-228`
- **问题**: `GET /api/v1/assets/{asset_id}/transcript` 在文稿文件缺失时直接 `DELETE FROM media_assets`，视频文件可能仍在，造成不可恢复的数据丢失。应仅返回 404 或将 `transcript_status` 设为 "missing"。

### H2. `asyncio.run()` 在可能有运行中事件循环时调用
- **文件**: `src/media_tools/pipeline/orchestrator_v2.py:1242`
- **问题**: `run_pipeline_batch()` 调用 `asyncio.run()`，若从异步上下文调用会崩溃 `RuntimeError`。

### H3. `update_progress_fn` 直接 await 未检查是否可等待
- **文件**: `src/media_tools/pipeline/worker.py:336`
- **问题**: 其他地方都用 `_call_progress()` 检查 `inspect.isawaitable()`，这里直接 `await`，传入同步回调会 `TypeError`。

### H4. LIKE 查询截断前缀可能匹配错误用户
- **文件**: `src/media_tools/douyin/core/downloader.py:616-618`
- **问题**: `sec_user_id[:20]` + `%` 通配符，不同用户可能共享 20 字符前缀，导致数据归错人。

### H5. `isInSearchMode` 未声明 — 运行时 ReferenceError
- **文件**: `frontend/src/pages/Inbox.tsx:455`
- **问题**: JSX 中使用 `isInSearchMode` 但该变量未在组件中定义，本地创作者选中时渲染路径会崩溃。

### H6. `InboxAuthorList` 用 `window.location.search` 代替 React Router
- **文件**: `frontend/src/pages/InboxAuthorList.tsx:11,17,52`
- **问题**: 直接读 `window.location.search` 不触发 React 重渲染，URL 通过 `navigate()` 变化后选中状态永远过期。应使用 `useSearchParams()`。

### H7. 读取不存在的 `completed_count` 属性
- **文件**: `frontend/src/pages/InboxAuthorList.tsx:46`
- **问题**: Creator 接口只有 `transcript_completed_count`，`completed_count` 不存在，侧边栏篇数永远显示 0。

### H8. WebSocket 无法关闭/清理
- **文件**: `frontend/src/store/useStore.ts:110-178`
- **问题**: 无 close 机制，组件卸载后 setTimeout 继续触发产生僵尸重连，资源泄漏。

### H9. `revokeObjectURL` 在 click 后立即调用
- **文件**: `frontend/src/lib/api.ts:66-74`
- **问题**: 浏览器可能还没开始下载 URL 就被回收，大文件或慢系统会下载失败。应延迟 revoke。

---

## MEDIUM — 22 个

### M1. 多处裸 SQLite 连接无 try/finally
- **文件**: `src/media_tools/douyin/core/downloader.py` 多处
- **问题**: 异常时连接泄漏，且绕过 `db/core.py` 统一管理。

### M2. `get_db_connection()` 函数名冲突
- **文件**: `src/media_tools/douyin/core/db_helper.py:14-46`
- **问题**: 与 `db/core.py` 同名但返回类型不同 `(conn, cursor)` vs `DBConnection`，导入错误静默崩溃。

### M3. `AccountPool._weights` 计算了但未使用
- **文件**: `src/media_tools/pipeline/orchestrator_v2.py:197-205`
- **问题**: 注释说"按权重分配"但 `get_account()` 是简单轮询，权重是死代码。

### M4. `_open_count` 无线程安全保护
- **文件**: `src/media_tools/db/core.py:85-131`
- **问题**: 多线程下计数不准，可能误报或遗漏连接泄漏。

### M5. `PipelineConfig` 默认值在类定义时调用 `get_config()`
- **文件**: `src/media_tools/pipeline/config.py:15`
- **问题**: 配置可能尚未初始化，得到错误路径。

### M6. N+1 数据库查询
- **文件**: `src/media_tools/api/routers/settings.py:196-259`
- **问题**: 每个千问账户单独开连接查询/更新。

### M7. `video_metadata` 和 `user_info_web` 不在 `init_db()` 中
- **文件**: `src/media_tools/db/core.py`
- **问题**: 重建数据库时这些表会缺失。

### M8. 异步函数中同步 DB 调用阻塞事件循环
- **文件**: `src/media_tools/pipeline/orchestrator_v2.py:598-675`
- **问题**: 并发转录时阻塞事件循环造成延迟。

### M9. Cookie 明文存入数据库
- **文件**: `src/media_tools/api/routers/settings.py`
- **问题**: 数据库泄露即暴露所有认证凭据。

### M10. 认证服务器绑定所有网络接口
- **文件**: `src/media_tools/douyin/auth_server.py:131-132`
- **问题**: 局域网任何人可提交数据。

### M11. `_complete_task`/`_fail_task` DB 写入无错误处理
- **文件**: `src/media_tools/api/routers/tasks.py:453-479`
- **问题**: DB 锁定时异常传播，WebSocket 通知不发，任务卡在 RUNNING。

### M12. `local_filename` 被设为文件夹名
- **文件**: `src/media_tools/douyin/core/downloader.py:385-389`
- **问题**: 应该是文件名，不是博主昵称。

### M13. 下载后收集所有 mp4 而非仅新增
- **文件**: `src/media_tools/douyin/core/downloader_ytdlp.py:500-504`
- **问题**: API 报告的下载数量不准确。

### M14. `get_db()` 未开启显式事务
- **文件**: `src/media_tools/db/core.py:74-82`
- **问题**: 需要原子性的路由可能数据不一致。

### M15. `fetchAssets` 无 catch 块
- **文件**: `frontend/src/pages/Inbox.tsx:70-82`
- **问题**: 错误变成 unhandled promise rejection，无用户反馈。

### M16. 乐观更新不回滚
- **文件**: `frontend/src/pages/Inbox.tsx:157-166`
- **问题**: star 切换 API 失败后 UI 状态与服务器不一致。

### M17. 硬编码 `bg-white` 破坏暗色模式
- **文件**: `frontend/src/components/layout/TaskMonitorPanel.tsx:222,271`
- **问题**: 暗色模式下任务卡片白底。

### M18. StrictMode 导致 WebSocket 双连接
- **文件**: `frontend/src/App.tsx` + `useStore.ts`
- **问题**: 开发模式下两个并行 WebSocket 连接。

### M19. 闭包捕获过期状态
- **文件**: `frontend/src/pages/Settings.tsx:257-267`
- **问题**: `handleToggleAutoTranscribe` 读到的 `autoDeleteVideo` 可能是旧值。

### M20. spread `taskUpdate` 会用 undefined 覆盖已有值
- **文件**: `frontend/src/store/useStore.ts:43-47`
- **问题**: `taskUpdate` 中的 `undefined` 字段会覆盖任务原有值。

### M21. `lastCompletedTaskTime` 变化触发不必要的 refetch
- **文件**: `frontend/src/pages/Creators.tsx:112-115`
- **问题**: 每次任务完成都 refetch，包括不相关的任务。

### M22. 关注创作者后 store 未刷新
- **文件**: `frontend/src/pages/Discovery.tsx:160-177`
- **问题**: 切换页面后数据可能过期。

---

## LOW — 12 个

### L1. 重复 `PRAGMA journal_mode=WAL`
- **文件**: `src/media_tools/douyin/core/downloader.py:78-79`

### L2. 不可达的 `return []` 死代码
- **文件**: `src/media_tools/api/routers/tasks.py:560-561`

### L3. `".."` 路径检查误判合法目录名
- **文件**: `src/media_tools/api/routers/tasks.py:32`

### L4. 批量操作无输入大小限制
- **文件**: `src/media_tools/api/routers/tasks.py`

### L5. 双重 commit
- **文件**: `src/media_tools/api/routers/tasks.py:213`

### L6. PRAGMA 用 f-string 拼接，潜在 SQL 注入
- **文件**: `src/media_tools/api/routers/creators.py:89-93`

### L7. `markAsset` 火后不理
- **文件**: `frontend/src/pages/Inbox.tsx:136`

### L8. 用原生 `confirm()` 而非 `ConfirmDialog`
- **文件**: `frontend/src/pages/Discovery.tsx:104`

### L9. 清理后用 `window.location.reload()`
- **文件**: `frontend/src/pages/Settings.tsx:728-730`

### L10. 死代码组件
- **文件**: `frontend/src/components/layout/Navbar.tsx`、`ContextualListItem.tsx`

### L11. 多处 catch 无 `console.error`
- **文件**: 多文件

### L12. 无全局 axios 错误拦截器
- **文件**: `frontend/src/lib/api.ts:7-12`

---

## 修复优先级建议

1. **C1-C3**: Cookie 临时文件删除 — 直接影响下载功能
2. **H5**: `isInSearchMode` 未声明 — 前端运行时崩溃
3. **H1**: 资产记录误删 — 不可恢复数据丢失
4. **H6-H7**: InboxAuthorList 过期状态 — 收件箱核心功能异常
5. **H8**: WebSocket 资源泄漏 — 长时间运行后内存/连接泄漏
6. **H9**: `revokeObjectURL` 过早调用 — 导出功能间歇性失败
7. **M1-M14**: 后端中等问题
8. **M15-M22**: 前端中等问题
9. **L1-L12**: 低优先级清理
