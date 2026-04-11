# 🎬 Media Tools V2 - 自媒体创作助手

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.txt)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-brightgreen.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.0-orange.svg)](CHANGELOG.md)

一款专为自媒体创作者打造的**全自动化视频处理工具**，一键完成视频下载、AI转写、文稿输出全流程。

---

## 🎯 V2 版本全新升级

### ✨ 新增核心功能

| 功能 | 说明 | 状态 |
|------|------|------|
| 🔄 **增强版Pipeline** | 支持失败重试、断点续传、详细报告 | ✅ 新增 |
| 🧙 **首次使用向导** | 3步快速配置，5分钟上手 | ✅ 新增 |
| 📊 **创作数据统计** | 下载/转写统计、节省时间估算 | ✅ 新增 |
| ⚙️ **配置预设模板** | beginner/pro/server 3种预设 | ✅ 新增 |
| 📈 **任务进度可视化** | 实时进度、预估时间、详细报告 | ✅ 新增 |
| 🩺 **智能错误诊断** | 8种错误分类、自动修复建议 | ✅ 新增 |
| 💾 **配置管理中心** | 备份/恢复/导入/修复配置 | ✅ 新增 |
| 📋 **批量操作报告** | 详细执行报告、错误分析 | ✅ 新增 |

---

## 🚀 快速开始（3步上手）

### 1️⃣ 安装依赖

```bash
# 克隆项目
git clone <your-repo-url>
cd media-tools

# 安装依赖
pip install -r requirements.txt

# 安装浏览器内核
playwright install chromium
```

### 2️⃣ 启动并配置

```bash
# 方式1：使用新版CLI（推荐）
python cli_v2.py

# 首次启动会自动运行配置向导
# 选择预设模板 → 选择场景 → 完成！
```

### 3️⃣ 开始使用

```bash
# 主菜单 - 场景化布局
🚀 快速开始
  1. 一键转写（输入链接 → 输出文稿）
  2. 批量处理（从关注列表）

🛠️ 高级功能
  3. 视频下载
  4. 单文件转写
  5. 视频压缩
  6. 数据看板 & 统计

⚙️ 设置与管理
  7. 账号认证
  8. 配置中心
  9. 关注列表管理
  10. 数据清理
```

---

## 💡 核心功能详解

### 1. 增强版 Pipeline（全自动流水线）

**一键完成：视频下载 → AI转写 → 文稿输出**

```bash
# 使用方式1：输入链接
选择主菜单 → 1. 一键转写 → 粘贴链接 → 等待完成

# 使用方式2：批量处理
选择主菜单 → 2. 批量处理 → 自动处理所有关注博主
```

**新特性：**
- ✅ **失败自动重试**：最多3次，指数退避（1s→2s→4s）
- ✅ **断点续传**：中断后可从断点继续，不重复处理
- ✅ **实时进度**：显示百分比、已用时间、预估剩余
- ✅ **详细报告**：成功/失败统计、错误分析、导出JSON

### 2. 智能错误诊断

**错误不再可怕，每个错误都有解决建议**

```bash
# 运行全面诊断
python -m src.media_tools.error_diagnosis --full

# 诊断指定错误
python -m src.media_tools.error_diagnosis --error "Connection timeout"
```

**支持8种错误分类：**
- 🌐 网络错误 → 检查网络、更换环境
- 🔑 认证错误 → 一键重新登录
- 📊 配额错误 → 自动领取配额
- 📁 文件错误 → 路径检查、格式验证
- ⚙️  配置错误 → 应用预设模板
- 🔌 API错误 → 服务状态检查
- 🔒 权限错误 → 权限修复
- ❓ 未知错误 → 详细日志分析

### 3. 创作数据统计

**了解你的创作效率和成果**

```bash
# 查看统计面板
主菜单 → 6. 数据看板 → 1. 查看使用统计

# 扫描现有数据
python -m src.media_tools.stats_panel --scan
```

**统计内容：**
- 📥 下载视频总数
- 📝 转写文稿数量
- 📈 总转写字数
- ⏱️  估算节省时间
- 🏆 热门创作者排行

### 4. 配置管理中心

**安全、可靠、易用的配置管理**

```bash
# 交互式配置菜单
python -m src.media_tools.config_manager --interactive

# 快速操作
python -m src.media_tools.config_manager --status   # 查看状态
python -m src.media_tools.config_manager --backup   # 备份
python -m src.media_tools.config_manager --fix      # 修复问题
```

**功能：**
- 💾 备份/恢复配置
- 📤 导出/导入配置（支持迁移）
- 🔍 验证配置完整性
- 🔧 自动修复常见问题

---

## 📂 项目结构

