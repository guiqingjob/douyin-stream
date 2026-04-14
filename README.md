# 🎬 Media Tools Workspace

> 一个围绕 **素材获取 → 文稿生成 → 结果管理** 组织的本地内容工作台。

![React](https://img.shields.io/badge/Frontend-React%2018-61DAFB?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Python Version](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg?logo=python&logoColor=white)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Media Tools 是一个帮助你将视频素材（如抖音）快速抓取、批量转写为文字稿，并在本地进行沉浸式阅读与管理的现代化 Web 工作台。

项目现已全面重构为 **React + FastAPI** 的现代前后端分离架构，并采用了精致的 **macOS 视觉风格**。

---

## ✨ 核心特性

- 🎨 **macOS 风格界面**：采用毛玻璃半透明效果、细腻的阴影与圆角设计，提供原生应用般的丝滑体验。
- 👀 **“先预览，后选择”工作流**：告别盲盒式全量下载。输入博主主页链接，系统极速抓取视频列表，你可以直观地勾选感兴趣的视频后再下发处理。
- 📖 **沉浸式文稿阅读器**：内置抽屉式（Drawer）长文本阅读器，转写完成后无需离开网页即可流畅阅读、复制内容。
- ⚙️ **强大的全局管理**：
  - **多账号池**：在设置页可视化管理抖音 Cookie 池，支持动态添加/移除。
  - **任务监控**：独立的全局任务监控大盘，实时展示下载与转写进度及后台日志。
  - **无痕清理**：支持一键彻底删除创作者及关联的所有本地视频、文稿和数据库记录，并可配置转写后自动删除源视频以节省空间。

---

## 🛠 技术栈

- **前端**：React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui
- **后端**：Python 3.11+ + FastAPI + SQLite
- **核心组件**：Playwright (抓取)、f2 (抖音API)、Qwen (大模型转写)

---

## 🚀 快速启动

### 环境要求
1. **Python 3.11+**
2. **Node.js 18+** (含 npm)
3. **FFmpeg** (用于音视频处理)

### 1. 获取代码
```bash
git clone https://github.com/guiqingjob/douyin-stream.git
cd douyin-stream
```

### 2. 一键启动
项目内置了便捷的启动脚本，会自动检查并安装依赖，同时启动前后端服务：
```bash
# 赋予脚本执行权限（仅首次需要）
chmod +x run.sh

# 一键启动前端 (5173/5174) 和后端 (8000)
./run.sh
```

启动成功后，在浏览器中打开前端地址（通常为 `http://localhost:5173` 或控制台提示的地址）即可开始使用。

### 3. 分步启动（可选）
如果你希望在不同的终端窗口中分别运行前后端，也可以使用以下命令：
```bash
./run.sh backend    # 仅启动 FastAPI 后端
./run.sh frontend   # 仅启动 React 开发服务器
./run.sh build      # 编译前端生产环境产物到 frontend/dist/
```

---

## 💡 使用指南

1. **配置环境**：首次启动后，点击左侧导航栏进入 **Settings (设置)** 页面，填入你的通义千问（Qwen）API Key 以及抖音 Cookie。
2. **发现内容**：进入 **Discover (发现)** 页面，粘贴抖音博主的主页链接，点击预览。
3. **按需抓取**：在展示的视频网格中，勾选你感兴趣的视频，点击底部的“批量处理”。
4. **监控进度**：点击左下角的 **Task Monitor** 可以随时查看后台下载与转写的进度。
5. **阅读文稿**：任务完成后，进入 **Inbox (收件箱)**，点击对应的视频卡片即可呼出阅读器查看文字稿。

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。