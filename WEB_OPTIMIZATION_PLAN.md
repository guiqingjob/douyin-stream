# Media Tools Web 管理面板 - 持续优化规划

> **项目状态**: 基础功能完整，存在代码质量和技术债务问题
> **创建时间**: 2026-04-13
> **最后更新**: 2026-04-13

---

## 一、项目现状总结

### ✅ 已完成功能
- 7 个页面 + 4 个组件完整实现
- 所有核心模块导入正常（11 个关键模块验证通过）
- 认证文件、数据库、配置文件就绪
- 环境检测、关注管理、账号管理等基础功能可用
- 后台任务队列机制（基于 JSON 文件轮询）

### ⚠️ 主要问题
- **代码重复**：`scripts/core/` 和 `src/media_tools/douyin/core/` 有 14 个完全相同的文件
- **路径混乱**：Web 页面混用 `scripts.core.*` 和 `media_tools.douyin.core.*`
- **关键 Bug**：`orchestrator_v2.py` 第 716 行引用错误导致批量转写崩溃
- **功能未生效**：进度组件已实现但未被调用

---

## 二、优化规划（按优先级排序）

### 🔴 P0 - 严重问题（必须立即修复）

#### P0-1: 消除代码重复（最高优先级）

**问题**: 
- `scripts/core/` 14 个文件与 `src/media_tools/douyin/core/` 完全相同
- 总约 3957 行重复代码
- 修改一处不会同步到另一处

**影响**: 
- 维护成本高，容易遗漏
- Web 页面用旧路径，CLI 可能用新路径，行为不一致

**修复方案**:
1. 删除 `scripts/core/` 目录（保留 `scripts/` 下的工具脚本如 `run_download.py`, `auth_server.py`）
2. 所有 `scripts.core.*` 引用改为 `media_tools.douyin.core.*`
3. 如果 CLI 仍需要 `scripts/`，创建符号链接指向 `src/media_tools/douyin/`

**涉及文件**:
- 删除: `scripts/core/*.py` (14 个文件)
- 修改: `web/pages/download.py`, `web/pages/cleanup.py` (6 处导入)

---

#### P0-2: 修复 orchestrator_v2.py 关键 Bug

**问题**: 
```python
# src/media_tools/pipeline/orchestrator_v2.py:716-719
for path_str, state in self.state_mgr.states.items():  # ❌ state_mgr 不存在
    if state.status == VideoStatus.RUNNING:            # ❌ VideoStatus 未定义
```

**影响**: 批量转写失败时二次崩溃

**修复方案**:
```python
# 方案 1: 修正引用
for path_str, state in self.state_manager.states.items():
    if state.status == "running":

# 方案 2: 删除这段无用的 fallback 逻辑
```

**工作量**: 修改 3 行代码

---

#### P0-3: 修复 Web 页面旧路径引用

**问题**: 
- `web/pages/download.py` 3 处使用 `scripts.core.*`
- `web/pages/cleanup.py` 3 处使用 `scripts.core.*`

**修复**:
```python
# download.py
- from scripts.core.downloader import download_by_url
+ from media_tools.douyin.core.downloader import download_by_url

- from scripts.core.update_checker import check_all_updates
+ from media_tools.douyin.core.update_checker import check_all_updates

# cleanup.py
- from scripts.core.cleaner import clean_deleted_videos
+ from media_tools.douyin.core.cleaner import clean_deleted_videos

- from scripts.core.db_helper import execute_query
+ from media_tools.douyin.core.db_helper import execute_query
```

---

#### P0-4: 任务进度组件未被调用

**问题**: 
- `download.py` 和 `transcribe.py` 导入了 `render_task_progress`
- 但页面中从未调用过，用户看不到进度条

**修复**: 在页面主渲染函数中添加调用
```python
# download.py 的 render_download() 末尾
render_task_progress()

# transcribe.py 的 render_transcribe() 末尾
render_task_progress()
```

---

### 🟡 P1 - 重要改进（用户体验提升）

#### P1-1: task_queue.py 使用绝对路径

**问题**: 
```python
_STATE_FILE = Path(".task_state.json")  # 相对路径，位置不确定
```

**修复**:
```python
_STATE_FILE = Path(__file__).parent.parent / ".task_state.json"  # 项目根目录
```

---

#### P1-2: 创建 config/transcribe/accounts.json

**问题**: 只有 `accounts.example.json`，账号管理页面 fallback 到默认模式

