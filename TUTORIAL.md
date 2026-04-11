# 📖 Media Tools V2 完全使用教程

> 从零开始，手把手教你成为Media Tools高手！

---

## 🎯 目录

1. [安装与配置](#1-安装与配置)
2. [首次使用向导](#2-首次使用向导)
3. [快速上手3个场景](#3-快速上手3个场景)
4. [高级功能详解](#4-高级功能详解)
5. [配置管理](#5-配置管理)
6. [故障排查](#6-故障排查)
7. [最佳实践](#7-最佳实践)

---

## 1. 安装与配置

### 1.1 环境要求

- **Python**: 3.11 或更高版本
- **操作系统**: macOS / Linux / Windows
- **磁盘空间**: 至少 2GB
- **网络**: 稳定的网络连接

### 1.2 快速安装

```bash
# 方法1：使用快速启动脚本（推荐）
git clone <你的仓库地址>
cd media-tools
chmod +x run.sh
./run.sh setup

# 方法2：手动安装
git clone <你的仓库地址>
cd media-tools

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 安装浏览器内核
playwright install chromium

# 初始化配置
./run.sh setup
```

### 1.3 验证安装

```bash
# 运行演示
./run.sh demo

# 运行测试
./run.sh test

# 查看诊断
./run.sh diag
```

如果所有测试通过，说明安装成功！

---

## 2. 首次使用向导

### 2.1 启动向导

第一次运行程序时，会自动启动配置向导：

```bash
python cli_v2.py
```

你会看到：

```
================================================================
🎉 欢迎使用 Media Tools！检测到首次使用
================================================================

💡 建议先选择一个配置预设模板

⚙️  配置预设选择

当前未选择预设

选择预设模板:
❯ 🌱 新手模式 (beginner)
  🚀 专业模式 (pro)
  🖥️  服务器模式 (server)
  ⏭️  跳过，使用手动配置
```

### 2.2 选择预设

**新手模式** (推荐初次使用)：
- 低并发（3路），避免限流
- 自动清理云端记录
- 自动删除原视频（省空间）
- 配置最简单

**专业模式** (熟练用户)：
- 6路高并发
- 启用视频压缩
- 所有功能全开
- 批量处理优化

**服务器模式** (服务器部署)：
- 10路超高并发
- 无头模式运行
- 详细日志记录
- 适合定时任务

### 2.3 选择场景

```
📋 步骤 1/3: 选择你的使用场景

这将帮你自动配置最合适的功能

你最主要的用途是？
❯ 🔄 全自动流水线 (推荐)
    下载视频 → 自动转写 → 输出文稿，一条链全自动
  📥 主要下载视频
    批量下载抖音视频到本地，暂不转写
  🎙️ 主要转写本地视频
    已有视频文件，只需AI转写成文稿
```

### 2.4 账号配置

```
🔑 步骤 2/3: 账号配置

现在要配置哪个账号？
❯ 📱 抖音账号 (扫码登录)
    用于下载抖音视频
  🤖 Qwen AI账号 (浏览器认证)
    用于AI转写
  ⏭️  跳过，稍后配置
```

**抖音认证**：
1. 选择"抖音账号"
2. 会弹出浏览器窗口
3. 用手机抖音扫码登录
4. 认证成功

**Qwen认证**：
1. 选择"Qwen AI账号"
2. 会弹出浏览器窗口
3. 登录Qwen AI平台
4. 认证成功

### 2.5 完成配置

```
🎉 步骤 3/3: 配置完成！

📋 你的配置摘要:
  • 使用场景: auto
  • 配置状态: ✅ 已初始化

接下来要做什么？
❯ 🚀 直接进入主菜单开始使用
  🧪 运行一个测试任务
  📖 查看使用教程
```

---

## 3. 快速上手3个场景

### 场景1：转写单个视频（最常用）

**目标**：输入一个抖音链接，得到文字稿

**步骤**：

```bash
# 1. 启动程序
python cli_v2.py

# 2. 选择 "1. 一键转写"

# 3. 粘贴抖音链接
请粘贴抖音链接: https://www.douyin.com/video/7123456789

# 4. 等待自动完成
📥 步骤 1/2: 下载视频...
  [下载] 开始下载...
  ✅ 下载成功

🎙️  步骤 2/2: 开始转写...
  [上传] 上传到OSS...
  [转写] AI处理中...
  [导出] 生成文稿...
  ✅ 转写成功！

文稿: transcripts/视频名-2026-04-12T10-30-45.md
```

**结果**：在 `transcripts/` 目录下找到Markdown文稿

### 场景2：批量转写关注的博主

**目标**：一次性下载并转写所有关注博主的最新视频

**步骤**：

```bash
# 1. 先添加关注的博主
python cli_v2.py
选择 "9. 关注列表管理"
选择 "2. 添加博主链接"
粘贴博主主页链接

# 2. 批量处理
选择 "2. 批量处理"
确认: y

# 3. 等待完成
🔄 开始批量处理...

[1/5] 📥 博主A
  📥 下载视频（最多 5 个）...
  ✓ 找到 5 个视频
  
[2/5] 📥 博主B
  ...

🎙️  开始批量转写 25 个视频...

📊 批量操作摘要
  操作名称    批量转写
  总任务数    25
  成功        24
  失败        1
  成功率      96.0%
```

**结果**：所有文稿保存在 `transcripts/` 目录

### 场景3：转写本地视频文件

**目标**：将自己录制的视频转成文稿

**步骤**：

```bash
# 1. 选择单文件转写
python cli_v2.py
选择 "4. 单文件转写"

# 2. 输入文件路径（支持拖拽）
请输入文件路径 (支持拖拽): /path/to/your/video.mp4

# 3. 等待完成
开始转写...
  [1/1] 处理中...
  ✅ 转写成功！

文稿: transcripts/video-2026-04-12T10-30-45.md
```

---

## 4. 高级功能详解

### 4.1 配置预设管理

**查看当前预设**：
```bash
python -m src.media_tools.config_presets --show
```

**切换预设**：
```bash
# 切换到专业模式
python -m src.media_tools.config_presets --apply pro

# 切换到服务器模式
python -m src.media_tools.config_presets --apply server
```

**列出所有预设**：
```bash
python -m src.media_tools.config_presets --list
```

### 4.2 统计面板使用

**查看统计**：
```bash
# 查看当前统计
python -m src.media_tools.stats_panel

# 扫描现有数据并更新
python -m src.media_tools.stats_panel --scan

# 重置统计
python -m src.media_tools.stats_panel --reset
```

**统计数据包括**：
- 下载视频总数
- 转写文稿数量
- 总转写字数
- 估算节省时间
- 热门创作者排行

### 4.3 错误诊断工具

**全面诊断**：
```bash
python -m src.media_tools.error_diagnosis --full
```

会检查：
- ✅ 网络连接
- ✅ 抖音认证
- ✅ Qwen认证
- ✅ 配置文件
- ✅ 磁盘空间
- ✅ 依赖安装

**诊断具体错误**：
```bash
python -m src.media_tools.error_diagnosis --error "Connection timeout"
```

会提供：
- 错误分类
- 可能原因
- 解决方案
- 自动修复选项

### 4.4 配置管理中心

**启动交互菜单**：
```bash
python -m src.media_tools.config_manager --interactive
```

**功能**：
- 🔍 验证所有配置
- 💾 备份配置
- ♻️  恢复配置
- 📤 导出配置
- 📥 导入配置
- 📋 查看备份列表
- 🔧 修复常见问题

**快速操作**：
```bash
# 查看状态
python -m src.media_tools.config_manager --status

# 备份
python -m src.media_tools.config_manager --backup

# 修复
python -m src.media_tools.config_manager --fix
```

### 4.5 进度可视化

进度面板会自动在批量任务中显示：

```
╭────────────────── 📊 统计 ──────────────────╮
│  总计: 10 | 成功: 6 | 失败: 1 | 跳过: 0     │
│  处理中: 3                                   │
│  已用时间: 45.2s                             │
│  预估剩余: 22.1s                             │
╰──────────────────────────────────────────────╯

#  状态          文件名              耗时      详情
1. ✅ 成功      video_1.mp4         5.2s      transcripts/...
2. ✅ 成功      video_2.mp4         4.8s      transcripts/...
3. 🔄 处理中    video_3.mp4         6.1s      上传中...
4. ❌ 失败      video_4.mp4         2.3s      网络错误
5. ⏳ 等待中    video_5.mp4         -         -
```

---

## 5. 配置管理

### 5.1 配置文件说明

```
config/
├── config.yaml              # 抖音配置（Cookie、下载路径）
├── following.json           # 关注列表
├── transcribe/
│   ├── .env                 # 转写环境变量
│   └── accounts.json        # 转写账号配置
└── active_preset.txt        # 当前激活的预设
```

### 5.2 备份与恢复

**备份**：
```bash
python -m src.media_tools.config_manager --backup
# 备份保存到 config/backups/20260412_103045/
```

**恢复**：
```bash
python -m src.media_tools.config_manager --interactive
# 选择"恢复配置"，选择备份
```

### 5.3 迁移配置

**导出**：
```bash
python -m src.media_tools.config_manager --interactive
# 选择"导出配置"，指定目录
```

**导入**：
```bash
python -m src.media_tools.config_manager --interactive
# 选择"导入配置"，选择目录
```

---

## 6. 故障排查

### 6.1 常见问题

**Q: 下载失败怎么办？**
```bash
# 1. 运行诊断
python -m src.media_tools.error_diagnosis --error "下载失败"

# 2. 检查网络
ping douyin.com

# 3. 重新认证
python cli_v2.py → 7. 账号认证 → 1. 抖音扫码登录
```

**Q: 转写失败怎么办？**
```bash
# 1. 检查配额
qwt quota status

# 2. 领取配额
qwt quota claim

# 3. 重新认证
python cli_v2.py → 7. 账号认证 → 2. Qwen AI认证
```

**Q: 配置乱了怎么办？**
```bash
# 1. 查看当前状态
python -m src.media_tools.config_manager --status

# 2. 修复常见问题
python -m src.media_tools.config_manager --fix

# 3. 如果有备份，恢复
python -m src.media_tools.config_manager --interactive
```

### 6.2 日志查看

日志文件位于 `logs/` 目录：

```bash
# 查看最新日志
tail -f logs/latest.log

# 搜索错误
grep -i error logs/*.log
```

### 6.3 获取帮助

```bash
# 查看帮助
./run.sh help

# 查看文档
cat README_V2.md

# 查看演示
./run.sh demo
```

---

## 7. 最佳实践

### 7.1 新手建议

1. **先用新手预设**
   ```bash
   python -m src.media_tools.config_presets --apply beginner
   ```

2. **从单个视频开始**
   - 先测试转写1个视频
   - 确认正常后再批量处理

3. **定期备份配置**
   ```bash
   python -m src.media_tools.config_manager --backup
   ```

### 7.2 高效使用技巧

1. **使用关注列表批量下载**
   - 先添加常看的博主
   - 定期运行"批量处理"

2. **开启自动清理**
   - 导出后自动删除云端记录
   - 转写后自动删除原视频

3. **监控统计**
   - 定期查看统计面板
   - 了解自己的使用习惯

### 7.3 服务器部署

1. **使用服务器预设**
   ```bash
   python -m src.media_tools.config_presets --apply server
   ```

2. **Docker部署**
   ```bash
   docker build -t media-tools .
   docker run -d media-tools
   ```

3. **定时任务**
   ```bash
   # 添加到crontab，每天自动处理
   0 2 * * * cd /path/to/media-tools && ./run.sh test
   ```

---

## 🎉 恭喜你学完了！

现在你已经掌握了 Media Tools V2 的所有使用方法！

**下一步**：
- 📝 查看 [CHANGELOG.md](CHANGELOG.md) 了解更新
- 🤝 查看 [CONTRIBUTING.md](CONTRIBUTING.md) 参与贡献
- 💬 遇到问题？创建 Issue 寻求帮助

**祝你使用愉快！** 🚀
