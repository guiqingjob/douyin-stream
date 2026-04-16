# B 站（UP 主投稿）全量下载 + 自动转写：设计方案（v1）

## 背景与目标

本项目当前已具备抖音创作者同步、视频下载、以及下载后自动转写（Qwen）的完整链路。需要新增 B 站（bilibili）下载能力，并与现有抖音能力在 API 调用方式、任务系统、进度展示、转写链路上保持一致的使用体验。

本方案聚焦于用户核心诉求：

- 用户粘贴 UP 主空间链接，先“关注/添加创作者”
- 默认执行“全量下载 UP 主投稿视频（UGC/BV）”
- 按 B 站“合集/系列”分组落盘，未归类视频进入“全部投稿”
- 下载清晰度默认“1080P 优先”，拿不到自动降级；Cookie 非必需，但可用于提升画质/稳定性
- 下载完成后按现有全局开关 `auto_transcribe` 决定是否自动转写

## 范围与非目标

### 范围（本期必须支持）

- 解析并支持以下输入：
  - UP 主空间：`https://space.bilibili.com/<mid>`
  - BV 视频页（用于反查作者 mid 并允许直接添加）：`https://www.bilibili.com/video/BV...`
  - 短链：`https://b23.tv/...`（跟随跳转后再归一化）
- 仅处理 UGC 投稿视频（BV/AV 所属的普通投稿）
- 默认全量下载：首次拉取下载全量投稿，二次运行增量补齐（新增 + 失败/未完成）
- 分P视频：同一 BV 下的 P1/P2/... 全部下载，文件名包含 P 序号
- 任务进度：与现有任务 WebSocket 推送兼容
- 自动转写：与现有 orchestrator 对接，受全局 `auto_transcribe` 控制

### 非目标（明确不做）

- 番剧/电影/纪录片等 PGC（`ep/ss`）自动抓取与下载
- DRM 内容处理
- 弹幕/字幕下载（可作为后续迭代）

## 总体架构

### 高层数据流

1. 前端粘贴链接 → 调用“添加创作者”API
2. 后端识别平台为 bilibili → 解析创作者标识（mid）→ 写入 `creators`（platform=bilibili）
3. 用户点击“全量同步”→ 创建任务（task_queue）→ 后台执行：
   1) 拉取该 UP 主的“合集/系列”结构与投稿列表
   2) 生成下载清单（按合集分组、含分P拆分）
   3) 下载视频到落盘目录，更新 `media_assets.video_status` 与任务进度
   4) 若 `auto_transcribe=true`：将新下载文件路径交给现有转写 orchestrator，更新 `transcript_status`
4. 前端通过 WebSocket 订阅任务更新并展示进度

### 与现有系统的集成点

- 任务与进度：复用现有 `/api/v1/tasks/*` 与 WebSocket
- 资产库：复用 `media_assets`，新增 bilibili 资产写入与状态更新
- 创作者库：复用 `creators`，利用 `platform` 区分
- 转写：复用现有 `orchestrator.transcribe_with_retry`，只要求“下载阶段产出本地文件路径列表”

## 模块划分与目录结构

新增模块与现有 `src/media_tools/douyin` 同级：

- `src/media_tools/bilibili/`
  - `__init__.py`
  - `core/`
    - `url_parser.py`：URL 归一化、类型识别（space / BV / b23）
    - `sync.py`：同步 UP 主投稿与合集结构，产出下载条目
    - `downloader.py`：yt-dlp 封装、清晰度选择、断点续传、进度回调
    - `models.py`：后端内部元数据结构（Pydantic/TypedDict）
  - `utils/`
    - `naming.py`：文件命名与路径规划
    - `cookies.py`：Cookie 解析与注入（不记录明文）

新增平台路由层（建议位置）：

- `src/media_tools/pipeline/download_router.py`：根据 URL 或 creator.platform 选择对应平台实现（douyin/bilibili）

## URL 解析与创作者添加

### 识别规则

按域名/路径快速判断：

- `space.bilibili.com/<mid>` → 直接解析 mid
- `www.bilibili.com/video/<bvid>` → 解析 bvid，随后通过 yt-dlp 提取 info 获取 uploader_id（mid）与 uploader
- `b23.tv/<code>` → HEAD/GET 跟随跳转，得到最终 URL，再走上述规则

### 创作者 ID 与跨平台去重

现有 `creators.uid` 是主键且用于 `media_assets.creator_uid` 外键语义。为避免不同平台 uid 可能冲突，本方案采用“带平台前缀”的逻辑主键：

- bilibili 创作者 uid：`bilibili:<mid>`
- douyin 保持现状（不改历史数据）

写入字段：

- `creators.uid`：`bilibili:<mid>`
- `creators.sec_user_id`：可存 mid（字符串）或留空（用于兼容字段，不作为核心）
- `creators.platform`：`bilibili`
- `creators.nickname/avatar/bio`：从 yt-dlp 的 extractor 或公开页面信息补齐

## 同步与下载清单生成（按合集分组）

### 分组策略

优先按 B 站“合集/系列/列表”分组：

