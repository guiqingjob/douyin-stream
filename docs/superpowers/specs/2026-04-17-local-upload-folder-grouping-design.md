# 本地上传按文件夹分组展示（设计）

## 背景与问题

当前“本地上传”素材会全部归入同一个创作者（`local:upload`）下展示，导致大量素材混在同一列表中，难以定位来源文件夹与归属。

## 目标

- 以“发现页输入的扫描目录”为根目录，对本地上传素材进行文件夹层级分组展示。
- 左侧创作者列表仍保留单一创作者“本地上传”（不拆分多个本地创作者）。
- 不增加额外说明文案，仅提供可用的分组浏览结构。

## 非目标

- 不修改现有 Douyin/Bilibili 素材的归类逻辑。
- 不引入额外的上传批次/标签 UI（本迭代只按目录分组）。

## 数据模型变更

### media_assets 增加字段

- 新增列：`folder_path TEXT DEFAULT ''`
- 含义：素材所在目录相对于本次扫描根目录的相对路径（POSIX 风格，使用 `/` 分隔）。
  - 文件位于根目录：`folder_path = ''`
  - 文件位于子目录：`folder_path = '章节1/音频'`
  - 文件不在根目录下（异常情况）：`folder_path = '(其他)'`

### DB 迁移策略

使用现有 `_ensure_column(...)` 机制在启动时自动补列：
- `_ensure_column(conn, "media_assets", "folder_path", "TEXT DEFAULT ''")`

## API 变更

### 本地转写触发接口

现有：`POST /api/v1/tasks/transcribe/local`

新增请求字段：
- `directory_root: str | None`
  - 来自“发现页”的扫描目录输入
  - 作为本地文件分组的根

后端处理：
- `_register_local_assets(...)` 接收 `directory_root`，为每个 file_path 计算并写入 `folder_path`
- 仍使用现有 `asset_id = sha1(resolve(file_path))` 方案保证去重

### 素材列表接口

现有：`GET /api/v1/assets/?creator_uid=...`

变更：
- SELECT 字段加入 `folder_path`
- 响应中返回 `folder_path`，供前端分组渲染使用

## folder_path 计算规则

输入：
- `file_path`: 本地文件绝对路径
- `directory_root`: 本次扫描根目录（绝对路径）

步骤：
1. 对 `file_path`、`directory_root` 分别 `Path(...).resolve()`
2. 若 `file_path` 在 `directory_root` 下：
   - `relative_dir = file_path.parent.relative_to(directory_root)`
   - `folder_path = relative_dir.as_posix()`（根目录下则为空字符串）
3. 否则：
   - `folder_path = '(其他)'`

## 前端变更

### 发现页：提交本地转写时带上 directory_root

现有前端仅提交 `file_paths` 与 `delete_after`：
- `triggerLocalTranscribe(file_paths, delete_after)`

变更：
- 额外传 `directory_root = localDir`（发现页输入框）

### 收件箱：按 folder_path 分组展示

当选中的 creator_uid 为 `local:upload` 时：
- 将 assets 按 `folder_path` 分组
- 渲染为“可折叠分组列表”
  - 组标题：`folder_path`（空字符串组可显示为“根目录”或空组置顶）
  - 展开后：列出该组的文件资产卡片（沿用现有卡片 UI）

其他 creator_uid（抖音/B站等）保持原样列表展示。

## 兼容性与回填策略

- 对历史的本地素材（无 `folder_path`）：
  - 继续归入空字符串组（根目录组），保证可见性
- 对跨根目录选择文件（少见）：
  - 不在 `directory_root` 下的文件归入 `'(其他)'`

## 测试策略

后端（pytest）：
- 新增单测覆盖：
  - `_register_local_assets` 在给定 `directory_root` 时写入正确的 `folder_path`
  - `GET /assets?creator_uid=local:upload` 返回字段包含 `folder_path`

前端：
- 构建校验：`npm run build`
- 手动验证：
  - 扫描包含子目录的本地根目录
  - 触发本地转写
  - Inbox 选择“本地上传”，按目录分组可展开查看文件

