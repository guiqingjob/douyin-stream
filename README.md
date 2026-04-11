# 🚀 抖音短视频自动下载管家 (Douyin Stream)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.txt)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-brightgreen.svg)](https://www.python.org/)
[![CI Status](https://github.com/guiqingjob/douyin-stream/actions/workflows/ci.yml/badge.svg)](https://github.com/guiqingjob/douyin-stream/actions)

一款专为自媒体创作者、运营人员和数据分析师打造的**全自动抖音无水印视频下载与数据分析管家**。

本项目基于 **F2 框架**实现，提供高效、稳定、可增量的抖音视频批量下载能力，并附带完善的数据统计与可视化 Web 管理界面。

---

## ✨ 核心特性

- **🎬 自动下载无水印视频**：原画质提取，支持单个博主下载、全量批量下载、交互式选择下载及快速采样下载。
- **🧠 智能增量更新**：自动跳过已下载的视频，支持差量更新，只拉取博主最新发布的内容，极大节省时间和带宽。
- **🤖 自动化 Cookie 管理**：内置基于 Playwright 的扫码登录脚本，自动获取并持久化保存 Cookie，内置防风控设计。
- **📊 完善的关注列表管理**：支持从主页链接一键添加用户、批量导入、实时搜索与移除。
- **💾 元数据与统计入库**：下载视频时自动抓取点赞、评论、收藏、分享等数据，存入本地 SQLite 数据库。
- **🌐 可视化 Web 界面**：纯前端（Glassmorphism 毛玻璃风格）实现的 Web 数据面板，可直观浏览博主、播放视频并按多维度排序筛选。
- **🧹 一键清理与取关**：提供优雅的数据清理命令，不再关注的博主可一键清空数据库记录及本地视频文件。
- **📦 智能视频压缩**：集成 FFmpeg，支持单文件/多用户/全量视频压缩，智能跳过小文件与低分辨率视频。

## 🎯 典型使用场景

- **服务器自动化下载**：部署在服务器上，定时批量抓取目标博主的最新视频内容。
- **本地视频库构建**：分类存储视频，使用博主昵称命名文件夹，便于后续剪辑与素材管理。
- **自媒体竞品分析**：依托抓取到的点赞、评论、收藏等结构化数据，进行竞品数据可视化分析。

## 📚 文档导航

我们为不同技术背景的用户提供了详尽的说明文档，请根据您的需求查阅：

- 👶 **[零基础小白说明书 (USER_MANUAL)](references/USER_MANUAL_ZERO_BASIS.md)**：专门为非技术人员编写的“保姆级”图文操作指南。
- ⚙️ **[安装指南 (INSTALLATION)](references/INSTALLATION.md)**：系统要求、依赖安装及环境配置步骤。
- 📖 **[使用说明 (USAGE)](references/USAGE.md)**：所有脚本的详细命令参数、配置项说明及完整工作流。
- 🔌 **[API 与架构文档 (API_DOCS)](references/API.md)**：供开发者参考的二次开发、API 调用与数据库结构说明。
- 🤝 **[贡献指南 (CONTRIBUTING)](CONTRIBUTING.md)**：参与本项目开发的代码规范、PR 提交流程指南。
- ❓ **[常见问题解答 (FAQ)](references/FAQ.md)**：常见报错排查及解决方案。
- 📜 **[变更日志 (CHANGELOG)](CHANGELOG.md)**：历史版本更新记录。

## 🛠️ 快速开始

> **💡 新版 CLI 已上线！** 现在只需运行 **一个命令**，通过交互式菜单即可完成所有操作，无需再记忆复杂命令。

### 1. 环境准备
请确保您的电脑已安装 Python 3.9 - 3.13，然后执行：
```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器内核 (用于扫码登录)
playwright install chromium
```

### 2. 启动统一 CLI
```bash
python cli.py
```
启动后按菜单提示选择功能即可：
- **1** - 环境检测
- **2** - 扫码登录
- **3** - 关注列表管理
- **4** - 视频下载
- **5** - 视频压缩
- **6** - 生成数据看板

---

<details>
<summary>📜 旧版命令（已废弃，点击展开）</summary>

> ⚠️ 以下旧版命令已迁移至 `scripts/deprecated/`，运行时会提示使用新 CLI。

```bash
# 环境检测
python scripts/check_env.py

# 扫码登录
python scripts/login.py --persist

# 添加关注博主
python scripts/manage-following.py --add "https://www.douyin.com/user/MS4wLjABAAAA..."

# 下载视频
python scripts/batch-download.py
python scripts/download.py "https://www.douyin.com/user/MS4wLjABAAAA..."

# 生成数据看板
python scripts/generate-data.py
```

</details>

---

## 📂 核心目录结构

```text
douyin-stream/
├── cli.py                      # 🆕 统一 CLI 入口（用户唯一需要运行的脚本）
├── scripts/
│   ├── core/                   # 🆕 业务逻辑层（CLI 调用的核心模块）
│   │   ├── ui.py               # 终端美化输出（颜色/进度条/表格）
│   │   ├── config_mgr.py       # 统一配置管理
│   │   ├── env_check.py        # 环境检测
│   │   ├── auth.py             # 登录认证
│   │   ├── following_mgr.py    # 关注列表管理
│   │   ├── downloader.py       # 视频下载
│   │   ├── compressor.py       # 视频压缩
│   │   └── data_generator.py   # 数据看板生成
│   ├── deprecated/             # ⚠️ 已废弃的旧脚本（向后兼容）
│   │   ├── check_env.py
│   │   ├── login.py
│   │   ├── download.py
│   │   ├── batch-download.py
│   │   ├── manage-following.py
│   │   ├── compress.py
│   │   ├── generate-data.py
│   │   └── sync-following.py
│   ├── utils/                  # 通用工具模块（基础设施）
│   │   ├── config.py
│   │   ├── following.py
│   │   ├── auth_parser.py
│   │   └── logger.py
│   └── templates/              # Web 模板目录
├── config/                     # 配置目录
│   ├── config.yaml             # 主配置文件（含 Cookie、下载路径等）
│   └── following.json          # 关注博主名单库
├── downloads/                  # 下载文件存储目录
└── douyin_users.db             # SQLite 数据库（自动生成）
```

## 👨‍💻 架构与二次开发

本项目的核心逻辑位于 `scripts/` 目录下，按功能进行了高度解耦。如需将本项目进一步改造为 SaaS API 接口、接入 FastAPI 或对接 MySQL/PostgreSQL 数据库集群，请查阅 [API_DOCS.md](references/API.md)。

## 🤝 参与贡献

我们非常欢迎来自社区的贡献！无论是报告 Bug、提出新功能建议，还是提交 Pull Request。
请在提交代码前，务必阅读我们的 [贡献指南 (CONTRIBUTING.md)](CONTRIBUTING.md)，以了解我们的代码规范（Black & Flake8）和提交流程。

## 📄 开源协议

本项目基于 [MIT 协议](LICENSE.txt) 开源。

> **免责声明**：本项目仅供编程学习与本地个人数据整理分析使用，请遵守相关法律法规及抖音平台的服务条款，严禁用于任何非法商业用途、恶意爬取或侵犯他人隐私与知识产权的行为。