- 如果某投稿属于某合集：落到 `<UP>/<合集名>/`
- 否则：落到 `<UP>/全部投稿/`

若合集结构无法稳定获取（例如 extractor 不提供或网络异常），则降级：

- 全部落到 `<UP>/全部投稿/`

### 分P处理

对多P视频：

- 每个 P 作为一个“下载单元”（产出一个本地视频文件）
- 仍归属到同一个合集目录
- 文件名包含 `P{index}` 与分P标题（可选）

### 增量规则

以 `media_assets.asset_id` 去重：

- bilibili 单视频（单P）：`bilibili:<bvid>`
- bilibili 多P：`bilibili:<bvid>:p<index>`（index 从 1 开始）

同步时：

- 若 asset_id 已存在且 `video_status=downloaded`：跳过
- 若 asset_id 存在但失败/未完成：加入下载队列重试
- 若不存在：创建新资产并下载

## 下载实现（yt-dlp）

### 依赖策略

- 后端新增 Python 依赖：`yt-dlp`
- 系统依赖：`ffmpeg`（用于 DASH 音视频合并）

若运行环境缺少 ffmpeg：

- 记录明确错误提示（告知安装 ffmpeg）
- 不做静默失败

### 清晰度策略（1080P 优先 + 自动降级）

默认格式选择策略：

- 目标：1080P（含 1080P+）优先
- 若不可用：自动选择次高（720P/480P/360P），保证“夜间任务能跑完”

Cookie 行为：

- 不配置 Cookie：尝试下载公开投稿的可用清晰度
- 配置 Cookie：用于提升 formats 列表可用性与可用清晰度上限

### 断点续传

启用断点续传并确保可恢复：

- 保存 `.part` 临时文件与下载状态
- 若直链过期导致失败：重新解析 formats 后继续下载

### 进度回调

将 yt-dlp 进度转换为统一回调：

- `progress`：0~1
- `msg`：当前下载/合并/后处理阶段描述

上报通道：复用现有任务 WebSocket 广播。

## 转写对接（下载后自动转写）

### 行为定义

下载完成后，若 `auto_transcribe=true`：

- 将新下载文件（本地绝对路径）交给现有 orchestrator 执行 `transcribe_with_retry`
- 转写成功可选删除源视频（沿用现有 `auto_delete_video` 逻辑）

若 `auto_transcribe=false`：

- 只下载，不触发转写

### 转写归属与资产更新

对于每个下载单元（asset_id）：

- `media_assets.video_path`：相对 download 根目录的路径
- `media_assets.video_status`：`downloaded/failed/pending`
- `media_assets.transcript_path` / `transcript_status`：沿用现有转写产物管理

## API 与 UI 变更（保持体验一致）

### API

- 复用现有：
  - `POST /api/v1/creators/`：扩展支持 bilibili 链接（后端按链接识别平台）
  - `POST /api/v1/tasks/download/creator`：对 bilibili creator_uid 调用 bilibili 同步下载
  - `POST /api/v1/tasks/download/full-sync`：扩展为“全平台全量同步”或保持抖音不变（本期建议先保持抖音不变，另加 bilibili 的全量同步入口）
  - `POST /api/v1/tasks/pipeline`：如传入 bilibili URL，走 bilibili 下载 + 转写

新增（建议）：

- `GET /api/v1/bilibili/metadata?url=...`：用于前端在添加前预览（UP 信息、视频数量、合集概览、可用清晰度策略提示）
- `POST /api/v1/settings/bilibili`：添加 bilibili cookie 到账号池
- `DELETE /api/v1/settings/bilibili/{account_id}`：移除 bilibili cookie

### UI

- Creators 页面：
  - 输入框文案改为“粘贴抖音/B站主页链接添加创作者”
  - 对 bilibili creator 仍显示“增量同步/全量同步”按钮，体验一致
- Settings 页面：
  - 增加 “Bilibili 账号池” 区块（与抖音同样的 Cookie 添加/备注/移除交互）

## 配置与安全

- Cookie 属于敏感凭证：
  - 不写入日志
  - 不写入任务 payload
  - API 返回不回显 cookie
- 下载路径必须进行路径安全校验，避免目录穿越（沿用现有 `_resolve_safe_path` 风格）
- 限速与并发：
  - 复用全局 `concurrency` 配置控制下载并发，减少风控风险
  - 失败重试采用退避策略（指数退避 + 最大次数）

## 测试计划

### 单元测试

- URL 解析：space/BV/b23/m 站链接归一化
- asset_id 生成：单P/多P唯一性与稳定性
- 命名规则：非法字符清理、重名策略
- 任务进度映射：yt-dlp progress hook → 统一 progress

### 集成测试

- 使用一个公开视频 UP 主空间链接：
  - 首次全量下载
  - 二次增量下载（无新增应快速完成）
  - 故意中断后续传（断点续传）
- auto_transcribe=true：
  - 下载后触发转写
  - 转写成功后自动删除视频（若开启）

## 交付物

- bilibili 模块（UGC 投稿）全量/增量下载能力
- 与抖音一致的任务/进度/转写体验
- Settings 增加 bilibili cookie 管理
- 设计文档与测试覆盖

