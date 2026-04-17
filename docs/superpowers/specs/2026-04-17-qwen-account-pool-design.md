# Qwen 账号池统一管理与额度策略设计

## 背景问题

- 当前 UI 中的「Qwen 账号池」使用数据库表 `Accounts_Pool(platform='qwen')` 存储账号 Cookie，用于管理列表展示和备注。
- 转写执行、额度统计、自动领取逻辑则基于转写子模块的 `accounts.json` + `.auth/*` 文件体系：
  - 账号轮换策略由 `QWEN_ACCOUNTS_FILE` + `QWEN_ACCOUNT_STRATEGY` 驱动。
  - 额度查询与权益领取通过 `quota.py / account_status.py` 按 `auth_state_path` 抓取。
- 两套体系之间没有联动，导致：
  - 设置页添加的 Qwen 账号不会自动参与转写轮换。
  - 额度展示中的账号信息与「账号池列表」不一致，用户不知道池里的账号具体剩余多少。
  - 自动领取额度只作用于 `accounts.json` 定义的账号，不一定覆盖 UI 中的「账号池」。

用户的目标：
- 以设置页的「Qwen 账号池」（DB）为唯一真相来源。
- 在账号列表中直接看到每个账号的剩余转写小时数。
- 转写时自动优先消耗额度高的账号；Cookie 过期时标记失效，由用户更新，不自动删除。
- 自动领取额度（手动+定时）都对账号池中的全部账号生效。
- 平时转写不频繁抓额度，只在领取额度的场景顺便刷新。

## 目标

1. **单一来源**：以 DB 表 `Accounts_Pool(platform='qwen')` 作为 Qwen 账号池的唯一配置来源。
2. **额度可见**：设置页「Qwen 账号池」列表中，每个账号显示「剩余 X 小时」，X 直接来自 Qwen 返回的 `remainingQuota`（整数小时），不再显示已用。
3. **自动使用**：转写执行时自动根据剩余小时优先使用账号，Cookie 失效则标记为失效并跳过。
4. **自动领取**：手动 `/settings/qwen/claim` 和定时任务都遍历 DB 账号池中的全部账号进行检查和领取。
5. **额度刷新策略**：平时转写不抓实时额度，只在领取额度（手动或自动）时调用额度接口刷新快照。

## 非目标

- 不引入 UI 内对 `accounts.json` 的直接编辑入口（内部可继续作为转写子模块的兼容配置文件，但不再面向用户暴露）。
- 不追求实时精确扣减（按视频时长进行分钟级估算），展示层只关注「剩余小时」的最近快照。
- 不对 Qwen 官方额度逻辑（如何计费分钟/小时等）做反推或模拟，只消费其对外接口。

## 数据模型设计

### Accounts_Pool（Qwen 账号池）

在现有表结构基础上增强：

```sql
CREATE TABLE Accounts_Pool (
  account_id TEXT PRIMARY KEY,
  platform   TEXT,
  cookie_data TEXT,
  status     TEXT DEFAULT 'active',
  last_used  TIMESTAMP,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  remark     TEXT DEFAULT '',
  auth_state_path TEXT DEFAULT '' -- 新增：该账号对应的 Qwen storageState 文件路径
);
```

约定：
- `platform='qwen'` 的记录构成 Qwen 账号池。
- `auth_state_path` 指向每个账号独立的 Playwright storageState 文件，例如：
  - `.auth/qwen-storage-state-{account_id}.json`

### Quota 状态（沿用现有）

- 使用 `.auth/quota-usage.json` 存储每个账号、每天的额度记录：
  - Key：`account_key(account_id)` + 当天日期。
  - 字段：`consumedMinutes`, `lastEquityClaimAt`, `lastEquityBeforeRemaining`, `lastEquityAfterRemaining` 等。
- 新设计中继续沿用，用于：
  - 识别是否已在当天领取额度；
  - 给 Settings 页展示「是否已领」的辅助信息（如需要）。

### 额度快照（QuotaSnapshot）

沿用 `QuotaSnapshot` 对象：

```python
@dataclass(frozen=True, slots=True)
class QuotaSnapshot:
    raw: Any
    used_upload: int          # 已用分钟
    total_upload: int         # 总分钟
    remaining_upload: int     # 剩余分钟
    gratis_upload: bool
    free: bool
```

新增一个衍生字段概念：
- `remaining_hours = remainingQuota`，直接从 Qwen 返回的 `remainingQuota`（整数小时）读取，用于展示与排序。
- 不需要持久化为单独字段，可在 Settings 状态接口中直接传出。

## 额度接口解析确认

