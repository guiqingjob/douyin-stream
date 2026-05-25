# Media Tools 配置架构

## 两层模型

整个项目运行时的配置只有 **2 个真实层**，按优先级（高→低）：

| 层 | 来源 | 何时读 | 谁能改 | 缓存 |
|---|---|---|---|---|
| 1 | **`SystemSettings` 数据库表**（运行期 mutable） | 每次 `AppConfig.get(...)` 调用 | 前端 settings UI / API | 内存 5 秒 TTL |
| 2 | **`config/config.yaml` + `.env` + 环境变量**（启动一次性） | 进程启动时 `load_config()` 跑一次 | 改文件后重启进程才生效 | 进程级常驻 |

第 1 层是用户运行期可改的（如 `concurrency` / `auto_transcribe` / `export_format` / `api_key`）。
第 2 层是部署级配置（如 `cookie` / `download_path` / `QWEN_*` 系列环境变量）。

## 调用规范

- ✅ **生产代码** 一律走 `from media_tools.core.config import get_app_config` → `config.xxx` 或 `get_runtime_setting(key, default)`
- ✅ 启动期可在 `core/config.py` / `transcribe/config.py` / `logger.py` 等 **少数 bootstrap 文件**里读 `os.environ.get(...)`
- ❌ 其余 src 代码**不允许**直接 `os.environ.get(...)`——所有运行期配置走 AppConfig
- ❌ 不允许散落第三、第四个配置层（如 module-level 全局变量、隐藏 in-memory dict）

## 缓存策略

`_get_system_setting` 用 `_settings_cache: dict[key, (value, expire_time)]`，TTL **5 秒**。

- **API 路径写入**（`_set_system_setting`）→ 立刻 invalidate 对应 key 的缓存条目；
- **DB 直接写入**（非常规，例如手动改 settings UI 跳过 API）→ 最坏 5 秒后被下次读取看到。

之所以选 5 秒而不是更长：
- 配置改完想立刻在 UI 上看到效果是核心 UX，10 秒+ 都被用户报过"不生效"
- 5 秒 = 每秒最多 1 次 DB miss → 几乎零额外 IO

之所以不选 0（无缓存）：
- 部分 setting 在热路径上被读（如 `concurrency`）；零缓存 → 每个任务派发都打 DB 一次。

## 验证

回归测试 `tests/test_config_layers.py` 强制约束：

1. 改 `SystemSettings` 表内某 key 后等待 6 秒（>TTL），`AppConfig.get(key)` 必须返回新值
2. `os.environ.get` 在 src 内的总出现次数被钉在一个允许列表里（防回滚加新散落点）

`tests/test_export_format_changes_take_effect.py` 锁住 v2026-05 那次踩的坑：

DB 设 `export_format=md` → 6 秒后启动新转写产物必须是 `.md` 后缀。

## 历史

合并自前 5 层混乱（env + .env + DB runtime + AppConfig._RUNTIME_DEFAULTS + 前端 settings），
2026-05 REFACTOR 任务 4 一次性收敛到 2 层。
