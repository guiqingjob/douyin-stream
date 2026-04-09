# 🤝 参与贡献指南 (Contributing)

欢迎参与 `douyin-download-renew` 的开发！我们非常期待您的加入，共同打造这个强大、易用的短视频自动下载与数据分析管家。

为了保持代码库的整洁和高质量，请在提交代码前仔细阅读以下指南。

---

## 1. 发现 Bug 或 提出建议

如果您在使用过程中发现了任何问题，或者有想要增加的新功能，请在 GitHub Issues 中提出。

在提交 Issue 时，请尽量包含以下信息：
- 您的操作系统和 Python 版本
- 复现问题的详细步骤
- 终端中打印出的错误日志（如有）
- 您期望的功能效果（如果是新功能建议）

---

## 2. 参与开发与提交代码 (Pull Request)

如果您想亲自修复 Bug 或添加新功能，请按照以下步骤提交 Pull Request (PR)：

### 第一步：Fork 并克隆项目
点击项目主页右上角的 `Fork` 按钮，将项目 Fork 到您的个人账号下，然后克隆到本地：
```bash
git clone https://github.com/<您的用户名>/douyin-download-renew.git
cd douyin-download-renew
```

### 第二步：配置开发环境
安装所有依赖（包括开发测试工具 `flake8`, `black`, `isort`）：
```bash
pip install -r requirements.txt
pip install flake8 black isort
```

### 第三步：创建新分支
请从 `main` 分支切出一个描述性的新分支：
```bash
# 修复 Bug 的分支名示例
git checkout -b fix/auth-parser-error

# 添加新功能的分支名示例
git checkout -b feat/add-fastapi-support
```

### 第四步：编写代码并测试
在开发过程中，请确保您的代码遵循现有的架构设计：
- 所有通用工具方法请放在 `scripts/utils/` 下。
- 所有日志输出必须使用 `scripts.utils.logger` 中的 `logger.info()` 或 `logger.error()`，**严禁使用 `print()`**。
- 请确保不破坏核心的“增量下载”和“SQLite 落库”逻辑。

### 第五步：代码格式化与静态检查 (关键)
本项目启用了 GitHub Actions 进行自动代码质量检查。在提交代码前，请务必在本地运行以下命令以确保代码符合规范：

1. **自动格式化代码** (按照 Black 和 isort 标准)：
```bash
black scripts/
isort scripts/
```

2. **静态语法检查** (修复所有警告)：
```bash
flake8 scripts/ --ignore=E501,E402,W293,E226,W503,F401,F841
```

### 第六步：提交并推送
提交信息请遵循 [Angular 提交规范](https://github.com/angular/angular/blob/main/CONTRIBUTING.md#-commit-message-format)：
```bash
git add .
git commit -m "feat: 增加对某个新接口的解析支持"
git push origin <您的分支名>
```

### 第七步：发起 Pull Request
回到本项目的 GitHub 页面，点击 `Compare & pull request`，详细描述您的改动，并提交。维护者会尽快 Review 您的代码。

---

## 3. 提交信息规范 (Commit Message Format)

请使用以下前缀来标记您的提交类型：
- `feat:` 新增功能
- `fix:` 修复 Bug
- `docs:` 文档变更
- `style:` 代码格式修改（不影响逻辑）
- `refactor:` 代码重构（非新增功能也非修复 bug）
- `perf:` 性能优化
- `test:` 添加或修改测试代码
- `chore:` 构建过程或辅助工具的变动

---

感谢您为开源社区做出的贡献！🎉