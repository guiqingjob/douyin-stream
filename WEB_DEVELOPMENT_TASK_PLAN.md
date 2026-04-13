# Web 管理面板完整开发任务文档

> **项目**: Media Tools - Streamlit Web 管理面板
> **分支**: `feature/streamlit-web`
> **技术栈**: Streamlit + Python Threading + JSON 状态文件轮询
> **创建时间**: 2026-04-13

---

## 一、项目架构

### 1.1 目录结构

```
media-tools/
├── web_app.py                           # Streamlit 主入口（7个页面路由）
├── web/
│   ├── __init__.py
│   ├── components/                      # 可复用组件（4个）
│   │   ├── auth_status.py              # 认证状态卡片
│   │   ├── progress_display.py         # 进度显示
│   │   ├── stats_panel.py              # 统计面板
│   │   └── task_queue.py               # 后台任务队列
│   └── pages/                           # 页面模块（7个）
│       ├── dashboard.py                # 仪表盘
│       ├── following.py                # 关注管理
│       ├── download.py                 # 下载任务
│       ├── transcribe.py               # 转写任务
│       ├── accounts.py                 # 账号管理
│       ├── cleanup.py                  # 数据清理
│       └── settings.py                 # 系统设置
├── scripts/                             # 抖音下载核心模块
│   ├── core/
│   │   ├── cleaner.py                  # 数据清理
│   │   ├── db_helper.py                # 数据库操作
│   │   ├── downloader.py               # 视频下载
│   │   ├── following_mgr.py            # 关注管理
│   │   └── env_check.py                # 环境检测
│   └── utils/
├── src/media_tools/                     # Python 包
│   ├── transcribe/                      # Qwen 转写模块
│   │   ├── orchestrator_v2.py          # Pipeline 编排
│   │   └── quota.py                    # 配额管理
│   └── config_manager.py               # 配置管理
└── .auth/                               # 认证状态
    └── qwen-storage-state.json         # Qwen 认证文件
```

### 1.2 技术架构

- **UI 框架**: Streamlit（声明式 UI，每次交互重新渲染）
- **后台任务**: `threading.Thread`（非 asyncio，非多进程）
- **任务状态**: 单文件 `.task_state.json`（轮询机制，2秒刷新）
- **数据持久化**: JSON 文件 + SQLite（下载元数据）
- **路径约定**: 
  - 项目根目录: `/path/to/media-tools`
  - 下载目录: `downloads/`
  - 转写目录: `transcripts/`
  - 临时文件: `temp_uploads/`

---

## 二、已知问题清单（按优先级排序）

### 🔴 P0 - 严重问题（必须修复）

#### P0-1: 数据库清理功能为空操作
- **文件**: `web/pages/cleanup.py` 第 64 行
- **问题描述**: 
  ```python
  # 当前代码
  if st.button("清理过期数据库记录", key="clean_db"):
      st.warning("此操作将删除数据库中的过期记录，确定继续？")
      # 这里可以接入实际的清理逻辑  ← 注释说明了功能未完成
      st.success("数据库清理完成")
  ```
- **影响**: 用户误以为已清理，实际数据库未变化
- **修复方案**:
  1. 调用 `scripts.core.db_helper` 或 `scripts.core.cleaner` 中的实际清理函数
  2. 查看 `scripts/core/cleaner.py` 中是否有 `clean_db_records()` 或类似函数
  3. 若无现成函数，查看 `db_helper.py` 中的数据库操作，实现清理逻辑
  4. 清理后应显示统计信息（清理了多少条记录，释放了多少空间）

#### P0-2: 任务队列竞态条件
- **文件**: `web/components/task_queue.py`
- **问题描述**: 
  - `load_task_state()` 和 `save_task_state()` 无锁保护
  - 多线程同时调用 `update_task_progress()` 可能导致状态丢失
- **影响**: 任务进度更新可能丢失，显示错误状态
- **修复方案**:
  ```python
  import threading
  
  # 在文件顶部添加
  _state_lock = threading.Lock()
  
  # 修改 load_task_state()
  def load_task_state():
      with _state_lock:
          # 原有逻辑
          pass
  
  # 修改 save_task_state()
  def save_task_state(state):
      with _state_lock:
          # 原有逻辑
          pass
  ```

