# 🔧 故障排查手册

> 快速定位和解决常见问题

---

## 📋 目录

1. [安装问题](#1-安装问题)
2. [配置问题](#2-配置问题)
3. [下载问题](#3-下载问题)
4. [转写问题](#4-转写问题)
5. [Pipeline问题](#5-pipeline问题)
6. [性能问题](#6-性能问题)
7. [其他问题](#7-其他问题)

---

## 1. 安装问题

### Q: Python版本不对

**症状**:
```
ERROR: Package requires Python 3.11+
```

**解决方案**:
```bash
# 检查Python版本
python3 --version

# 如果低于3.11，升级Python
# macOS
brew install python@3.11

# Ubuntu
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# 使用pyenv（推荐）
curl https://pyenv.run | bash
pyenv install 3.11.0
pyenv global 3.11.0
```

### Q: 依赖安装失败

**症状**:
```
ERROR: Could not install requirements
```

**解决方案**:
```bash
# 1. 升级pip
pip install --upgrade pip

# 2. 清理缓存
pip cache purge

# 3. 重新安装
pip install -r requirements.txt

# 4. 如果某个包失败，单独安装
pip install playwright rich questionary pyyaml f2
```

### Q: Playwright安装失败

**症状**:
```
ERROR: playwright install failed
```

**解决方案**:
```bash
# 1. 安装playwright
pip install playwright

# 2. 安装浏览器
playwright install chromium

# 3. 安装系统依赖（Ubuntu/Debian）
playwright install-deps chromium

# 4. macOS不需要额外步骤
```

---

## 2. 配置问题

### Q: 配置文件不存在

**症状**:
```
ERROR: config/config.yaml not found
```

**解决方案**:
```bash
# 运行初始化
./run.sh setup

# 或手动创建
cp config/config.yaml.example config/config.yaml
cp config/following.json.example config/following.json
cp config/transcribe/.env.example config/transcribe/.env
```

### Q: Cookie过期

**症状**:
```
ERROR: Cookie expired
ERROR: Authentication failed
```

**解决方案**:
```bash
# 重新登录
python cli_v2.py
选择 "7. 账号认证" → "1. 抖音扫码登录"

# Cookie有效期约24小时，需定期更新
```

### Q: 配置混乱

**症状**:
不知道哪个配置生效了

**解决方案**:
```bash
# 查看配置状态
python -m src.media_tools.config_manager --status

# 修复常见问题
python -m src.media_tools.config_manager --fix

# 如果有备份，恢复
python -m src.media_tools.config_manager --interactive
```

---

## 3. 下载问题

### Q: 下载失败

**症状**:
```
ERROR: Download failed
ERROR: Connection timeout
```

**诊断步骤**:

1. **检查网络**
```bash
ping douyin.com
curl -I https://douyin.com
```

2. **运行诊断**
```bash
python -m src.media_tools.error_diagnosis --error "Connection timeout"
```

3. **检查Cookie**
```bash
# 查看config/config.yaml中的cookie
cat config/config.yaml | grep cookie
```

**解决方案**:
- 切换网络（WiFi → 手机热点）
- 重新登录获取新Cookie
- 检查防火墙设置
- 等待几分钟后重试

### Q: 下载速度慢

**症状**:
下载速度只有几百KB/s

**解决方案**:
```bash
# 1. 检查网络带宽
speedtest-cli

# 2. 降低并发数
# 编辑 config/config.yaml
max_concurrent: 3  # 降低到3

# 3. 检查是否有其他程序占用带宽
```

### Q: 重复下载

**症状**:
已经下载的视频又下载了一遍

**解决方案**:
```bash
# 检查数据库
sqlite3 douyin_users.db "SELECT count(*) FROM video_metadata;"

# 清理并重新同步
python cli_v2.py
选择 "10. 数据清理" → "清理数据库"

# 确保增量下载功能正常
```

---

## 4. 转写问题

### Q: 配额不足

**症状**:
```
ERROR: Quota exceeded
ERROR: No quota available
```

**解决方案**:
```bash
# 1. 查看配额
qwt quota status

# 2. 领取配额
qwt quota claim

# 3. 如果所有账号都用完
# 等待下个月重置
# 或添加新账号
```

### Q: 转写失败

**症状**:
```
ERROR: Transcription failed
```

**诊断**:
```bash
# 运行诊断
python -m src.media_tools.error_diagnosis --error "Transcription failed"

# 检查日志
tail -f logs/latest.log
```

**常见原因**:
1. 配额不足 → 领取配额
2. 认证过期 → 重新认证
3. 网络问题 → 检查网络
4. 文件格式 → 确认是MP4/M4A/WAV

**解决方案**:
```bash
# 重新认证
python cli_v2.py
选择 "7. 账号认证" → "2. Qwen AI认证"
```

### Q: 转写结果不准确

**症状**:
转写的文字有很多错误

**可能原因**:
- 视频音质差
- 背景音乐太大
- 方言/口音问题

**解决方案**:
- 选择音质清晰的视频
- 优先转写人声为主的视频
- 手动校对转写结果

---

## 5. Pipeline问题

### Q: Pipeline中断

**症状**:
下载成功，但没自动转写

**解决方案**:
```bash
# 1. 检查日志
tail -f logs/latest.log

# 2. 手动转写已下载的视频
python cli_v2.py
选择 "4. 单文件转写"

# 3. 检查Pipeline配置
python cli_v2.py
选择 "8. 配置中心" → "Pipeline配置"
```

### Q: 断点续传不工作

**症状**:
中断后重新开始，从头处理

**解决方案**:
```bash
# 检查状态文件
cat .pipeline_state.json

# 如果文件损坏，删除重新
rm .pipeline_state.json

# 重新运行Pipeline
```

---

## 6. 性能问题

### Q: 内存占用过高

**症状**:
程序运行占用几个GB内存

**解决方案**:
```bash
# 1. 降低并发数
# config/config.yaml
concurrency: 3

# 2. 分批处理
# 不要一次处理太多视频

# 3. 重启程序
# 释放内存泄漏
```

### Q: 磁盘空间不足

**症状**:
```
ERROR: No space left on device
```

**解决方案**:
```bash
# 1. 检查磁盘使用
df -h

# 2. 清理旧视频
python cli_v2.py
选择 "10. 数据清理"

# 3. 开启自动删除
# Pipeline配置中开启"转写后删除原视频"

# 4. 移动数据到其他盘
mv downloads/ /Volumes/ExternalDrive/
ln -s /Volumes/ExternalDrive/downloads downloads
```

---

## 7. 其他问题

### Q: 程序崩溃

**症状**:
突然退出或报错

**解决方案**:
```bash
# 1. 查看错误日志
tail -n 100 logs/latest.log

# 2. 运行诊断
python -m src.media_tools.error_diagnosis --full

# 3. 更新到最新版本
git pull
pip install -r requirements.txt

# 4. 如果问题持续，提交Issue
# 包含错误日志和复现步骤
```

### Q: 中文乱码

**症状**:
文件名或内容出现乱码

**解决方案**:
```bash
# 确保locale设置正确
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# macOS通常不需要额外设置
# Linux可能需要:
sudo locale-gen zh_CN.UTF-8
```

---

## 🔍 快速诊断命令

```bash
# 一键诊断
./run.sh diag

# 或
python -m src.media_tools.error_diagnosis --full

# 查看日志
tail -f logs/latest.log

# 检查配置
python -m src.media_tools.config_manager --status

# 查看统计
python -m src.media_tools.stats_panel

# 运行测试
./run.sh test
```

---

## 💡 获取帮助

如果以上方法都无法解决：

1. **查看文档**
   - [README_V2.md](README_V2.md)
   - [TUTORIAL.md](TUTORIAL.md)

2. **查看演示**
   ```bash
   ./run.sh demo
   ```

3. **提交Issue**
   - 描述问题
   - 附上错误日志
   - 说明复现步骤

---

**最后更新**: 2026-04-12
