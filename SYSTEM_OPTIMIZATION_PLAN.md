# Media Tools 系统深度优化规划

在完成了 Web 端的 UI 重构后，目前的系统处于“外表光鲜，内力虚浮”的状态。为了让这个项目真正达到**生产可用 (Production-Ready)** 的级别，我规划了以下四个阶段的深度优化方案。我们将按照**从外到内、从痛点到性能**的顺序逐一攻破。

---

## 🚀 阶段一：消灭环境卡点 (Environment Auto-Fix)
**现状**：用户在首页看到 `Playwright 浏览器: 未安装` 只能手动去终端敲命令，体验极度割裂。
**目标**：在 Web 端的“系统配置”页面提供“一键自动修复环境”的能力，降低用户的使用门槛。

**具体行动**：
1. 在 `web/pages/settings.py` 中添加一键执行 `python -m playwright install chromium` 的按钮和进度反馈。
2. 将环境检测逻辑从同步阻塞改为异步或子进程调用，防止检测时卡死 Web 界面。

---

## 🐛 阶段二：重塑日志与异常捕获 (Logging & Error Tracking)
**现状**：整个 `web/` 目录和大量核心代码使用 `except Exception as e:` 吞掉了错误堆栈，报错时控制台静悄悄，排障全靠猜。
**目标**：建立全局统一的结构化日志系统，让每一个报错都有迹可循。

**具体行动**：
1. 在 `src/media_tools/utils/logger.py` 中强化全局 Logger 配置（输出到终端和 `logs/app.log`）。
2. 扫描所有 `web/pages/` 文件，在捕获异常时强制加入 `logger.exception(e)`，并在 UI 层抛出脱敏后的用户提示。
3. 移除核心代码中的 `print()` 调试语句。

---

## ⚡ 阶段三：异步性能解毒 (Async I/O Optimization)
**现状**：调度器（`orchestrator_v2.py`）使用 `asyncio`，但下载和转写的底层实现中混杂了大量同步的 `sqlite3` 写入和 `shutil` 文件操作，高并发下会导致 Event Loop 死锁。
**目标**：彻底打通异步血脉，消除 I/O 阻塞。

**具体行动**：
1. 重构 `douyin/core/db_helper.py` 等模块，将密集的 `sqlite3` 写入通过 `asyncio.to_thread()` 放入后台线程池。
2. 优化批量下载和转写的任务提交方式，引入 `asyncio.gather` 或限制并发数（`asyncio.Semaphore`）。

---

## 🧹 阶段四：工程化与测试卡点 (Code Quality & CI)
**现状**：代码风格不一，缺乏强类型校验，CI 流程形同虚设。
**目标**：引入现代 Python 工程化规范，建立长效的质量保证机制。

**具体行动**：
1. 引入 `Ruff` 并配置 `pyproject.toml`，一键格式化全库代码。
2. 修复 GitHub Actions 的 `ci.yml`，强制执行 `pytest` 和 `ruff check`。