#### P0-3: 临时文件未清理（磁盘泄漏）
- **文件**: `web/pages/transcribe.py` 第 37-41 行
- **问题描述**: 
  - 用户上传文件到 `temp_uploads/` 后，转写完成但文件未删除
  - 多次使用后占用大量磁盘空间
- **修复方案**:
  1. 在 `_start_transcribe_task()` 成功后，添加清理逻辑：
     ```python
     import os
     
     # 转写完成后
     try:
         os.remove(temp_file_path)
         st.info(f"已清理临时文件: {temp_file_path}")
     except Exception as e:
         st.warning(f"临时文件清理失败: {e}")
     ```
  2. 或在 `settings.py` 中添加定期清理 `temp_uploads/` 的功能

---

### 🟡 P1 - 中等问题（重要改进）

#### P1-1: 批量操作错误统计缺失
- **文件**: 
  - `web/pages/download.py` - 批量下载关注
  - `web/pages/transcribe.py` - 批量转写
- **问题描述**: 
  ```python
  # 当前代码（download.py）
  for user in users:
      try:
          download_by_url(user["url"], max_counts=max_count)
      except Exception:
          pass  # ← 静默失败，用户不知道哪些失败了
  ```
- **修复方案**:
  ```python
  success_list = []
  failed_list = []
  
  for user in users:
      try:
          download_by_url(user["url"], max_counts=max_count)
          success_list.append(user["nickname"])
      except Exception as e:
          failed_list.append({"user": user["nickname"], "error": str(e)})
  
  # 显示统计
  st.success(f"✅ 成功: {len(success_list)} 个")
  if failed_list:
      st.error(f"❌ 失败: {len(failed_list)} 个")
      with st.expander("查看失败详情"):
          for item in failed_list:
              st.warning(f"{item['user']}: {item['error']}")
  ```

#### P1-2: 重复代码统一
- **问题 1**: 认证检查逻辑在 3 个文件中重复
  - `web/components/auth_status.py`
  - `web/pages/settings.py` - `_check_douyin_auth()` 和 `_check_qwen_auth()`
  - `web/pages/dashboard.py` - 环境检测中的认证检查
  
  **修复**: 统一调用 `auth_status.py` 中的组件函数

- **问题 2**: 环境检测逻辑不一致
  - `dashboard.py`: 调用 `check_all()` 一次性检测
  - `settings.py`: 逐项调用独立检查函数并分别显示
  
  **修复**: 
  - 仪表盘页面保留 `check_all()`（快速检测）
  - 设置页面保留逐项检测（详细诊断）
  - 在代码注释中说明差异原因

- **问题 3**: 文件大小格式化重复
  - `web/pages/cleanup.py` - `_format_size()`
  - `web/components/stats_panel.py` - 内联计算
  
  **修复**: 提取到 `web/utils.py` 或 `web/components/__init__.py`

#### P1-3: 硬编码路径统一
- **问题**: `.auth/qwen-storage-state.json` 在 4 个文件中硬编码
  - `web/pages/transcribe.py`
  - `web/pages/settings.py`
  - `web/pages/accounts.py`
  - `web/components/auth_status.py`
- **修复方案**: 创建 `web/constants.py`
  ```python
  # web/constants.py
  from pathlib import Path
  
  PROJECT_ROOT = Path(__file__).parent.parent
  QWEN_AUTH_PATH = PROJECT_ROOT / ".auth" / "qwen-storage-state.json"
  DOUYIN_COOKIE_PATH = PROJECT_ROOT / ".auth" / "douyin-cookie.json"
  TEMP_UPLOADS_DIR = PROJECT_ROOT / "temp_uploads"
  DOWNLOADS_DIR = PROJECT_ROOT / "downloads"
  TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"
  TASK_STATE_FILE = PROJECT_ROOT / ".task_state.json"
  ```

