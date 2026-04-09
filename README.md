# 🚀 抖音短视频自动下载管家 (Douyin Download Renew)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.txt)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-brightgreen.svg)](https://www.python.org/)

一款专为自媒体创作者、运营人员和数据分析师打造的**全自动抖音无水印视频下载与数据分析管家**。

基于现代化的架构设计，本项目不仅支持全量与增量视频的高速并发下载，还能无感记录播放、点赞等业务数据，并在本地自动生成极具科技感的**毛玻璃（Glassmorphism）数据看板**。

---

## ✨ 核心特性

- **🎬 自动下载无水印视频**：基于强大的 `f2` 引擎，原画质提取，突破反爬限制。
- **🧠 智能增量更新**：自动跳过已下载的视频，只拉取博主最新发布的内容，节省时间和带宽。
- **📊 数据无感沉淀**：内置 SQLite 数据库，自动记录视频的点赞、评论、分享等核心互动数据。
- **🌐 精美 Web 看板**：运行命令即可生成无需服务器的单文件静态网页，支持多维度智能排序与毫秒级搜索。
- **🤖 Playwright 扫码授权**：提供稳定可靠的二维码扫码登录及 Cookie 自动保活与防风控验证机制。
- **🧹 一键清理与取关**：提供优雅的数据清理命令，不再关注的博主可一键清空记录及本地视频。

## 📚 文档导航

我们为不同技术背景的用户提供了详尽的说明文档，请根据您的需求查阅：

- 👶 **[零基础小白说明书 (USER_MANUAL)](references/USER_MANUAL_ZERO_BASIS.md)**：专门为非技术人员编写的“保姆级”图文操作指南。
- ⚙️ **[安装指南 (INSTALLATION)](references/INSTALLATION.md)**：系统要求、依赖安装及环境配置步骤。
- 📖 **[使用说明 (USAGE)](references/USAGE.md)**：所有脚本的详细命令参数、配置项说明及完整工作流。
- ❓ **[常见问题解答 (FAQ)](references/FAQ.md)**：常见报错排查及解决方案。
- 📜 **[变更日志 (CHANGELOG)](CHANGELOG.md)**：历史版本更新记录。

## 🛠️ 快速开始

### 1. 环境准备
确保您的电脑已安装 Python 3.9+，然后执行：
```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器内核 (用于扫码登录)
playwright install chromium
```

### 2. 获取授权 (扫码登录)
```bash
python scripts/login.py --persist
```

### 3. 添加关注博主
```bash
python scripts/manage-following.py --add "https://www.douyin.com/user/MS4wLjABAAAA..."
```

### 4. 批量执行下载
```bash
python scripts/batch-download.py
```

### 5. 生成并查看 Web 看板
```bash
python scripts/generate-data.py
```
执行完毕后，双击打开 `downloads/index.html` 即可欣赏精美的数据面板。

---

## 👨‍💻 架构与开发

本项目的核心逻辑位于 `scripts/` 目录下，按功能进行了高度解耦。如需将本项目进一步改造为 SaaS API 接口或对接数据库集群，请参考 `scripts/utils/` 中的模块化设计。

## 📄 开源协议

本项目基于 MIT 协议开源，请遵守相关法律法规，仅用于学习与数据分析，严禁用于任何非法商业用途。
