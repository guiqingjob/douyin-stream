---
name: douyin-batch-download
homepage: https://github.com/cat-xierluo/legal-skills
author: 杨卫薪律师（微信ywxlaw）
version: "1.9.0"
license: MIT
description: 抖音视频批量下载工具 - 基于 F2 框架实现高效、增量的视频下载功能。支持单个/批量博主下载，自动 Cookie 管理，差量更新机制。本技能应在用户需要批量下载特定博主视频、服务器部署自动化下载、或定期更新视频库时使用。
---

# 抖音视频批量下载工具 (Douyin Batch Download)

本技能基于 **F2 框架**实现，提供高效、稳定、可增量的抖音视频批量下载能力，并附带完善的数据统计与可视化 Web 管理界面。

## ✨ 核心功能

- **多模式下载**：支持单个博主下载、全量批量下载、交互式选择下载及快速采样下载。
- **智能增量更新**：自动跳过已下载的视频，支持差量更新，极大节省时间和带宽。
- **自动化 Cookie 管理**：内置扫码登录脚本，自动获取并持久化保存 Cookie，防风控设计。
- **完善的关注列表管理**：支持从主页链接一键添加用户、批量导入、实时搜索与移除。
- **元数据与统计入库**：下载视频时自动抓取点赞、评论、收藏、分享等数据，存入本地 SQLite 数据库。
- **可视化 Web 界面**：纯前端实现的 Web 数据面板，可直观浏览博主、播放视频并按多维度排序筛选。
- **智能视频压缩**：集成 FFmpeg，支持单文件/多用户/全量视频压缩，智能跳过小文件与低分辨率视频。

## 🎯 典型使用场景

- **服务器自动化下载**：部署在服务器上，定时批量抓取目标博主的最新视频内容。
- **本地视频库构建**：分类存储视频，使用博主昵称命名文件夹，便于后续剪辑与素材管理。
- **自媒体竞品分析**：依托抓取到的点赞、评论、收藏等结构化数据，进行竞品数据可视化分析。

## 🚀 快速入门

### 1. 环境准备
请确保已安装 Python (3.9-3.13) 及相关依赖包，推荐使用环境检测脚本验证：
```bash
python scripts/check_env.py
```
> **提示**：如未安装，请查阅 [安装指南](references/INSTALLATION.md)。

### 2. 获取 Cookie 登录态
**方式一：扫码登录 (推荐)**
首次使用需获取登录态：
```bash
python scripts/login.py --persist
```
> **提示**：使用 `--persist` 参数可持久化保存登录状态，下次无需重新扫码。

**方式二：手动抓取网页 Cookie**
如果无法使用扫码脚本，你也可以在浏览器中登录 [抖音网页版](https://www.douyin.com/)，按 `F12` 打开开发者工具 -> `Application (应用)` -> `Cookies`，提取以下核心 Cookie 字段并拼接：
- `sessionid` (必须，核心身份凭证)
- `passport_csrf_token` (重要，防跨站伪造请求)
- `sid_guard` / `ttwid` (辅助验证)

然后将拼接好的字符串（格式如 `sessionid=xxx; passport_csrf_token=yyy;`）写入 `config/config.yaml` 或使用内置的**可视化解析器**处理。

### 3. 一键下载
推荐的下载方式，自动保存视频及统计数据：
```bash
# 单个博主下载
python scripts/download.py "https://www.douyin.com/user/MS4wLjABAAAA..."

# 交互式批量下载
python scripts/batch-download.py
```

### 4. 浏览数据
下载完成后，生成最新数据并在浏览器中查看：
```bash
python scripts/generate-data.py
# 随后在文件管理器中双击打开 downloads/index.html
```

## 📚 文档导航

为保持内容清晰，详细说明已分拆至独立文档，请根据需求查阅：

- 👶 **[零基础小白说明书 (USER_MANUAL)](references/USER_MANUAL_ZERO_BASIS.md)**：专门为非技术人员编写的“保姆级”图文操作指南。
- ⚙️ **[安装指南 (INSTALLATION)](references/INSTALLATION.md)**：系统要求、依赖安装步骤。
- 📖 **[使用说明 (USAGE)](references/USAGE.md)**：所有脚本的详细命令参数、配置项说明及完整工作流。
- ❓ **[常见问题解答 (FAQ)](references/FAQ.md)**：常见报错排查及解决方案。
- 📜 **[变更日志 (CHANGELOG)](CHANGELOG.md)**：历史版本更新记录。

## 📂 核心目录结构

```text
douyin-batch-download/
├── SKILL.md                  # 技能说明主文档
├── references/               # 详细文档目录
│   ├── INSTALLATION.md       # 安装指南
│   ├── USAGE.md              # 使用说明
│   └── FAQ.md                # 常见问题解答
├── scripts/                  # 核心执行脚本
│   ├── utils/                # 通用工具模块
│   │   ├── config.py         # 统一配置模块
│   │   └── following.py      # following.json 操作库
│   ├── check_env.py          # 环境检测工具
│   ├── login.py              # 扫码登录与 Cookie 提取
│   ├── download.py           # 核心下载脚本（带统计入库）
│   ├── batch-download.py     # 批量下载控制器
│   ├── manage-following.py   # 关注列表维护工具
│   ├── sync-following.py     # F2 数据库与关注列表同步
│   ├── compress.py           # 视频批量压缩工具
│   └── generate-data.py      # Web 静态数据生成器
├── config/                   # 配置目录
│   ├── config.yaml           # 主配置文件（含 Cookie）
│   └── following.json        # 关注（待下载）博主列表
└── douyin_users.db           # SQLite 数据库（用户信息与视频元数据）
```