**修复**:
```bash
cp config/transcribe/accounts.example.json config/transcribe/accounts.json
```

---

#### P1-3: 改进删除用户交互

**问题**: 当前需要勾选确认框 + 点击删除按钮，操作繁琐

**修复**: 使用 `st.confirm()` 弹窗确认
```python
# 当前
confirm_delete = st.checkbox("确认删除 XXX？")
if st.button("删除选中", disabled=not confirm_delete):
    ...

# 修改为
if st.button("删除", type="primary"):
    if st.confirm(f"确认删除用户 {nickname}？"):
        remove_user(uid)
        st.success("已删除")
```

---

#### P1-4: 批量操作实时进度反馈

**问题**: 用户需要手动刷新页面才能看到进度

**修复方案**:
1. 在批量操作循环中定期更新 `.task_state.json`
2. 前端使用 `st.empty()` + 定时刷新显示进度
3. 或使用 WebSocket/Server-Sent Events（复杂）

**简单方案**:
```python
# 在批量下载循环中
for i, user in enumerate(users):
    progress = (i + 1) / len(users)
    update_task_progress("batch_download", progress=progress, 
                        message=f"正在下载 {user['nickname']}...")
    st.rerun()  # 触发页面刷新
```

---

#### P1-5: 错误历史查看

**问题**: 任务失败后错误信息一闪而过，无法回溯

**修复**: 
1. 创建 `.task_history.jsonl` 文件记录所有任务
2. 添加"查看任务历史"按钮
3. 显示最近 10 个任务的状态和错误信息

---

### 🟢 P2 - 优化改进（代码质量提升）

#### P2-1: 重构 stats_panel.py 缓存逻辑

**问题**: 嵌套缓存设计复杂且不必要

**当前代码**:
```python
@st.cache_data(ttl=60)
def _get_cached_stats():
    return _get_stats_internal()

def _get_stats() -> dict:
    return _get_cached_stats()
```

**修复**: 简化为单层缓存
```python
@st.cache_data(ttl=60)
def get_stats() -> dict:
    # 直接实现统计逻辑
    ...
```

---

#### P2-2: 统一 Cookie/认证管理

**问题**: 
- Cookie 存储在 `config/config.yaml`
- 认证状态在 `.auth/` 目录
- 两套体系可能不一致

**修复方案**: 
1. 统一使用 `.auth/` 目录存储所有认证信息
2. `config.yaml` 中只保留引用路径
3. 添加认证状态同步机制

---

#### P2-3: 添加新手引导

**问题**: 首次访问用户不知道如何使用

**修复方案**:
1. 检测首次访问（创建 `.first_visit` 标记文件）
2. 显示引导流程：
   - 步骤 1: 环境检测
   - 步骤 2: 配置 Cookie
   - 步骤 3: 添加关注博主
   - 步骤 4: 开始下载
3. 每步都有详细说明和示例

---

#### P2-4: 使用 st.navigation 替代 st.radio

**问题**: 当前使用 `st.radio` + `session_state` 手动实现页面切换

**修复**:
```python
# 当前
page = st.radio("导航", PAGES, index=page_idx)

# 修改为（Streamlit 1.40+）
pg = st.navigation([
    st.Page(render_dashboard, title="仪表盘"),
    st.Page(render_following, title="关注管理"),
    ...
])
pg.run()
```

---

#### P2-5: 添加数据导入/导出功能

**问题**: 关注列表只有 JSON 导入/导出，缺少备份功能

**修复**:
1. 添加"备份所有数据"按钮（following.json + 数据库 + 配置）
2. 支持一键恢复
3. 定期自动备份（cron 或定时任务）

---

## 三、执行计划

### 阶段 1: 修复严重问题（1-2 小时）

| 任务 | 预计时间 | 负责人 | 状态 |
|------|----------|--------|------|
| P0-1: 消除代码重复 | 30 分钟 | Agent | 完成 |
| P0-2: 修复 orchestrator_v2.py Bug | 10 分钟 | Agent | 完成 |
| P0-3: 修复 Web 页面旧路径引用 | 15 分钟 | Agent | 完成 |
| P0-4: 调用任务进度组件 | 10 分钟 | Agent | 完成 |

**验收标准**:
- [x] `scripts/core/` 目录已删除或创建符号链接
- [x] `orchestrator_v2.py` 批量转写不再崩溃
- [x] 所有 Web 页面使用统一的 `media_tools.douyin.core.*` 路径
- [x] 下载/转写页面显示进度条

