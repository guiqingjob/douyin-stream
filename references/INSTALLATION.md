# 安装指南 (Installation Guide)

本技能依赖特定环境与 Python 库。请按照以下说明依次完成环境配置。

## 1. 环境自检工具 (推荐)
本项目内置了环境自检脚本，可以帮助你一键确认当前环境是否满足要求：
```bash
python scripts/check_env.py
```
若检查未通过，请继续阅读下方的详细安装步骤。

## 2. 系统依赖

### Python 版本
要求：**Python 3.9 - 3.13** (由于底层 `f2` 库的限制)。

### 浏览器 (Playwright 扫码登录所需)
无需手动下载普通浏览器，后续通过 Python 的 `playwright` 命令行自动安装专用的 Chromium 浏览器即可。

### FFmpeg (视频压缩功能所需)
**可选**：如果您不需要使用 `scripts/compress.py` 压缩视频功能，则可跳过此步骤。

| 操作系统 | 安装命令 / 下载方式 |
| :--- | :--- |
| **macOS** | `brew install ffmpeg` |
| **Ubuntu/Debian** | `sudo apt install ffmpeg` |
| **Windows** | `choco install ffmpeg` 或从 [FFmpeg 官网](https://ffmpeg.org/download.html) 下载并配置环境变量 |

## 3. Python 依赖包

本项目依赖如下核心包：
| 包名 | 用途 |
| :--- | :--- |
| `f2` | 抖音视频下载核心框架 |
| `playwright` | 浏览器自动化（用于扫码登录获取 Cookie） |
| `pyyaml` | YAML 配置文件解析 |
| `httpx` | 异步 HTTP 客户端 |
| `aiofiles` | 异步文件操作 |

### 安装命令

1. **安装 Python 依赖库**：
```bash
pip install f2 playwright pyyaml httpx aiofiles
```

2. **安装 Playwright 浏览器组件**：
```bash
playwright install chromium
```
> **注意**：如果上述命令因网络问题失败，请尝试设置相应的镜像源，或多试几次。

## 4. 初始化配置文件

安装完所有依赖后，初始化你的个人配置：

```bash
# 如果 config 目录不存在，请先创建
mkdir -p config

# 复制模板文件
cp config/config.yaml.example config/config.yaml
cp config/following.json.example config/following.json
```

接下来，你就可以参考 [使用说明 (USAGE.md)](USAGE.md) 进行配置并开始下载了。