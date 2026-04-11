# 项目规划文档：media-tools

## 一、项目概述

### 目标
将抖音视频下载和 Qwen 音频转写两个功能整合到一个统一的 CLI 工具中，实现**一键式自动化工作流**：
```
抖音视频下载 → 自动上传 Qwen 转写 → 输出文稿 (md/docx)
```

### 核心价值
- 保留原有的抖音交互式 CLI 风格
- 新增自动化 pipeline 功能
- 支持分步操作和一键完成两种模式

---

## 二、架构设计

### 2.1 项目结构
```
media-tools/
├── cli.py                      # 主入口（保留抖音交互式风格）
├── pyproject.toml              # 统一项目配置（新增）
├── requirements.txt            # Python 依赖
│
├── src/media_tools/            # 新增：标准化包结构
│   ├── __init__.py
│   ├── transcribe/             # 从 qwen_transcribe 迁移
│   │   ├── __init__.py
│   │   ├── flow.py             # 核心转写流程
│   │   ├── config.py           # 配置管理
│   │   ├── http.py             # HTTP 请求封装
│   │   ├── oss_upload.py       # OSS 文件上传
│   │   ├── quota.py            # Quota 管理
│   │   ├── runtime.py          # 运行时工具
│   │   ├── accounts.py         # 账号管理
│   │   ├── errors.py           # 异常定义
│   │   └── result_metadata.py  # 结果元数据
│   │
│   ├── pipeline/               # 新增：流程编排
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # Pipeline 编排器
│   │   └── config.py           # Pipeline 配置
│   │
│   └── cli/                    # 新增：CLI 子命令
│       ├── __init__.py
│       └── pipeline.py         # Pipeline 子命令
│
├── scripts/                    # 抖音脚本（保留原有结构）
│   ├── core/                   # 核心业务逻辑
│   │   ├── downloader.py       # 视频下载
│   │   ├── following_mgr.py    # 关注管理
│   │   ├── compressor.py       # 视频压缩
│   │   └── ...
│   └── utils/                  # 工具模块
│
├── config/                     # 配置目录
│   ├── config.yaml             # 抖音配置
│   ├── following.json          # 关注列表
│   └── transcribe/             # 转写配置（新增）
│       ├── .env                # 环境变量
│       └── accounts.json       # 账号配置
│
├── downloads/                  # 下载输出
├── transcripts/                # 转写输出（新增）
├── .auth/                      # 认证状态（新增）
└── logs/                       # 日志目录
```

### 2.2 CLI 设计

#### 主菜单（交互式）
```
╔══════════════════════════════════════════════╗
║          media-tools 主菜单                   ║
╠══════════════════════════════════════════════╣
║  1. 检查博主更新                              ║
║  2. 下载所有更新                              ║
║  3. 关注列表管理                              ║
║  4. 视频下载                                  ║
║  5. 🆕 下载并自动转写（Pipeline）              ║
║  6. 视频压缩                                  ║
║  7. 生成数据看板                              ║
║  8. 系统设置                                  ║
║  9. 数据清理                                  ║
║  0. 退出程序                                  ║
╚══════════════════════════════════════════════╝
```

#### 子命令模式（高级用户）
```bash
# Pipeline 命令
media-tools pipeline run --url "https://douyin.com/video/xxx"
media-tools pipeline from-following --all
media-tools pipeline from-following --select
media-tools pipeline sync

# 抖音命令（保留原有功能）
media-tools douyin download
media-tools douyin check-updates

# 转写命令
media-tools transcribe run video.mp4
media-tools transcribe batch ./folder
```

---

## 三、开发阶段

### 阶段 1：基础迁移
- [x] 创建项目目录，复制 douyindownload_renew
- [x] 初始化 Git 仓库
- [x] 编写规划文档
- [ ] 迁移 qwen_transcribe 核心模块到 `src/media_tools/transcribe/`
- [ ] 合并依赖和配置文件
- [ ] 创建 `.env` 和 accounts.json 配置模板

### 阶段 2：Pipeline 开发
- [ ] 创建 `src/media_tools/pipeline/` 模块
- [ ] 实现 Pipeline 编排器（orchestrator.py）
- [ ] 实现 CLI 子命令
- [ ] 修改主菜单，增加 Pipeline 选项

### 阶段 3：集成测试
- [ ] 测试单个视频：下载 → 转写 → 输出
- [ ] 测试批量：关注列表 → 批量下载转写
- [ ] 测试增量：只处理新视频
- [ ] 测试错误处理和重试

### 阶段 4：文档和优化
- [ ] 更新 README.md
- [ ] 编写使用指南
- [ ] 性能优化和异常处理
- [ ] 最终测试和发布

---

## 四、关键设计决策

### 4.1 依赖合并
两个项目的公共依赖：
- `playwright>=1.40.0` - 浏览器自动化
- `rich>=13.0.0` - 终端美化
- `questionary>=2.0.0` - 交互菜单

抖音独有依赖：
- `f2>=1.0.0` - 下载框架
- `pyyaml>=6.0.0` - YAML 配置

转写独有依赖：
- 无（依赖已覆盖）

### 4.2 认证共存
- 抖音：`config/config.yaml` 中存储 Cookie
- 转写：`.auth/` 目录存储 Playwright 状态
- 两者独立，互不干扰

### 4.3 路径设计
```
downloads/              # 抖音视频下载
└── {博主昵称}/
    └── *.mp4

transcripts/            # 转写文稿输出
└── {博主昵称}/
    └── {视频名}-{timestamp}.md
```

### 4.4 Pipeline 流程
```python
async def pipeline_run(video_path: Path):
    # 1. 视频已下载（MP4）
    # 2. 直接上传转写（Qwen 支持 MP4）
    result = await run_real_flow(
        file_path=video_path,
        auth_state_path=transcribe_config.auth_state,
        download_dir=TRANSCRIPTS_DIR,
        export_config=get_export_config("md"),
        should_delete=False,
    )
    # 3. 输出文稿：transcripts/{视频名}-{timestamp}.md
    return result.export_path
```

---

## 五、风险点

### 5.1 已知风险
1. **异步/同步混用**：抖音用同步包装异步，转写纯异步，需统一
2. **Playwright 实例**：两个模块都用 Playwright，需确认是否共享浏览器实例
3. **配置路径**：抖音用 `config/config.yaml`，转写用 `.env`，需统一加载逻辑

### 5.2 缓解措施
- 为 Pipeline 创建独立的 Playwright 上下文
- 配置路径统一从环境变量或 `.env` 加载
- 异步调用统一用 `asyncio.run()` 包装

---

## 六、成功标准

- [x] Git 仓库初始化
- [ ] 一条命令完成：下载 → 转写 → 输出文稿
- [ ] 保留原有抖音 CLI 交互风格
- [ ] 所有原有功能正常工作
- [ ] 支持批量和增量处理
- [ ] 完整的错误处理和日志
- [ ] 文档齐全

---

## 七、时间线

> 注：不预估时间，按阶段推进

1. **阶段 1** → 完成基础迁移
2. **阶段 2** → 完成 Pipeline 开发
3. **阶段 3** → 完成集成测试
4. **阶段 4** → 完成文档和发布

每个阶段完成后进行验收，确认无误后进入下一阶段。