额度抓取逻辑位于 [quota.py](file:///Users/gq/Projects/media-tools/src/media_tools/transcribe/quota.py#L122-L184)：

- 请求：

```python
quota_json = await api_json(
    api,
    "https://api.qianwen.com/growth/user/benefit/base",
    {"requestId": str(uuid.uuid4())},
    headers,
)
```

- 在 `quota_json["data"]` 中找到 `benefitType == "TINGWU_TRANSCRIPTION_DURATION"` 的权益项：
  - `usageQuota`: 已用小时（整数）。
  - `remainingQuota`: 剩余小时（整数）。
  - `totalQuotaAndUnit`: 如 `"共500小时0分钟"` 这样的总配额字符串。

当前实现：
- 将 `usageQuota` / `remainingQuota` 乘以 60 转为分钟，用于 `QuotaSnapshot.used_upload/remaining_upload`。
- 使用 `totalQuotaAndUnit` 提供总分钟精确值。

在本设计中：
- 展示与排序均使用 `remaining_hours = remainingQuota`。
- 分钟级数据仅用于本地消耗统计与内部逻辑，不用于 UI 直接显示。

## 行为设计

### 1. 额度展示（Settings 页）

接口变更：

- `GET /api/v1/settings/` 保持现有结构，仍返回：
  - `qwen_accounts`: DB 中 `Accounts_Pool(platform='qwen')` 的账号列表。
  - `status_summary.qwen_accounts_count` 等统计字段。

- `GET /api/v1/settings/qwen/status` 改造为：
  - 遍历 DB 账号池（`Accounts_Pool(platform='qwen')`），对每个账号：
    - 使用其 `auth_state_path` 调用 `get_quota_snapshot(auth_state_path=...)`；
    - 获取 `remaining_hours`（来自 `remainingQuota`）；
    - 组合 `daily_record = get_daily_quota_record(account_id)`。
  - 返回结构示例：

```json
{
  "status": "success",
  "accounts": [
    {
      "accountId": "qingyin",
      "label": "备注/昵称",
      "remaining_hours": 375,
      "status": "active",          // 或 "invalid"
      "daily": {
        "lastEquityClaimAt": "2026-04-17T08:05:00",
        "consumedMinutes": 120
      }
    }
  ]
}
```

前端展示：
- Settings 页的「Qwen 账号池」列表中，每个账号右侧显示：
  - `剩余 {remaining_hours} 小时`
- 不展示“已用多少小时”。

### 2. 账号池写入与 storageState 管理

#### 添加账号（POST /api/v1/settings/qwen/accounts）

现状：
- `save_qwen_cookie_string(req.cookie_string, default_qwen_auth_state_path())`
  - 将 Cookie 写到默认 auth_state 文件，并同步到 `auth_credentials` 表。
- 再在 `Accounts_Pool` 中插入一条记录。

改造：
- 为每个新账号生成独立的 `auth_state_path`：
  - 例如：`.auth/qwen-storage-state-{account_id}.json`
- 调用：

```python
auth_state_path = build_auth_state_path_for_account(account_id)
save_qwen_cookie_string(req.cookie_string, auth_state_path, sync_db=False)
```

- 在 `Accounts_Pool` 中插入：
  - `account_id`, `platform='qwen'`, `cookie_data`, `remark`, `auth_state_path`
- 默认不再向 `auth_credentials(platform='qwen')` 写入此账号的状态（该表仅保留默认账号兼容用途）。

#### 更新 Cookie

为账号池中的某条记录提供“更新 Cookie”的接口（可复用 `POST /settings/qwen/accounts` 或新增 `PUT /settings/qwen/accounts/{id}/cookie`），流程：
- 读取该账号的 `auth_state_path`。
- 使用新的 Cookie 字符串调用 `save_qwen_cookie_string(..., auth_state_path)` 覆盖 storageState。
- 将账号状态更新为 `active`。

#### 删除账号

`DELETE /settings/qwen/accounts/{account_id}`：
- 删除 `Accounts_Pool` 中记录。
- 删除对应 `auth_state_path` 文件（如果存在）。

### 3. 自动选择账号（执行时）

目标：优先消耗额度高的账号，Cookie 过期时不删除账号而是标记失效并跳过，用户可通过更新 Cookie 恢复。

策略：

- 执行入口（转写时）从 DB 加载所有 Qwen 账号：
  - 只使用 `status='active'` 且 `auth_state_path` 有效的账号参与排序。
  - 对每个账号读取最近一次额度快照中的 `remaining_hours`（来自近一次领取行为产生的记录）。
- 排序规则：
  - 先按 `remaining_hours` 从大到小排序。
  - 相同 `remaining_hours` 的账号之间按 round-robin（可借助 `account_pool_state_file` 中 `lastSuccessfulAccountId` 实现）。
- 执行过程中：
  - 如果 `run_real_flow` 抛出认证相关错误（根据错误类型映射到 `ErrorType.AUTH`）：
    - 将该账号标记为 `invalid`（写回 DB 的 `status` 字段）。
    - 当前任务自动尝试下一个账号。
  - 任务成功完成后：
    - 调用 `mark_account_success(account_id)` 更新 `lastSuccessfulAccountId`（用于下次 round-robin 起点）。

注意：
- 不在每个任务结束后重新抓实时额度，只依赖近期一次领取时刷新的快照。

### 4. 自动领取额度（claim）

#### 手动领取（POST /settings/qwen/claim）

改造后的流程：
- 从 DB 读取所有 `Accounts_Pool(platform='qwen')` 中的账号。
- 对每个账号：
  - 若 `has_claimed_equity_today(account_id)` 为真：
    - 记录状态为 `"already_claimed"`，跳过。
  - 否则调用：

```python
result = await claim_equity_quota(
    account_id=account_id,
    auth_state_path=auth_state_path,
)
```

- 领取前后 `claim_equity_quota` 自身会：
  - 调用 `get_quota_snapshot()` 以获取 `before_snapshot` 和 `after_snapshot`；
  - 调用 `_write_equity_claim_record()` 更新 quota 状态文件；
  - 这些数据被用于下一次 `get_qwen_status()` 和账号排序。

#### 自动领取（scheduler）

定时任务 `_auto_claim_qwen_quota`：
- 每天固定时间（例如 08:05）执行。
- 遍历 DB Qwen 账号池中的所有账号，逻辑同手动领取。
- 不对其它时间段重复抓额度。

### 5. 额度刷新策略

为避免频繁调用 Qwen 接口，本设计遵循以下规则：

- 转写执行时：
  - 不主动调用 `get_quota_snapshot()`。
  - 仅使用当前本地记录的 `remaining_hours`（来源于最近一次领取）进行排序与决策。

- Settings 页打开时：
  - 不主动抓去 Qwen 额度，只读取：
    - DB 中账号池列表（账号基本信息）。
    - quota 状态文件中的每日记录（如 `lastEquityClaimAt`）。
  - 仅展示「剩余小时」的最近快照值。

- 额度刷新点：
  - 手动调用 `/settings/qwen/claim`。
  - scheduler 自动领取。
  - 如未来需要，可增加显式“刷新额度”按钮，用户点击时触发一次 `get_quota_snapshot()`，本设计暂不要求。

## 错误与异常处理

- 如果某个账号在领取额度时失败（网络/认证/接口变更）：
  - 不立即将账号标记为失效，仅记录失败原因。
  - 如错误类型为认证问题，可将账号状态设置为 `invalid` 并在 Settings 列表中强调“失效”，等待用户更新 Cookie。

- 如果 `Accounts_Pool` 中存在账号记录但对应 `auth_state_path` 文件不存在或无效：
  - 在额度查询/执行时，尝试通过 DB 中保存的 Cookie 重建 storageState；
  - 若仍失败，则标记账号为 `invalid` 且跳过执行。

## 对现有逻辑的影响与兼容性

- `accounts.json`：
  - 仍可保留以确保 CLI（qwen-transcribe run/batch）或老版本流程可独立运行。
  - 但在 web 后端的 API 和 Pipeline 流程中，将以 DB 账号池为主，不再依赖 `accounts.json` 作为账号池。

- 默认单账号：
  - 若 `Accounts_Pool` 中没有 Qwen 账号，但仍存在默认 auth_state 文件：
    - 可以兼容一个 “default” 账号，行为与当前单账号模式一致。
  - 一旦用户在 UI 中添加了第一个 Qwen 账号，策略即切换为 DB 账号池模式。

## 测试建议

- 单元测试：
  - `test_get_qwen_status_uses_accounts_pool`: 确认 `/settings/qwen/status` 仅基于 DB 账号池构造账号列表与 remaining_hours。
  - `test_claim_quota_uses_accounts_pool`: 确认 `/settings/qwen/claim` 对每个 DB 账号执行 `claim_equity_quota`，并正确识别今天已领的账号。
  - `test_transcribe_prefers_higher_remaining_hours`: 构造两个账号的额度快照，验证转写时优先选择剩余小时更高的账号。
  - `test_auth_error_marks_account_invalid_and_skips`: 模拟认证失败，验证账号状态转为 invalid 且后续任务不再使用该账号。

- 集成测试：
  - 「添加账号 → 手动领取额度 → 查看 Settings 页额度展示」全链路。
  - 「多个账号剩余小时不同 → 启动批量转写 → 检查使用账号顺序」。
  - 「Cookie 过期 → 显示失效 → 更新 Cookie → 状态恢复」。

