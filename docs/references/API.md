# 🔌 API 与架构开发指南 (API & Architecture Docs)

本项目 `douyin-stream` 在设计之初，就充分考虑了模块化与二次开发的可能。如果你希望将本项目接入你自己的 SaaS 服务、Web 后端（如 FastAPI / Django）或替换存储引擎，这份文档将为你提供关键的架构信息。

---

## 1. 核心模块与入口函数

所有的通用能力均被抽象在 `scripts/utils/` 目录下，你不必通过命令行（`subprocess`）调用，而是可以直接 `import` 并在你的 Python 应用程序中调用。

### 1.1 统一配置加载 (`config.py`)
```python
from scripts.utils.config import load_config, get_db_path, get_download_path

# 获取 config/config.yaml 中的所有配置
config = load_config()

# 获取统一的数据库路径
db_path = get_db_path()

# 获取经过校验的下载根目录
dl_path = get_download_path()
```

### 1.2 关注名单管理 (`following.py`)
名单同时关联本地 JSON 和 SQLite，该模块已封装所有复杂的双写同步逻辑。
```python
from scripts.utils.following import add_user, remove_user, list_users, get_user

# 获取所有关注名单
users = list_users()

# 添加/更新用户
add_user("1234567890", sec_user_id="MS4w...", name="博主昵称")

# 删除用户
remove_user("1234567890")
```

### 1.3 下载与统计入库 (`download.py`)
核心下载引擎基于 `f2` 构建，支持异步并发。你可以将其无缝挂载到任何异步框架（如 FastAPI、AIOHTTP）的 Background Task 中。
```python
import asyncio
from scripts.download import download_with_stats

async def trigger_download():
    # 异步下载博主最新 10 个视频，并自动完成元数据落库
    await download_with_stats(
        url="https://www.douyin.com/user/MS4w...", 
        max_counts=10
    )

# asyncio.run(trigger_download())
```

---

## 2. 数据库设计 (SQLite: `douyin_users.db`)

项目运行时会自动在根目录下生成 `douyin_users.db`。它包含三张核心表，用于支撑全链路的数据看板和防重复下载。

### 2.1 `user_info_web` 表
存放通过 API 抓取到的博主详细信息。
- `uid`: 博主数字 ID (Primary Key)
- `sec_user_id`: 抖音内部加密 ID
- `nickname`: 博主昵称
- `avatar_url`: 头像地址
- `signature`: 个性签名
- `follower_count`: 粉丝数
- `following_count`: 关注数
- `aweme_count`: 历史发布视频总数

### 2.2 `video_metadata` 表 (核心业务数据)
记录被成功下载并解析的每一条视频元数据。
- `aweme_id`: 视频唯一 ID (Primary Key)
- `uid`: 归属博主 UID
- `nickname`: 归属博主昵称
- `desc`: 视频文案（含 Hash 标签）
- `create_time`: 发布时间（时间戳）
- `digg_count`: 点赞量
- `comment_count`: 评论量
- `share_count`: 分享量
- `collect_count`: 收藏量
- `download_time`: 记录下载到本地的准确时间戳

---

## 3. 架构演进建议

如果你准备将本项目部署到生产级服务器或开源社区的高可用场景，建议进行以下改造：

### 3.1 替换 SQLite 为 MySQL/PostgreSQL
当前 `douyin_users.db` 满足本地单机高频读取，但并发写能力较弱。如果封装为多用户的 Web API：
1. 建议使用 `SQLAlchemy` 或 `Tortoise ORM` 替换原生的 `sqlite3` 模块。
2. 确保 `download_with_stats` 中的落库行为改为使用 ORM 事务。

### 3.2 剥离 Web 看板为独立前端项目
目前的 Web 看板是靠 `generate-data.py` 静态注入 `data.js` 的“伪 SSR”模式。如果改为 API 后端：
1. 请提供 `/api/v1/videos?uid={uid}` 等接口直连数据库。
2. 将 `index.html` 中的 JS 逻辑替换为使用 `fetch/axios` 动态请求后端。

### 3.3 加入任务队列机制 (Celery / Redis)
由于视频下载是典型的 I/O 密集型且耗时的任务，如果你暴露 HTTP 接口：
- **切勿**阻塞请求线程。
- 应当将 `download_with_stats` 丢入 **Celery Worker**，然后为前端提供一个 `/api/v1/task/status` 的轮询接口，查询当前博主视频是否抓取完毕。