#### P1-4: 任务取消机制缺失
- **文件**: `web/components/task_queue.py`
- **问题**: 任务一旦启动无法取消
- **修复方案**:
  ```python
  import threading
  
  # 添加取消标志
  _cancel_flag = threading.Event()
  
  def cancel_task():
      """取消当前任务"""
      _cancel_flag.set()
  
  def is_task_cancelled():
      """检查是否取消"""
      return _cancel_flag.is_set()
  
  def reset_cancel_flag():
      """重置取消标志"""
      _cancel_flag.clear()
  
  # 在 run_task_in_background() 中定期检查
  def run_task_in_background(task_name, task_func, *args, **kwargs):
      reset_cancel_flag()  # 启动时重置
      
      def wrapper():
          try:
              # 在长时间运行的循环中检查
              if is_task_cancelled():
                  mark_task_failed(task_name, "任务已取消")
                  return
              task_func(*args, **kwargs)
          except Exception as e:
              mark_task_failed(task_name, str(e))
      
      thread = threading.Thread(target=wrapper)
      thread.start()
  ```

#### P1-5: `st.json()` 序列化风险
- **文件**: 
  - `web/components/progress_display.py` 第 41 行
  - `web/pages/accounts.py` 第 27 行
- **问题**: 当 `state["result"]` 包含不可序列化对象（Path、自定义类）时会崩溃
- **修复方案**:
  ```python
  def safe_json_display(data):
      """安全的 JSON 显示"""
      try:
          st.json(data)
      except TypeError as e:
          st.warning(f"JSON 序列化失败，显示为文本: {e}")
          st.code(str(data))
  ```

---

### 🟢 P2 - 轻微问题（优化改进）

#### P2-1: 删除操作无确认弹窗
- **文件**: `web/pages/following.py` - 删除用户按钮
- **修复**:
  ```python
  # 当前代码
  if st.button("删除", key=f"del_{uid}"):
      delete_user(uid)
  
  # 修改为
  if st.button("删除", key=f"del_{uid}"):
      if st.checkbox(f"确认删除用户 {nickname}?", key=f"confirm_{uid}"):
          delete_user(uid)
          st.success("已删除")
  ```

#### P2-2: 异常静默失败（缺少日志）
- **位置**: 多处 `except Exception: pass`
  - `web/components/stats_panel.py` - 关注数获取失败
  - `web/pages/download.py` - 单个下载失败
  - `web/pages/transcribe.py` - 单个转写失败
- **修复**: 至少添加 `st.error()` 或 `import logging; logging.error()`

#### P2-3: 统计面板性能优化
- **文件**: `web/components/stats_panel.py`
- **问题**: 每次渲染都遍历整个 `downloads/` 和 `transcripts/` 目录
- **修复**: 添加缓存
  ```python
  import streamlit as st
  
  @st.cache_data(ttl=60)  # 60秒缓存
  def get_cached_stats():
      return _get_stats()
  
  def render_stats_panel():
      stats = get_cached_stats()
      # 使用缓存的 stats
  ```

#### P2-4: 预设模板外部化
- **文件**: `web/pages/settings.py` - `presets` 字典硬编码
- **修复**: 从 `config.yaml` 或独立 `presets.json` 加载

---

## 三、修改计划（分阶段执行）

### 阶段 1: 修复严重问题（P0）

**目标**: 修复功能缺失和数据安全问题

| 序号 | 任务 | 文件 | 预计改动 | 状态 |
|------|------|------|----------|------|
| 1.1 | 实现数据库清理逻辑 | `web/pages/cleanup.py` | +30 行 | 完成 |
| 1.2 | 添加任务队列锁 | `web/components/task_queue.py` | +10 行 | 完成 |
| 1.3 | 临时文件自动清理 | `web/pages/transcribe.py` | +15 行 | 完成 |

**验收标准**:
- [x] 数据库清理功能真正执行了清理操作，并显示统计
- [x] 并发更新任务状态时无数据丢失
- [x] 转写完成后临时文件被删除

---

### 阶段 2: 提升用户体验（P1 核心）

**目标**: 批量操作反馈、任务取消、路径统一

