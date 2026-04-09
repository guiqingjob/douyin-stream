# 🚀 抖音短视频自动下载管家 (Douyin Stream)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.txt)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-brightgreen.svg)](https://www.python.org/)
[![CI Status](https://github.com/GQ-Studio/douyin-stream/actions/workflows/ci.yml/badge.svg)](https://github.com/GQ-Studio/douyin-stream/actions)

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

### 1. 环境准备
请确保您的电脑已安装 Python 3.9 - 3.13，然后执行：
```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器内核 (用于扫码登录)
playwright install chromium

# 检查环境是否全部正常
python scripts/check_env.py
```

### 2. 获取授权 (扫码登录)
```bash
python scripts/login.py --persist
```
*(如果没有弹出浏览器，也可以在 `config/config.yaml` 中手动填入抓取到的 Cookie。)*

### 3. 添加关注博主
去抖音复制博主的主页链接，添加到系统的监控白名单中：
```bash
python scripts/manage-following.py --add "https://www.douyin.com/user/MS4wLjABAAAA..."
```

### 4. 一键执行下载
```bash
# 交互式批量下载（会提示你选择全量还是单个）
python scripts/batch-download.py

# 或者直接针对某个博主下载
python scripts/download.py "https://www.douyin.com/user/MS4wLjABAAAA..."
```

### 5. 生成并查看 Web 数据看板
```bash
python scripts/generate-data.py
```
执行完毕后，系统会在 `downloads/` 目录下生成 `data.js` 和 `index.html`。
双击打开 `downloads/index.html` 即可在浏览器中欣赏您的私人精美短视频库面板。

---

## 📂 核心目录结构

```text
douyin-stream/
├── references/               # 详细文档目录 (包含小白教程、安装、使用说明等)
├── scripts/                  # 核心执行脚本
│   ├── utils/                # 通用工具模块 (高度解耦，适合 API 化)
│   │   ├── config.py         # 统一配置模块
│   │   ├── following.py      # following.json 与数据库操作库
│   │   ├── auth_parser.py    # Cookie 解析验证引擎
│   │   └── logger.py         # 统一日志输出引擎
│   ├── check_env.py          # 环境检测工具
│   ├── login.py              # 扫码登录与 Cookie 提取
│   ├── download.py           # 核心下载脚本（带统计入库与增量逻辑）
│   ├── batch-download.py     # 批量下载控制器
│   ├── manage-following.py   # 关注列表维护与彻底清理工具
│   ├── compress.py           # 视频批量压缩工具
│   └── generate-data.py      # Web 静态数据生成器
├── config/                   # 配置目录
│   ├── config.yaml           # 主配置文件（含 Cookie、下载路径、命名模板）
│   └── following.json        # 关注（待下载）博主名单库
└── douyin_users.db           # SQLite 数据库（自动生成，存放统计与元数据）
```

## 👨‍💻 架构与二次开发

本项目的核心逻辑位于 `scripts/` 目录下，按功能进行了高度解耦。如需将本项目进一步改造为 SaaS API 接口、接入 FastAPI 或对接 MySQL/PostgreSQL 数据库集群，请查阅 [API_DOCS.md](references/API.md)。

## 🤝 参与贡献

我们非常欢迎来自社区的贡献！无论是报告 Bug、提出新功能建议，还是提交 Pull Request。
请在提交代码前，务必阅读我们的 [贡献指南 (CONTRIBUTING.md)](CONTRIBUTING.md)，以了解我们的代码规范（Black & Flake8）和提交流程。

## 📄 开源协议

本项目基于 [MIT 协议](LICENSE.txt) 开源。

> **免责声明**：本项目仅供编程学习与本地个人数据整理分析使用，请遵守相关法律法规及抖音平台的服务条款，严禁用于任何非法商业用途、恶意爬取或侵犯他人隐私与知识产权的行为。
