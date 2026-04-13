# Web 应用用户体验修复计划

> 从真实用户角度发现的问题和修复方案

---

## 🔴 严重问题（页面无法正常使用）

### P0-1: following.json 路径错误（所有关注功能显示为空）

**问题**: 
- `src/media_tools/douyin/utils/following.py` 中 `SKILL_DIR` 计算错误
- 实际读取: `src/media_tools/config/following.json`（17 字节空数据）
- 应该读取: `config/following.json`（4381 字节真实数据）

**根因**: 
```python
# 错误：following.py 在 src/media_tools/douyin/utils/
SKILL_DIR = Path(__file__).parent.parent.parent.resolve()
# 结果: src/media_tools/
# 而不是项目根目录
```

**修复**: 
- 方案 A: 修正 `SKILL_DIR` 为上 4 级（`parent` × 4）
- 方案 B（推荐）: 使用环境变量或从 `web_app.py` 传入项目根目录

### P0-2: 仪表盘快速操作按钮无效

**问题**: 
- `dashboard.py` 设置 `st.session_state.page = "👤 关注管理"`
- 但 `web_app.py` 使用 `st.radio()` 控制页面切换
- 两者没有关联，点击按钮无响应

**修复**: 
- 方案 A: 改用 `st.session_state` 控制页面
- 方案 B: 使用 `st.switch_page()` (Streamlit 1.40+)

### P0-3: scripts.core.* 和 media_tools.douyin.core.* 混用

**问题**: 
- Web 页面使用 `media_tools.douyin.core.*`
- 但部分旧代码仍使用 `scripts.core.*`
- 两套路径指向不同文件，行为不一致

**修复**: 
- 统一为 `media_tools.douyin.core.*`
- 删除或废弃 `scripts/` 目录（或创建符号链接）

---

## 🟡 中等问题（功能可用但体验差）

### P1-1: 项目根目录硬编码

**问题**: 
- `SKILL_DIR` 在多个文件中通过 `Path(__file__).parent...` 计算
- 移动项目目录后全部失效

### P1-2: 配置加载不一致

**问题**: 
- `web/pages/settings.py` 使用 `media_tools.douyin.core.config_mgr`
- `scripts/core/config_mgr.py` 是旧版本
- 两者配置读取逻辑可能不同

### P1-3: 错误信息不友好

**问题**: 
- 用户看到 "No module named 'media_tools'" 不知道如何解决
- 应该提供更明确的指引

---

## 🟢 轻微问题

### P2-1: 目录不存在时未自动创建

**问题**: 
- `downloads/`, `transcripts/`, `temp_uploads/` 目录可能不存在
- 首次使用时会报错

---

## 修复执行顺序

```
1. 修复 following.json 路径（P0-1）← 最影响用户使用
2. 修复快速操作按钮（P0-2）
3. 统一模块路径（P0-3）
4. 修复配置加载（P1-2）
5. 添加友好错误提示（P1-3）
6. 自动创建必需目录（P2-1）
```