---

### 阶段 2: 提升用户体验（2-3 小时）

| 任务 | 预计时间 | 负责人 | 状态 |
|------|----------|--------|------|
| P1-1: task_queue.py 绝对路径 | 5 分钟 | Agent | 完成 |
| P1-2: 创建 accounts.json | 2 分钟 | Agent | 完成 |
| P1-3: 改进删除用户交互 | 15 分钟 | Agent | 完成 |
| P1-4: 批量操作实时进度 | 1 小时 | Agent | 完成 |
| P1-5: 错误历史查看 | 1 小时 | Agent | 完成 |

**验收标准**:
- [x] 任务状态文件在项目根目录
- [x] 账号管理页面正常显示
- [x] 删除用户只需一次确认
- [x] 批量操作显示实时进度
- [x] 可以查看历史任务错误

---

### 阶段 3: 代码质量提升（3-4 小时）

| 任务 | 预计时间 | 负责人 | 状态 |
|------|----------|--------|------|
| P2-1: 重构 stats_panel 缓存 | 15 分钟 | Agent | 完成 |
| P2-2: 统一 Cookie/认证管理 | 1 小时 | Agent | 完成 |
| P2-3: 添加新手引导 | 2 小时 | Agent | 完成 |
| P2-4: 使用 st.navigation | 30 分钟 | Agent | 完成 |
| P2-5: 数据导入/导出/备份 | 1 小时 | Agent | 完成 |

**验收标准**:
- [x] stats_panel.py 缓存逻辑简化
- [x] 认证体系统一
- [x] 首次访问显示引导
- [x] 使用 Streamlit 原生导航
- [x] 支持数据备份/恢复

---

## 四、技术栈和架构决策

### 当前技术栈
- **UI 框架**: Streamlit 1.x
- **后台任务**: Python Threading + JSON 文件轮询
- **数据持久化**: JSON 文件 + SQLite
- **认证**: Cookie + Playwright

### 架构决策

| 决策 | 当前方案 | 备选方案 | 选择理由 |
|------|----------|----------|----------|
| 任务队列 | JSON 文件轮询 | Celery/Redis | 简单，无外部依赖 |
| 页面导航 | st.radio + session_state | st.navigation | 保持现有（P2-4 再升级） |
| 缓存 | st.cache_data | functools.lru_cache | Streamlit 原生支持 |
| 配置管理 | YAML 文件 | 环境变量 + YAML | 用户友好 |

### 未来可能的升级路径
- 任务量增大时：JSON → SQLite/Redis
- 用户量增加时：单文件 → 多用户数据库
- 需要更多交互时：Streamlit → FastAPI + React

---

## 五、监控和测试

### 自动化测试
```bash
# 导入测试
python -c "from media_tools.douyin.core.* import *"

# 功能测试
python test_web_modules.py

# 端到端测试（手动）
streamlit run web_app.py
```

### 关键指标
- **页面加载时间**: < 2 秒
- **任务响应时间**: < 3 秒（轮询间隔 2 秒）
- **批量操作成功率**: > 95%
- **用户满意度**: 主观评估

---

## 六、风险和问题

### 已知风险
1. **删除 scripts/core/ 可能影响 CLI**: 需要确认 CLI 是否仍在使用
2. **批量操作实时刷新可能影响性能**: 需要测试大列表（100+ 用户）
3. **st.navigation 可能不兼容旧版 Streamlit**: 需要检查版本

### 缓解措施
1. 删除前先创建符号链接，观察一段时间
2. 添加缓存和分页
3. 检查 Streamlit 版本，提供 fallback

---

## 七、参考资料

### 相关文档
- `WEB_DEVELOPMENT_TASK_PLAN.md` - 之前的开发任务计划
- `WEB_UX_FIX_PLAN.md` - 用户体验修复计划
- `TEST_REPORT_FINAL.md` - 测试报告

### 关键文件
- `web_app.py` - 主入口
- `web/pages/*.py` - 页面模块
- `web/components/*.py` - 组件模块
- `src/media_tools/douyin/core/*.py` - 核心业务逻辑

---

## 八、版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| v1.0 | 2026-04-13 | 初始版本，创建优化规划 |

---

**维护者**: 开发团队
**审核周期**: 每周回顾一次
**下次审核**: 2026-04-20
