# Media Tools

> 视频素材抓取 → 云端转写 → 本地阅读，一站式内容工作台。

![React](https://img.shields.io/badge/Frontend-React%2019-61DAFB?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11%2B-brightgreen?logo=python&logoColor=white)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Media Tools 是一个本地化的 Web 工作台，帮助你从抖音批量抓取视频、通过通义千问云端转写为文字稿，并在浏览器中沉浸式阅读和管理。前后端分离架构，macOS 风格界面，支持深色/浅色主题。

---

## 核心特性

### Creators — 创作者管理

- 添加抖音博主，自动拉取头像、简介等信息
- 支持增量同步和全量重拉两种模式
- 定时自动同步（APScheduler cron 表达式，如每日凌晨 2 点）
- 一键删除创作者及其所有关联视频、文稿和数据库记录

### Discover — 发现与选取

- 输入博主主页链接，极速预览视频列表（含封面、时长、标题）
- 勾选感兴趣的视频后选择「仅下载」或「下载 + 转写」
- 告别盲盒式全量下载，按需处理

### Inbox — 收件箱与阅读

- 左侧创作者列表 + 右侧视频/文稿网格，双栏布局
- 抽屉式长文本阅读器，转写完成后无需离开页面即可阅读
- 虚拟滚动渲染大量资产，性能无忧

### Settings — 全局配置

- 抖音 Cookie 池管理，动态添加/移除账号
- 通义千问认证配置
- 全局开关：并发数、转写后自动删除源视频、下载后自动触发转写

### 任务系统

- 后台异步执行，WebSocket 实时推送进度到前端
- 失败自动重试（指数退避）+ 错误分类（网络/配额/认证/超时等）
- 断点续传：状态持久化到本地 JSON，中断后可继续
- 全局任务监控面板，查看运行中/失败/已完成的所有任务

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 19 + Vite + TypeScript + Tailwind CSS + shadcn/ui + Zustand |
| 后端 | Python 3.11+ + FastAPI + SQLite (WAL) + APScheduler |
| 核心 | f2（抖音 API）、Playwright（云端转写交互）、FFmpeg（音视频处理） |

---

## 快速启动

### 环境要求

- **Python 3.11+**
- **Node.js 18+**（含 npm）
- **FFmpeg**（音视频处理）

### 获取代码

```bash
git clone https://github.com/guiqingjob/douyin-stream.git
cd douyin-stream
```

### 一键启动

```bash
chmod +x run.sh   # 仅首次
./run.sh           # 同时启动后端 (8000) 和前端 (5173)
```

启动成功后访问 `http://localhost:5173`。

### 分步启动

```bash
./run.sh backend    # 仅启动 FastAPI 后端
./run.sh frontend   # 仅启动 React 开发服务器
./run.sh build      # 编译前端生产环境产物到 frontend/dist/
```

脚本会自动检测并安装缺失的 Python / npm 依赖。

---

## 配置说明

运行时配置位于 `config/config.yaml`，首次启动后通过 Settings 页面可视化管理，主要字段：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `cookie` | 抖音登录 Cookie | 通过 Settings 页面配置 |
| `download_path` | 视频下载存储路径 | `./downloads` |
| `auto_transcribe` | 下载后自动触发转写 | `true` |
| `auto_delete_video` | 转写成功后删除源视频 | `true` |
| `naming` | 视频文件命名模板 | `{desc}_{aweme_id}` |

通义千问认证状态存储在 `config/transcribe/` 目录下，通过 Settings 页面配置。

---

## 项目结构

```
media-tools/
├── frontend/                  # React SPA（独立子仓库）
├── src/media_tools/
│   ├── api/                   # FastAPI 应用
│   │   └── routers/           # 路由：creators, assets, tasks, settings, douyin, scheduler
│   ├── douyin/                # 抖音集成：下载、关注管理、Cookie 认证、视频压缩
│   ├── transcribe/            # 通义千问转写引擎：OSS 上传、轮询、导出、配额追踪
│   ├── pipeline/              # 流水线编排：下载→转写→导出，含重试和断点续传
│   └── db/                    # SQLite 数据库初始化与迁移
├── config/                    # 运行时配置文件
├── tests/                     # 测试套件
├── transcripts/               # 转写文稿输出目录
├── downloads/                 # 视频下载目录
└── run.sh                     # 一键启动脚本
```

---

## 开源协议

[MIT License](LICENSE)