| 序号 | 任务 | 文件 | 预计改动 | 状态 |
|------|------|------|----------|------|
| 2.1 | 批量下载错误统计 | `web/pages/download.py` | +20 行 | 完成 |
| 2.2 | 批量转写错误统计 | `web/pages/transcribe.py` | +20 行 | 完成 |
| 2.3 | 创建 constants.py | `web/constants.py` (新文件) | +15 行 | 完成 |
| 2.4 | 替换所有硬编码路径 | 4 个页面文件 | 修改 10+ 处 | 完成 |
| 2.5 | 任务取消机制 | `web/components/task_queue.py` | +30 行 | 完成 |
| 2.6 | 安全 JSON 序列化 | `web/components/progress_display.py` | +10 行 | 完成 |

**验收标准**:
- [x] 批量操作显示成功/失败统计报告
- [x] 用户可以取消正在运行的任务
- [x] 所有路径从 constants.py 统一管理
- [x] 复杂对象显示不会导致页面崩溃

---

### 阶段 3: 代码质量提升（P1 剩余 + P2）

**目标**: 重构重复代码，统一配置，增强健壮性

| 序号 | 任务 | 文件 | 预计改动 | 状态 |
|------|------|------|----------|------|
| 3.1 | 删除操作确认 | `web/pages/following.py` | +5 行 | 完成 |
| 3.2 | 异常日志记录 | 多处 | 修改 5+ 处 | 完成 |
| 3.3 | 统计面板缓存 | `web/components/stats_panel.py` | +5 行 | 完成 |
| 3.4 | 提取文件大小格式化 | `web/utils.py` (新文件) | +10 行 | 完成 |
| 3.5 | 统一认证检查调用 | 3 个页面文件 | 删除重复代码 | 完成 |

**验收标准**:
- [x] 无重复代码（通过 grep 验证）
- [x] 删除操作有确认步骤
- [x] 所有异常都有日志记录
- [x] 统计面板响应速度提升（缓存命中）

---

### 阶段 4: 性能优化（P2 剩余）

**目标**: 预设外部化、整体优化

| 序号 | 任务 | 文件 | 预计改动 | 状态 |
|------|------|------|----------|------|
| 4.1 | 预设模板外部化 | `config.yaml` + `settings.py` | +20 行 | 完成 |
| 4.2 | 代码审查和优化 | 全部 | 重构 | 完成 |

---

## 四、执行指南

### 4.1 启动开发环境

```bash
cd /path/to/media-tools
source .venv/bin/activate  # 如果有虚拟环境
streamlit run web_app.py --server.port 8501
```

### 4.2 测试每个修改

修改完成后，手动测试对应功能：

1. **数据库清理**: 先在数据库制造一些过期记录，然后执行清理
2. **任务队列**: 同时提交两个任务，观察状态更新
3. **临时文件**: 转写一个文件，检查 `temp_uploads/` 是否清空
4. **批量操作**: 批量下载/转写时故意制造失败，观察统计
5. **任务取消**: 启动一个长时间任务，测试取消按钮
6. **路径统一**: 移动 `.auth/` 目录，验证所有页面仍正常工作

### 4.3 提交规范

每个阶段完成后单独提交：

```bash
git add <修改的文件>
git commit -m "fix(web): [阶段编号] [简短描述]

详细说明修改内容
"
```

示例：
```bash
git commit -m "fix(web): P0-1 实现数据库清理功能

- 调用 scripts.core.cleaner.clean_db_records()
- 显示清理统计（删除记录数、释放空间）
- 添加操作确认弹窗
"
```

---

## 五、参考资料

### 5.1 关键模块路径

| 功能 | 文件路径 |
|------|----------|
| 数据库清理 | `scripts/core/cleaner.py`、`scripts/core/db_helper.py` |
| 下载功能 | `scripts/core/downloader.py` |
| 关注管理 | `scripts/core/following_mgr.py` |
| 环境检测 | `scripts/core/env_check.py` |
| Pipeline 编排 | `src/media_tools/pipeline/orchestrator_v2.py` |
| 配额管理 | `src/media_tools/transcribe/quota.py` |

