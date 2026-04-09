# 认证数据抓取与解析引擎使用指南

本指南详细介绍了如何使用项目内置的「可视化认证数据解析工具」，以及如何通过规则引擎动态配置 JSON、文本等数据的采集。

## 一、可视化数据解析工具

为了解决复杂场景下扫码登录受限、自动抓包困难的问题，我们提供了基于本地 Web 服务器的可视化抓取与解析工具。

### 1. 启动工具
在项目根目录运行以下命令：
```bash
python scripts/auth_server.py
```
终端会输出：`认证可视化服务器已启动: http://localhost:8080`

### 2. 使用方法
1. 在浏览器中打开 `http://localhost:8080`。
2. 你将看到一个名为 **🔐 认证数据解析器** 的界面。
3. **数据类型**：选择你要粘贴的数据类型（Cookie 字符串、JSON 响应 或 纯文本/Headers）。
4. **规则配置名**：输入你在 `config/auth_rules.yaml` 中配置的解析规则（例如默认的 `douyin`）。
5. **粘贴原始数据**：从浏览器开发者工具 (F12) 的 Network 面板中复制目标请求的 Headers、Response 等内容粘贴到此。
6. 点击 **开始解析**，工具会根据规则自动验证长度、关键字段，并返回结构化的提取结果。

---

## 二、智能规则引擎配置

通过修改 `config/auth_rules.yaml`，您可以无需编写代码，动态新增任何网站的认证解析逻辑。

### 1. Cookie 提取示例 (抖音)
```yaml
rules:
  douyin:
    description: "抖音网页版认证"
    type: "cookie"
    required_keys:
      - "sessionid"
    optional_keys:
      - "passport_csrf_token"
      - "ttwid"
    validation:
      check_expiry: true
      min_length: 50
```

### 2. JSON 提取示例 (自定义API)
支持通过对象点语法（如 `data.user.id`）深度提取嵌套 JSON 中的字段：
```yaml
  custom_json:
    description: "自定义JSON数据提取"
    type: "json"
    mapping:
      token: "data.access_token"
      userId: "data.user.id"
      sessionId: "data.session_id"
    validation:
      check_expiry: false
```

### 3. 纯文本 / Headers 正则提取
适用于从非标准响应或原生 HTTP 请求头中提取 `Bearer Token` 等：
```yaml
  custom_text:
    description: "自定义文本数据提取"
    type: "text"
    mapping:
      token: "Bearer\\s+([A-Za-z0-9-_\\.]+)"
      userId: "User:\\s*(\\d+)"
    validation:
      check_expiry: false
```

### 4. 常见网页抓取指南：抖音 Web
如果您无法运行自动化扫码工具，可以按以下步骤手动提取抖音登录凭证：
1. 使用任意浏览器（如 Chrome、Edge）打开 [抖音网页版 (douyin.com)](https://www.douyin.com/) 并完成扫码登录。
2. 按 `F12` 键打开 **开发者工具 (Developer Tools)**。
3. 切换到 **Application (应用)** 或 **Storage (存储)** 选项卡。
4. 展开左侧的 **Cookies** 树，点击 `https://www.douyin.com`。
5. 在右侧的表格中，寻找并复制以下核心 Cookie 的 `Value` 值：
   - **`sessionid`** (必需！此为账户核心会话凭证，长度通常较长)
   - **`passport_csrf_token`** (重要！防 CSRF 攻击的 Token)
   - **`sid_guard`** / **`ttwid`** (辅助风控校验)
6. 将它们拼接为标准的 Cookie 字符串（键值对之间用分号和空格隔开）：
   ```text
   sessionid=YOUR_SESSION_ID; passport_csrf_token=YOUR_TOKEN; sid_guard=YOUR_GUARD; ttwid=YOUR_TTWID;
   ```
7. 把这串内容直接复制到我们的 **可视化数据解析器** 中校验，或手动写入 `config/config.yaml` 文件的 `cookie` 字段。

---

## 三、异常处理与错误代码对照

当用户提供的数据无效、字段缺失或解析失败时，系统会返回对应的错误信息，并触发异常阻断。

| 错误信息 / 场景 | 触发原因 | 解决方案 |
| :--- | :--- | :--- |
| `缺少必填字段: [key]` | 提供的 Cookie 字符串或 JSON 中未包含在 `required_keys` 声明的核心字段。 | 检查复制的请求是否完整，通常需要从已登录的首页刷新获取完整 Cookie。 |
| `Cookie 长度过短 (<N)` | 捕获的文本过短，未达到规则设置的 `min_length` 阈值，涉嫌为残缺数据。 | 重新完整复制请求头中的 `Cookie: ` 字段值。 |
| `非法的 JSON 格式` | 选择解析类型为 JSON，但输入了包含非 JSON 字符的字符串。 | 确保粘贴的内容仅为标准的 JSON Response。 |
| `未能提取任何有效字段` | 正则匹配失败，或 JSON 路径不匹配。 | 检查 `auth_rules.yaml` 中的 `mapping` 路径或正则表达式是否正确。 |

*注：在业务代码调用中，当遇到此类解析失败时，系统将抛出异常并提示用户重新采集认证数据。*