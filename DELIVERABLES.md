# 交付产物文档

## 一、项目交付物清单

### 1. 核心产物

| 产物 | 路径 | 说明 |
|------|------|------|
| CLI 入口 | `cli.py` | 统一交互式命令行入口 |
| Pipeline 模块 | `src/media_tools/pipeline/` | 自动化流程编排 |
| 转写模块 | `src/media_tools/transcribe/` | Qwen 转写核心 |
| 配置模板 | `config/` | 抖音和转写配置 |
| 依赖配置 | `requirements.txt` | Python 依赖清单 |

### 2. 文档产物

| 文档 | 路径 | 说明 |
|------|------|------|
| 项目规划 | `PLAN.md` | 架构设计和开发计划 |
| 交付说明 | `DELIVERABLES.md` | 本文档 |
| 使用手册 | `README.md` | 项目介绍和使用指南 |
| 更新日志 | `CHANGELOG.md` | 版本更新记录 |
| 常见问题 | `references/FAQ.md` | 常见问题解答 |

### 3. 配置模板

| 文件 | 路径 | 说明 |
|------|------|------|
| 抖音配置示例 | `config/config.yaml.example` | Cookie、下载路径等 |
| 关注列表示例 | `config/following.json.example` | 关注的博主名单 |
| 转写环境变量 | `config/transcribe/.env.example` | Qwen 转写配置 |
| 账号配置示例 | `config/transcribe/accounts.example.json` | 多账号配置 |

### 4. 输出目录

| 目录 | 说明 | 产物类型 |
|------|------|----------|
| `downloads/` | 抖音视频下载 | MP4 视频文件 |
| `transcripts/` | 转写文稿输出 | MD/DOCX 文稿文件 |
| `logs/` | 运行日志 | 日志文件 |
| `.auth/` | 认证状态 | Playwright 状态文件 |

---

## 二、Pipeline 功能交付

### 2.1 核心功能

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│  抖音视频下载  │ ──> │  Qwen转写     │ ──> │  文稿输出   │
│  (MP4)      │     │  (直接支持)   │     │  (md/docx) │
└─────────────┘     └──────────────┘     └────────────┘
```

### 2.2 使用场景

#### 场景 1：单个视频一键转写
```bash
# 交互式菜单
$ python cli.py
选择: 5. 下载并自动转写（Pipeline）
  → 输入抖音链接
  → 自动下载视频
  → 自动上传转写
  → 输出文稿：transcripts/{视频名}-{timestamp}.md
```

#### 场景 2：批量转写关注博主
```bash
# 交互式菜单
选择: 5. 下载并自动转写（Pipeline）
  → 选择：从关注列表
  → 自动遍历所有博主
  → 下载新视频并转写
  → 输出文稿目录
```

#### 场景 3：增量同步
```bash
# 只处理新视频
选择: 5. 下载并自动转写（Pipeline）
  → 选择：同步模式
  → 检查更新
  → 仅处理新视频
  → 输出文稿
```

### 2.3 配置项

```yaml
# config/pipeline.yaml（新增）
pipeline:
  # 转写设置
  transcribe:
    account: default           # 使用哪个账号
    export_format: md           # 输出格式：md/docx
    output_dir: ./transcripts/  # 输出目录
    delete_after_export: false  # 转写后删除云端记录
    
  # 清理设置
  cleanup:
    remove_video: false         # 转写后删除视频
    keep_original: true         # 保留原视频
```

---

## 三、原有功能保留

### 3.1 抖音功能（完整保留）

| 功能 | 菜单选项 | 说明 |
|------|----------|------|
| 检查博主更新 | 1 | 检查已关注博主是否有新视频 |
| 下载所有更新 | 2 | 批量下载所有新视频 |
| 关注列表管理 | 3 | 添加/移除/批量导入博主 |
| 视频下载 | 4 | 单博主/全量/采样下载 |
| 视频压缩 | 6 | FFmpeg 视频压缩 |
| 生成数据看板 | 7 | Web 可视化数据面板 |
| 系统设置 | 8 | 环境检测/扫码登录 |
| 数据清理 | 9 | 清理数据库和本地文件 |

### 3.2 转写功能（新增子命令）

| 命令 | 说明 |
|------|------|
| `media-tools transcribe run video.mp4` | 单文件转写 |
| `media-tools transcribe batch ./folder` | 批量转写 |
| `media-tools transcribe auth` | 认证管理 |
| `media-tools transcribe accounts status` | 账号状态 |
| `media-tools transcribe quota claim` | Quota 补领 |

---

## 四、环境要求

### 4.1 系统依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 运行环境 |
| FFmpeg | 最新稳定版 | 视频压缩（可选） |
| Playwright | >=1.40.0 | 浏览器自动化 |

### 4.2 Python 依赖

```txt
# requirements.txt
f2>=1.0.0              # 抖音下载框架
playwright>=1.40.0     # 浏览器自动化
pyyaml>=6.0.0          # YAML 配置解析
questionary>=2.0.0     # 交互式命令行
rich>=13.0.0           # 终端美化输出
```

### 4.3 安装步骤

```bash
# 1. 克隆项目
cd /path/to/media-tools

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 4. 初始化配置
cp config/config.yaml.example config/config.yaml
cp config/following.json.example config/following.json
cp config/transcribe/.env.example config/transcribe/.env

# 5. 启动
python cli.py
```

---

## 五、验收标准

### 5.1 功能验收

- [ ] 启动 CLI 后进入交互式菜单
- [ ] 选项 1-4、6-9 功能与原版一致
- [ ] 选项 5（Pipeline）可完成：下载 → 转写 → 输出
- [ ] 支持单个视频链接转写
- [ ] 支持从关注列表批量转写
- [ ] 支持增量同步（只处理新视频）
- [ ] 转写输出格式支持 md 和 docx
- [ ] 错误处理和重试机制正常

### 5.2 兼容性验收

- [ ] 原有 `config/config.yaml` 配置可无缝迁移
- [ ] 原有 `config/following.json` 关注列表可正常使用
- [ ] 原有 `douyin_users.db` 数据库可正常读取
- [ ] 原有下载记录不丢失

### 5.3 文档验收

- [x] PLAN.md - 项目规划文档
- [x] DELIVERABLES.md - 交付产物文档
- [ ] README.md - 更新为新版使用说明
- [ ] references/ - 保留原有参考文档

---

## 六、已知限制

1. **Quota 限制**：Qwen 转写有每日上传配额，超出后需等待或补领
2. **文件大小**：单个文件上传大小受限（具体查看 Qwen 官方说明）
3. **并发限制**：批量转写时需注意并发数，避免触发限流
4. **网络要求**：需要稳定的网络连接访问抖音和 Qwen API

---

## 七、后续优化方向

1. **性能优化**
   - 批量转写时复用 Playwright 实例
   - 支持断点续传
   - 优化轮询间隔

2. **功能扩展**
   - 支持更多视频平台（快手、B站等）
   - 支持音频文件直接转写
   - 支持文稿后处理（摘要、关键词等）

3. **用户体验**
   - Web 管理界面
   - 进度条和实时状态
   - 配置文件热重载

---

## 八、项目状态

| 阶段 | 状态 | 完成度 |
|------|------|--------|
| 阶段 1：基础迁移 | 进行中 | 30% |
| 阶段 2：Pipeline 开发 | 未开始 | 0% |
| 阶段 3：集成测试 | 未开始 | 0% |
| 阶段 4：文档和优化 | 未开始 | 0% |

**当前版本**: v0.1.0-alpha
**最后更新**: 2026-04-11