### 5.2 配置示例

```yaml
# config.yaml
cookie:
  auto_extract: true
  manual: ""

download_path: ""
naming: "{desc}_{aweme_id}"

incremental:
  enabled: true

compression:
  auto_compress: false
  crf: 32
  preset: "fast"
  replace_original: true
  skip_small_threshold: 5242880
```

### 5.3 测试报告摘要

- 总测试项: 500+
- 通过率: 98%+
- 唯一 FAIL: `classify_error` 超时分类错误（`orchestrator_v2.py:72-82`）
- Web 界面测试: 尚未独立设计（现有测试针对 CLI）

---

## 六、常见问题排查

### Q1: 任务状态不更新
- 检查 `.task_state.json` 是否存在且可写
- 检查后台线程是否正常运行（无异常被吞掉）
- 查看 `task_queue.py` 中的 `update_task_progress()` 日志

### Q2: Streamlit 页面刷新后状态丢失
- 这是 Streamlit 的正常行为（每次交互重新运行脚本）
- 确保使用 `st.session_state` 持久化状态
- 任务状态应从 `.task_state.json` 读取而非内存变量

### Q3: 认证检查始终失败
- 确认 `.auth/qwen-storage-state.json` 存在
- 确认 Cookie 未过期
- 查看 `auth_status.py` 中的检测逻辑

### Q4: 批量操作卡顿
- 检查是否缺少统计面板缓存（`@st.cache_data`）
- 检查 `downloads/` 目录文件数量（1000+ 会显著影响性能）

---

## 七、任务检查清单（Agent 中断后恢复用）

如果任务被中断，按此清单检查进度：

### 阶段 1 检查
- [x] P0-1: `web/pages/cleanup.py` 数据库清理是否已实现？
- [x] P0-2: `web/components/task_queue.py` 是否添加了 `_state_lock`？
- [x] P0-3: `web/pages/transcribe.py` 临时文件是否已清理？

### 阶段 2 检查
- [x] P1-1: `web/pages/download.py` 批量下载是否有错误统计？
- [x] P1-1: `web/pages/transcribe.py` 批量转写是否有错误统计？
- [x] P1-2: 是否创建了 `web/constants.py`？
- [x] P1-2: 所有硬编码路径是否已替换为常量？
- [x] P1-4: `web/components/task_queue.py` 是否支持取消？
- [x] P1-5: `st.json()` 调用是否有安全包装？

### 阶段 3 检查
- [x] P2-1: `web/pages/following.py` 删除操作是否有确认？
- [x] P2-2: 所有 `except Exception: pass` 是否添加了日志？
- [x] P2-3: `web/components/stats_panel.py` 是否有缓存？
- [x] P1-2: 重复代码（认证检查、环境检测）是否已统一？
- [x] P1-2: 文件大小格式化是否提取为公共函数？

### 阶段 4 检查
- [x] P2-4: 预设模板是否外部化？
- [x] 整体代码审查是否完成？

---

## 八、最终验收标准

全部完成后，Web 应用应满足：

### 功能完整性
- ✅ 7 个页面均可正常访问且功能完整
- ✅ 4 个组件均可正常复用
- ✅ 后台任务支持：提交、进度显示、取消、完成通知
- ✅ 批量操作提供详细成功/失败统计

### 代码质量
- ✅ 无重复代码（通过 `grep` 验证）
- ✅ 无硬编码路径（全部从 constants.py 读取）
- ✅ 所有外部调用均有异常处理
- ✅ 所有异常均有日志记录

### 性能
- ✅ 统计面板使用缓存（响应时间 < 2秒）
- ✅ 任务状态更新无竞态条件
- ✅ 临时文件自动清理（无磁盘泄漏）

### 用户体验
- ✅ 删除操作有确认步骤
- ✅ 批量操作有进度条和统计报告
- ✅ 任务可取消
- ✅ 错误信息清晰可操作

---

**文档版本**: v1.0  
**最后更新**: 2026-04-13  
**维护者**: 开发团队