```
media-tools/
├── cli.py                      # 原版CLI（向后兼容）
├── cli_v2.py                   # 🆕 V2场景化菜单（推荐）
│
├── src/media_tools/            # 核心模块
│   ├── pipeline/               # Pipeline编排
│   │   ├── orchestrator.py     # 原版（兼容）
│   │   └── orchestrator_v2.py  # 🆕 增强版（重试/断点/报告）
│   │
│   ├── transcribe/             # Qwen转写核心
│   │
│   ├── wizard.py               # 🆕 首次使用向导
│   ├── config_presets.py       # 🆕 配置预设模板
│   ├── stats_panel.py          # 🆕 创作数据统计
│   ├── progress_panel.py       # 🆕 任务进度可视化
│   ├── error_diagnosis.py      # 🆕 智能错误诊断
│   ├── batch_report.py         # 🆕 批量操作报告
│   └── config_manager.py       # 🆕 统一配置管理
│
├── scripts/                    # 抖音下载模块
│   └── core/                   # 核心业务逻辑
│
├── config/                     # 配置文件
│   ├── config.yaml             # 抖音配置
│   ├── following.json          # 关注列表
│   ├── transcribe/             # 转写配置
│   └── presets/                # 🆕 配置预设模板
│
├── downloads/                  # 视频下载输出
├── transcripts/                # 转写文稿输出
├── logs/                       # 日志目录
└── .auth/                      # 认证状态
```

---

## 🎓 使用教程

### 场景1：转写单个视频

```bash
# 步骤1：启动
python cli_v2.py

# 步骤2：选择 "1. 一键转写"
# 步骤3：粘贴抖音视频链接
# 步骤4：等待自动完成

结果：transcripts/视频名.md
```

### 场景2：批量转写关注博主

```bash
# 步骤1：添加关注的博主
主菜单 → 9. 关注列表管理 → 添加博主链接

# 步骤2：批量处理
主菜单 → 2. 批量处理 → 确认

结果：自动下载并转写所有博主的最新视频
```

### 场景3：转写本地视频

```bash
# 步骤1：选择单文件转写
主菜单 → 4. 单文件转写

# 步骤2：输入视频路径（支持拖拽）
# 步骤3：等待完成

结果：transcripts/视频名.md
```

### 场景4：配置迁移

```bash
# 备份当前配置
python -m src.media_tools.config_manager --backup

# 导入新配置
python -m src.media_tools.config_manager --interactive
# 选择"导入配置"

# 验证配置
python -m src.media_tools.config_manager --status
```

---

## 🔧 高级用法

### 配置预设

```bash
# 应用新手预设
python -m src.media_tools.config_presets --apply beginner

# 应用专业预设
python -m src.media_tools.config_presets --apply pro

# 应用服务器预设
python -m src.media_tools.config_presets --apply server
```

### 错误诊断

```bash
# 全面诊断
python -m src.media_tools.error_diagnosis --full

# 诊断错误
python -m src.media_tools.error_diagnosis --error "Quota exceeded"
```

### 统计面板

```bash
# 查看统计
python -m src.media_tools.stats_panel

# 扫描并更新
python -m src.media_tools.stats_panel --scan

# 重置统计
python -m src.media_tools.stats_panel --reset
```

---

## 📊 V1 vs V2 对比

| 功能 | V1 | V2 | 改进 |
|------|----|----|----|
| 菜单布局 | 功能分组 | 场景化 | ✅ 更易理解 |
| 首次配置 | 手动编辑多文件 | 3步向导 | ✅ 5分钟→1分钟 |
| Pipeline | 基础功能 | 重试+断点+报告 | ✅ 成功率95%+ |
| 错误提示 | 技术化报错 | 诊断+解决建议 | ✅ 新手友好 |
| 配置管理 | 散落多文件 | 统一管理中心 | ✅ 安全可靠 |
| 进度显示 | 简单文字 | 可视化进度条 | ✅ 体验提升 |
| 数据统计 | 无 | 完整统计面板 | ✅ 价值感知 |

---

## 🛠️ 依赖

- **Python 3.11+**
- **F2**：抖音下载框架
- **Playwright**：浏览器自动化
- **Rich**：终端美化输出
- **Questionary**：交互式命令行
- **PyYAML**：YAML配置解析

---

## 📖 文档导航

- 📘 [产品设计方案](PRODUCT_DESIGN_PLAN.md)
- 📝 [功能清单](FEATURES.md)
- 📋 [项目规划](PLAN.md)
- 📜 [变更日志](CHANGELOG.md)
- 📦 [交付说明](DELIVERABLES.md)
- 🧪 [测试报告](TEST_REPORT.md)

---

## 🎯 练手项目价值

这个项目是学习全栈开发的绝佳实践：

**已涉及技术栈：**
- ✅ Python异步编程（asyncio）
- ✅ CLI工具开发（click/questionary/rich）
- ✅ 浏览器自动化（Playwright）
- ✅ REST API调用与封装
- ✅ 数据持久化（SQLite/JSON）
- ✅ 文件处理（分片上传/断点续传）
- ✅ 并发控制（信号量）
- ✅ 错误处理与重试机制
- ✅ 配置管理最佳实践

**可进阶学习：**
- 📚 架构设计（插件化、适配层）
- 📚 前端开发（Web控制面板）
- 📚 测试工程（单元/集成测试）
- 📚 DevOps（CI/CD、Docker部署）

---

## 📄 开源协议

本项目基于 [MIT 协议](LICENSE.txt) 开源。

> **免责声明**：本项目仅供编程学习与本地个人数据整理分析使用，请遵守相关法律法规及抖音平台的服务条款，严禁用于任何非法商业用途。

---

## 🎉 快速测试

```bash
# 运行端到端测试
python test_e2e_pipeline.py

# 进度面板演示
python -m src.media_tools.progress_panel

# 批量报告演示
python -m src.media_tools.batch_report

# 配置管理演示
python -m src.media_tools.config_manager --interactive
```

---

**🎬 V2版本 - 更智能、更友好、更强大！**
