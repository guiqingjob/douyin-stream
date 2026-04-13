# 使用说明 (Usage Guide)

本文档将详细介绍抖音批量下载工具的核心操作流程、脚本参数说明和高级配置。

---

## 一、配置 Cookie（必需）

抖音视频的获取高度依赖 Cookie 认证。请至少选择一种方式配置你的 Cookie。

### 方式一：扫码自动提取（推荐）

通过调用 `login.py` 脚本，可弹出浏览器进行扫码，自动获取 Cookie 并保存。
```bash
# 启动浏览器获取 Cookie，并持久化保存登录状态
python scripts/login.py --persist
```
- `--persist`：启用持久化模式，下次扫码时可能自动登录，免去重复扫码。
- 扫码成功后，Cookie 会自动写入 `config/config.yaml`。

### 方式二：手动配置
如果你在其他浏览器中已经登录，可手动抓取并填写到 `config/config.yaml` 文件中：
```yaml
cookie:
  auto_extract: true    # 优先从浏览器自动读取
  manual: "ttwid=xxx; sessionid=yyy; passport_csrf_token=zzz;"
```

---

## 二、视频下载

### 1. 单个博主下载 (`download.py`)
用于下载单一博主的主页所有视频，支持指定下载数量限制。
```bash
# 下载指定链接的全部视频
python scripts/download.py "https://www.douyin.com/user/MS4wLjABAAAA..."

# 限制仅下载最新 10 个视频
python scripts/download.py "https://www.douyin.com/user/MS4wLjABAAAA..." --max-counts=10

# 在后台静默运行任务
python scripts/download.py "https://www.douyin.com/user/MS4wLjABAAAA..." --daemon
```

### 2. 批量博主下载 (`batch-download.py`)
如果你配置了多位关注博主（`following.json`），可通过此脚本进行全量批量或抽样下载。
```bash
# 交互式：提供菜单供你选择博主
python scripts/batch-download.py

# 一键全量：自动循环下载所有关注列表中的博主
python scripts/batch-download.py --all

# 采样模式：每个博主仅下载 1 个最新视频（适合快速更新基础数据面板）
python scripts/batch-download.py --sample

# 跳过确认提示（适合定时任务/自动化）
python scripts/batch-download.py --all --yes
```

---

## 三、关注列表管理 (`manage-following.py`)

`following.json` 是用于记录你需要跟踪/批量下载的博主名单。使用以下脚本可避免手动编辑 JSON 格式错误。

| 命令 | 说明 | 示例 |
| :--- | :--- | :--- |
| `--list` | 列表查看当前所有的关注博主及状态 | `python scripts/manage-following.py --list` |
| `--add` | 根据主页链接新增博主到关注列表 | `python scripts/manage-following.py --add "https://www.douyin.com/user/..."` |
| `--batch` | 交互式批量粘贴链接添加博主 | `python scripts/manage-following.py --batch` |
| `--remove` | 移除指定 UID 博主（不删除已下载视频） | `python scripts/manage-following.py --remove 1234567890` |
| `--search` | 根据昵称、UID或简介全局检索关注列表 | `python scripts/manage-following.py --search "张三"` |
| `--update` | 同步并更新所有博主的基础信息 | `python scripts/manage-following.py --update` |

---

## 四、智能视频压缩 (`compress.py`)

如果你需要节省磁盘空间，可使用内置的 FFmpeg 视频压缩功能。

| 参数 | 说明 | 示例 |
| :--- | :--- | :--- |
| `(无参数)` | 默认遍历所有已下载目录进行压缩 | `python scripts/compress.py` |
| `--user` | 仅压缩特定博主目录下的视频 | `python scripts/compress.py --user "张三"` |
| `--file` | 仅压缩特定的 MP4 文件 | `python scripts/compress.py --file video.mp4` |
| `--keep` | 保留原文件（默认行为是**替换原文件**） | `python scripts/compress.py --keep` |
| `--crf` | 设置视频压缩质量（0-51，默认32） | `python scripts/compress.py --crf 38` |
| `--preset` | 压缩速度预设（如 fast, medium, slow） | `python scripts/compress.py --preset medium` |
| `--aggressive`| 激进压缩：降低分辨率并牺牲画质获取极高压缩率 | `python scripts/compress.py --aggressive` |

---

## 五、生成 Web 可视化数据 (`generate-data.py`)

在完成下载或压缩后，你可能希望以更美观的方式查看本地视频及点赞、评论等数据统计。

```bash
# 生成或更新本地 Web 数据 (data.js)
python scripts/generate-data.py
```

执行成功后，工具会在你的下载目录中生成静态 `index.html` 与 `data.js`，你只需**在文件管理器中双击打开 `index.html`**，即可直接在浏览器中享受丝滑的视频与数据交互体验（无需任何后端服务器支持）。

---

## 六、自定义下载路径配置

编辑 `config/config.yaml` 调整下载目录：

```yaml
# 留空时默认：
# macOS 存放在 ~/Downloads/抖音视频下载
# Windows 存放在 C:\Users\<用户名>\Downloads\抖音视频下载
download_path: ""

# 或者设置绝对路径：
# download_path: "~/Movies/Douyin"
```
视频将会以 `{download_path}/{博主昵称}/` 的目录结构自动分拣。
