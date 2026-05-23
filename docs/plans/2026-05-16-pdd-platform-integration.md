# 拼多多平台接入实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不新增独立页面、不回写 `App.vue` 平台分支的前提下，把拼多多作为 `pdd` 平台接入现有“平台账号 + 登录 Cookie + 采集适配器 + 统一字段上传 + 前端平台卡片/账号矩阵”主链路。

**Architecture:** 前端只通过 `platforms.js` 获得平台列表和展示能力；sidecar 通过平台适配器注册表按账号 `platform` 分发采集；拼多多适配器只在适配器内部处理原始 Cookie、接口、字段名和失败类型，对外返回现有统一上传 payload。

**Tech Stack:** Vue 3、Element Plus、Tauri、Python sidecar、DPAPI Cookie 保护、`httpx`、`node:test`、`unittest`。

---

## 目标边界

本计划的成功标准是新增拼多多平台后，用户可以在现有“数据采集”页看到拼多多卡片，在现有“用户管理”页创建和维护拼多多账号，完成登录、保存 Cookie、按账号采集、统一字段上传，并在失败时只标记对应拼多多账号，不影响千牛和京东账号。

最终目标不是做一个“拼多多页面”，而是把新平台接入方式固定为同一套扩展链路：

```text
platforms.js 平台配置
  -> 用户管理账号矩阵创建平台账号
  -> start_login / poll_login 保存账号级 Cookie
  -> capture_account / capture_all 按 platform 分发
  -> 平台采集适配器输出统一字段
  -> 复用现有上传和账号状态展示
```

新增平台时，只允许增加平台配置、登录态判断、采集适配器和字段映射；不允许新增独立页面，也不允许把平台逻辑塞回 `App.vue`。

本计划不做以下事项：

- 不新增“拼多多页面”。
- 不在 `desktop-tauri/src/App.vue` 里写 `if platform === "pdd"`。
- 不把拼多多原始字段泄漏到前端通用展示层或上传主字段之外。
- 不同时接抖店、抖音、快手等其他平台。
- 不做表格虚拟化、自动更新、数据迁移或后端指标扩字段。
- 不保存明文 Cookie，不输出 Cookie 值到日志。

## 项目结构理解

当前项目已经基本拆出了多平台主干，后续实现要顺着这个结构扩展：

| 模块 | 现有文件 | 责任 | 拼多多接入方式 |
| --- | --- | --- | --- |
| 桌面端总入口 | `desktop-tauri/src/App.vue` | 组合页面、调度通用状态 | 不写 `pdd` 判断，不承载平台业务逻辑 |
| 平台配置 | `desktop-tauri/src/lib/platforms.js` | 前端平台列表、标签、采集能力 | 增加 `pdd` 配置项 |
| 平台卡片汇总 | `desktop-tauri/src/lib/platformOverview.js`、`PlatformCards.vue` | 按平台统计账号和采集状态 | 自动从 `PLATFORMS` 派生拼多多卡片 |
| 账号矩阵 | `desktop-tauri/src/lib/accountMatrix.js`、`AccountTable.vue`、`AccountDialog.vue` | 账号筛选、创建、编辑、操作 | 自动从 `PLATFORMS` 派生拼多多选项 |
| sidecar 命令入口 | `desktop-client/sidecar_cli.py` | `start_login`、`poll_login`、`capture_all`、`capture_account` | 复用命令，不新增平台命令 |
| 平台 URL 和登录判断 | `desktop-client/platform_config.py` | 平台归一化、登录入口、登录成功判断 | 增加拼多多 URL 和登录态判断 |
| 账号与批量采集 | `desktop-client/login_accounts.py` | 账号模型、状态、批量采集结果 | 只接平台适配器注册表，不写 `elif pdd` |
| 京东参考适配器 | `desktop-client/jd_workload_capture.py` | 京东 Cookie、请求、字段映射 | 参考结构新增拼多多适配器 |
| 拼多多适配器 | `desktop-client/pdd_workload_capture.py` | 拼多多 Cookie、请求、字段映射 | 新增文件，平台私有逻辑只放这里 |

## 总体实施规划

建议拆成三个 PR，每个 PR 都有可独立验收的闭环。

### PR 1: `feat: add platform adapter foundation`

目标：先把“新增平台怎么接”固定下来，不接真实拼多多接口。

步骤：

1. 统一前后端平台配置入口。
2. 抽出 sidecar 平台采集适配器注册表。
3. 统一适配器输出字段和失败状态。

验收：

- `capture_all` 和 `capture_account` 不关心具体平台。
- 账号层只按 `platform` 找适配器。
- 以后新增平台不需要改 `App.vue`，也不需要在 `login_accounts.py` 继续追加平台分支。
- 千牛、京东现有流程不回退。

### PR 2: `feat: add pdd login and account support`

目标：让系统认识拼多多账号，并打通登录 Cookie 保存，但不急着采真实数据。

步骤：

1. 前后端加入 `pdd` 平台值。
2. 用户管理页能创建、筛选、编辑拼多多账号。
3. 数据采集页自动出现拼多多平台卡片。
4. 实测拼多多登录入口和登录成功判断。
5. 复用 `start_login` / `poll_login` 保存拼多多账号级 Cookie。

验收：

- 拼多多账号能在现有账号矩阵里创建。
- 拼多多平台卡片来自 `platforms.js`，不是新页面。
- 登录成功后 Cookie 状态为“已保存”。
- 普通用户 Chrome 不被关闭。
- 日志不输出 Cookie 值。

### PR 3: `feat: add pdd capture adapter`

目标：拼多多完成真实采集、统一字段映射和上传闭环。

步骤：

1. 实测拼多多数据页面、接口、参数、响应结构和字段语义。
2. 新增 `pdd_workload_capture.py`。
3. 写拼多多适配器单元测试。
4. 实现 Cookie 解密、Cookie 压缩、接口请求、错误分类、字段映射。
5. 把 `pdd` 注册到平台适配器注册表。
6. 做千牛、京东、拼多多混合账号批量采集验收。

验收：

- 拼多多适配器输出现有统一上传 payload。
- 字段语义不确定时主字段保持空值，原始数据只进 `rawMetrics`。
- 拼多多失败只标记拼多多账号，不影响千牛和京东。
- 上传失败不覆盖本地采集结果，但账号状态明确提示上传失败原因。

## 当前可复用主干

- 前端平台配置：`desktop-tauri/src/lib/platforms.js`
- 前端平台汇总：`desktop-tauri/src/lib/platformOverview.js`
- 前端账号矩阵：`desktop-tauri/src/lib/accountMatrix.js`
- 前端展示组件：`PlatformCards.vue`、`AccountTable.vue`、`AccountDialog.vue`
- sidecar 登录入口：`desktop-client/sidecar_cli.py` 的 `start_login`、`poll_login`
- sidecar 采集入口：`desktop-client/sidecar_cli.py` 的 `capture_all`、`capture_account`
- 账号状态与批量采集：`desktop-client/login_accounts.py`
- 京东参考适配器：`desktop-client/jd_workload_capture.py`
- 京东参考计划：`docs/plans/2026-05-11-jd-platform-integration.md`

## 前置条件

拼多多 PR 应建立在 `feat: add platform adapter foundation` 之后。如果当前分支仍然在 `login_accounts.py` 里直接写 `platform == "jd"` 的采集分支，不要在同一位置追加 `elif platform == "pdd"`；应先完成或合入平台适配器基础 PR，把平台分发抽成注册表。

基础 PR 至少应具备：

- 一个 sidecar 平台适配器接口，例如 `capture(state, log) -> payload`。
- 一个注册表，例如 `{"qn": qn_adapter, "jd": jd_adapter}`。
- 统一失败类型口径：登录失效、身份缺失、接口失败、字段缺失、上传失败。
- 统一字段校验：所有平台适配器对外返回同一组上传字段。
- 前端只读取 `platforms.js`，不在页面组件内写平台特殊判断。

## 统一上传字段

拼多多适配器对外返回字段必须与现有主干一致：

| 字段 | 口径 |
| --- | --- |
| `loginAccount` | 店铺或平台账号展示名，优先使用账号配置里的店铺名 |
| `recordDate` | 数据日期，默认采集本机日期的前一天 |
| `subAccount` | 客服子账号或平台返回的接待账号 |
| `consultationCount` | 咨询人数或语义完全一致的咨询量 |
| `receiveCount` | 接待人数 |
| `validReceiveCount` | 有效接待人数，拼多多无明确对应时为 `None` |
| `inquiryCount` | 询单人数，拼多多无明确对应时为 `None` |
| `conversionRate` | 转化率，拼多多无明确对应时为 `None` |
| `firstReplyTime` | 首响时长 |
| `avgReplyTime` | 平均时长，必须确认语义后再映射 |
| `wwReplyRate` | 回复率；如果拼多多有 3 分钟或 30 秒回复率，只在语义确认后映射 |
| `satisfaction` | 满意度 |
| `rawMetrics` | 拼多多原始响应、请求参数、字段映射依据和诊断信息 |

字段处理原则：

- 能确认同义的字段直接映射。
- 语义相近但不一致的字段不硬凑，主字段保持 `None`，原始值进入 `rawMetrics`。
- 拼多多新增指标不扩上传主字段，除非后续单独开后端和前端字段扩展 PR。
- `rawMetrics` 不能包含 Cookie、Token、手机号、身份证、明文账号密码等敏感值。

## 实施任务

### Task 1: 确认基础适配器 PR 状态

**Files:**

- Read: `desktop-client/login_accounts.py`
- Read: `desktop-client/sidecar_cli.py`
- Read: `desktop-client/jd_workload_capture.py`
- Read: `desktop-tauri/src/lib/platforms.js`

- [ ] **Step 1: 检查 sidecar 是否已有平台适配器注册表**

  预期结果：采集分发不再依赖在 `capture_enabled_accounts` 内为每个平台写分支。若仍只有京东特判，本 PR 暂停，先执行 `feat: add platform adapter foundation`。

- [ ] **Step 2: 检查统一失败类型是否已经落地**

  预期结果：适配器可以表达登录失效、身份缺失、接口失败、字段缺失；账号层能把这些失败落到 `loginStatus`、`lastFailureReason`、`lastError`、`lastCaptureSummary`。

- [ ] **Step 3: 检查前端是否仍只从 `platforms.js` 读取平台列表**

  预期结果：平台卡片、账号弹窗、账号表筛选都由 `PLATFORMS` 派生，不需要在组件里新增拼多多判断。

### Task 2: 增加拼多多平台配置

**Files:**

- Modify: `desktop-tauri/src/lib/platforms.js`
- Modify: `desktop-tauri/src/lib/platforms.test.js`
- Modify: `desktop-tauri/src/lib/accountMatrix.test.js`
- Modify: `desktop-tauri/src/lib/platformOverview.test.js`
- Modify: `desktop-client/platform_config.py`
- Modify: `desktop-client/tests/test_platform_config.py`
- Modify: `desktop-client/login_accounts.py`
- Modify: `desktop-client/tests/test_login_account_capture.py`

- [ ] **Step 1: 前端平台列表加入 `pdd`**

  增加平台项：

  ```js
  { value: "pdd", label: "拼多多", tagType: "warning", supportsCapture: true }
  ```

  验收：`platformList()` 返回千牛、京东、拼多多；`platformFilterOptions()` 返回全部、千牛、京东、拼多多；未知平台仍默认归一到 `qn`。

- [ ] **Step 2: sidecar 平台归一化加入 `pdd`**

  `platform_config.normalize_platform()` 和账号模型有效平台集合加入 `pdd`。旧账号、非法平台仍归一为 `qn`。

- [ ] **Step 3: 拼多多登录入口先使用实测确认值**

  不凭印象落代码。实现前先用临时影子浏览器确认拼多多商家/客服后台登录入口、登录成功后的 host 和客服数据入口；确认后再把常量写入 `platform_config.py`。

  目标常量命名固定为 `PDD_LOGIN_URL`、`PDD_SERVICE_URL`、`PDD_DATA_URL`。本任务不接受临时字符串；只有在 Task 5 记录了实测 URL 后，才把真实 URL 写入这些常量，并在 `test_platform_config.py` 里固定断言。

- [ ] **Step 4: 测试平台配置**

  Run:

  ```powershell
  python -m unittest desktop-client/tests/test_platform_config.py desktop-client/tests/test_login_account_capture.py
  ```

  Expected: `pdd` 可以被归一化、创建、编辑、进入登录入口；千牛和京东断言保持通过。

### Task 3: 打通拼多多登录与 Cookie 保存

**Files:**

- Modify: `desktop-client/platform_config.py`
- Modify: `desktop-client/sidecar_cli.py`
- Modify: `desktop-client/tests/test_platform_config.py`
- Modify: `desktop-client/tests/test_sidecar_cli.py`
- Modify: `desktop-client/tests/test_external_capture.py`

- [ ] **Step 1: 增加拼多多登录相关页面判断**

  增加类似京东的函数，但命名使用拼多多：`is_pdd_login_page(page_url)`、`is_pdd_login_success_page(page_url)`、`is_pdd_relevant_page(page_url)`。

  判断规则只基于实测 host 和路径，不复用千牛 `_m_h5_tk` 或京东 `pin/thor`。

- [ ] **Step 2: 增加拼多多登录成功 Cookie 口径**

  先用实测登录后的 Cookie 名称集合建立最小判断规则。规则必须满足：

  - 未登录页 Cookie 不会误判为已登录。
  - 登录成功页 Cookie 能稳定命中。
  - 日志只输出 URL、Cookie 名称、数量和布尔标记，不输出 Cookie 值。
  - 若拼多多登录需要短信、扫码或验证码，主窗口保持非阻塞，只显示等待或失败状态。

- [ ] **Step 3: 登录成功后沿用现有 DPAPI 保存逻辑**

  登录成功后继续写入账号级 `cookieProtected`、`cookieUpdatedAt`、`cookieSummary`、`lastKnownLoginAccount`、`loginStatus="已登录"`，并关闭本软件创建的临时登录 Chrome。

- [ ] **Step 4: 登录状态测试**

  测试用例覆盖：

  - 未登录拼多多页面不会保存 Cookie。
  - 登录成功页面加实测 Cookie 名称会保存 Cookie。
  - 拼多多 Cookie 诊断不包含 Cookie 值。
  - 千牛和京东登录状态判断不变。

### Task 4: 建立拼多多采集适配器骨架

**Files:**

- Create: `desktop-client/pdd_workload_capture.py`
- Create: `desktop-client/tests/test_pdd_workload_capture.py`
- Modify: platform adapter registry file from foundation PR
- Modify: `desktop-client/tests/test_login_account_capture.py`

- [ ] **Step 1: 定义拼多多适配器异常类型**

  异常命名建议：

  ```python
  class PddWorkloadCaptureError(DirectApiCaptureError):
      pass

  class PddWorkloadLoginRequiredError(DirectApiLoginRequiredError):
      pass

  class PddWorkloadIdentityRequiredError(PddWorkloadCaptureError):
      pass
  ```

- [ ] **Step 2: 定义适配器入口函数**

  入口函数签名保持可测试：

  ```python
  def capture_pdd_workload(
      state: Mapping[str, Any],
      log: Callable[[str], None],
      client: Any = None,
      today: date | None = None,
  ) -> Dict[str, Any]:
      raise PddWorkloadCaptureError("拼多多采集适配器尚未完成字段实测。")
  ```

- [ ] **Step 3: 定义内部函数边界**

  建议函数边界：`resolve_pdd_operator_identity` 负责客服身份，`build_pdd_workload_request_params` 负责日期和查询参数，`normalize_pdd_cookie_header` 负责 Cookie 压缩，`fetch_pdd_workload_data` 负责 HTTP 请求，`parse_pdd_workload_payload` 负责统一字段映射。

  这些函数先用测试驱动，不在 `sidecar_cli.py` 里直接写解析逻辑。

- [ ] **Step 4: 建立空 Cookie、解密失败、登录失效测试**

  测试口径：

  - 没有 `cookieProtected` 抛 `PddWorkloadLoginRequiredError`。
  - DPAPI 解密失败抛 `PddWorkloadLoginRequiredError`。
  - HTTP 401/403 或平台返回未登录码抛 `PddWorkloadLoginRequiredError`。
  - 身份缺失抛 `PddWorkloadIdentityRequiredError`，账号状态应是“采集失败”而不是“需要重新登录”。

### Task 5: 实测拼多多数据接口和字段

**Files:**

- Create: `docs/plans/2026-05-16-pdd-capture-observations.md`
- Modify: `desktop-client/tests/test_pdd_workload_capture.py`

- [ ] **Step 1: 用临时登录窗口完成拼多多登录**

  只使用本软件启动的影子 Chrome，不关闭普通用户 Chrome。登录遇到扫码、短信、验证码时，由用户手动完成。

- [ ] **Step 2: 记录登录成功判断依据**

  在观察文档记录：

  - 登录入口 URL。
  - 登录成功页面 URL。
  - 未登录 Cookie 名称集合。
  - 登录成功 Cookie 名称集合。
  - 能证明登录态有效的最小 Cookie 名称集合。

  不记录 Cookie 值。

- [ ] **Step 3: 记录客服数据接口**

  在观察文档记录：

  - 数据页面 URL。
  - 真实请求 URL、方法、必要 query/body 参数。
  - 必要请求头名称，不记录敏感值。
  - 日期参数口径，默认按“昨天”采集。
  - 返回根节点结构、成功码、未登录码、空数据结构。

- [ ] **Step 4: 记录字段映射依据**

  对每个统一字段给出“拼多多字段名 + 页面含义 + 是否映射”的结论。无法确认语义时写入 `rawMetrics`，主字段为 `None`。

- [ ] **Step 5: 提取脱敏测试样本**

  从实测响应提取最小脱敏样本，写入 `test_pdd_workload_capture.py` 的 `SAMPLE_RESPONSE`。样本必须去除 Cookie、Token、手机号、真实订单号、真实买家信息。

### Task 6: 实现拼多多字段解析和请求

**Files:**

- Modify: `desktop-client/pdd_workload_capture.py`
- Modify: `desktop-client/tests/test_pdd_workload_capture.py`

- [ ] **Step 1: 写请求参数测试**

  参照京东测试，固定 `today=date(2026, 5, 13)` 时采集 `2026-05-12`。

- [ ] **Step 2: 写字段解析测试**

  测试必须断言：

  - `loginAccount` 优先来自账号 `shopName`。
  - `recordDate` 来自平台返回日期或请求日期。
  - `subAccount` 来自拼多多客服账号字段；缺失时回退到登录识别名。
  - 每个已确认字段正确转换为统一字段。
  - 未确认字段保持 `None`。
  - 原始响应进入 `rawMetrics`，但不包含敏感值。

- [ ] **Step 3: 实现 Cookie 压缩**

  只保留拼多多接口必需 Cookie 名称。缺少登录必需 Cookie 时抛 `PddWorkloadLoginRequiredError`。日志只输出压缩前后数量和长度，不输出值。

- [ ] **Step 4: 实现 HTTP 请求和错误分类**

  错误分类：

  - 网络异常：`PddWorkloadCaptureError`
  - 401/403：`PddWorkloadLoginRequiredError`
  - 平台未登录码：`PddWorkloadLoginRequiredError`
  - 平台业务失败码：`PddWorkloadCaptureError`
  - 空数据：`PddWorkloadCaptureError`

- [ ] **Step 5: 运行适配器测试**

  Run:

  ```powershell
  python -m unittest desktop-client/tests/test_pdd_workload_capture.py
  ```

  Expected: 拼多多适配器单元测试全部通过。

### Task 7: 接入平台采集注册表

**Files:**

- Modify: platform adapter registry file from foundation PR
- Modify: `desktop-client/login_accounts.py`
- Modify: `desktop-client/sidecar_cli.py`
- Modify: `desktop-client/tests/test_login_account_capture.py`
- Modify: `desktop-client/tests/test_sidecar_cli.py`

- [ ] **Step 1: 注册 `pdd` 适配器**

  在平台适配器注册表加入 `pdd -> capture_pdd_workload`。账号层只按 `platform` 查注册表，不直接 import 后写平台分支。

- [ ] **Step 2: 批量采集测试增加千牛、京东、拼多多混合账号**

  断言采集顺序和上传结果：

  - `qn` 走千牛适配器。
  - `jd` 走京东适配器。
  - `pdd` 走拼多多适配器。
  - 任一平台失败不影响其他平台。

- [ ] **Step 3: 拼多多失败状态测试**

  断言：

  - 登录失效：账号 `loginStatus="需要重新登录"`，`lastFailureReason="需要重新登录"`。
  - 接口失败：账号 `loginStatus="采集失败"`，`lastFailureReason="接口失败"` 或“采集失败”。
  - 上传失败：采集结果 `ok=True`，`lastCaptureSummary.uploaded=False`，账号 `lastFailureReason="上传失败"` 或“平台未配置客服账号”。

- [ ] **Step 4: 运行账号采集测试**

  Run:

  ```powershell
  python -m unittest desktop-client/tests/test_login_account_capture.py desktop-client/tests/test_sidecar_cli.py
  ```

  Expected: 千牛、京东、拼多多混合采集测试通过。

### Task 8: 前端平台卡片和账号矩阵验收

**Files:**

- Modify: `desktop-tauri/src/lib/platforms.test.js`
- Modify: `desktop-tauri/src/lib/platformOverview.test.js`
- Modify: `desktop-tauri/src/lib/accountMatrix.test.js`
- Read: `desktop-tauri/src/components/PlatformCards.vue`
- Read: `desktop-tauri/src/components/AccountTable.vue`
- Read: `desktop-tauri/src/components/AccountDialog.vue`

- [ ] **Step 1: 更新平台列表测试**

  断言 `PLATFORMS.map((p) => p.value)` 为 `["qn", "jd", "pdd"]`。

- [ ] **Step 2: 更新平台汇总测试**

  构造拼多多账号，断言平台卡片摘要包含拼多多启用账号数、已登录账号数、最近采集结果。

- [ ] **Step 3: 更新账号矩阵测试**

  断言平台筛选包含拼多多；新增账号时如果当前筛选是拼多多，默认平台为 `pdd`。

- [ ] **Step 4: 检查组件无平台硬编码**

  `PlatformCards.vue`、`AccountTable.vue`、`AccountDialog.vue` 不应出现 `platform === "pdd"`。如果必须区分能力，放回 `platforms.js` 配置字段或通用 helper。

- [ ] **Step 5: 运行前端单元测试**

  Run:

  ```powershell
  npm test -- --runInBand
  ```

  如果当前项目没有该脚本，改用现有 `package.json` 中定义的测试命令。

  Expected: 平台配置、平台汇总、账号矩阵测试通过。

### Task 9: 手动端到端验收

**Files:**

- Read: `desktop-tauri/src/lib/sidecar.js`
- Read: `desktop-client/sidecar_cli.py`
- Read: `desktop-client/upload_client.py`

- [ ] **Step 1: 创建拼多多账号**

  在“用户管理”页创建 `platform=pdd` 账号，填写店铺名和登录识别名。账号出现在拼多多筛选结果中，平台列显示“拼多多”。

- [ ] **Step 2: 登录并保存 Cookie**

  点击账号“登录”，临时 Chrome 打开拼多多登录页。用户完成登录后，账号状态变为“已登录”，Cookie 状态为“已保存”。普通用户 Chrome 不被关闭。

- [ ] **Step 3: 单账号采集**

  点击该拼多多账号“采集”。预期：调用拼多多适配器，返回统一 payload，上传成功或明确显示上传失败原因。

- [ ] **Step 4: 平台卡片采集**

  在“数据采集”页点击拼多多平台卡片采集启用账号。预期：只采集拼多多启用账号，卡片最近结果更新。

- [ ] **Step 5: 全部采集**

  同时保留千牛、京东、拼多多账号，执行全部采集。预期：三个平台按账号分发，某个平台失败不影响其他平台账号状态。

- [ ] **Step 6: 后端联调边界**

  如果上传接口需要后端配合，由用户在 IntelliJ IDEA 中用 JDK 17 重启后端。Codex 不启动或重启后端服务。

### Task 10: 收尾检查

**Files:**

- Read: `desktop-tauri/src/App.vue`
- Read: `desktop-tauri/src/lib/platforms.js`
- Read: `desktop-client/login_accounts.py`
- Read: platform adapter registry file from foundation PR
- Read: `desktop-client/pdd_workload_capture.py`

- [ ] **Step 1: 搜索禁止模式**

  检查：

  - `App.vue` 不包含 `pdd`。
  - 前端组件不包含 `platform === "pdd"`。
  - `login_accounts.py` 不新增拼多多专用分支。
  - 日志不输出 Cookie 值。

- [ ] **Step 2: 运行后端 sidecar 测试**

  Run:

  ```powershell
  python -m unittest discover desktop-client/tests
  ```

  Expected: sidecar 测试通过。

- [ ] **Step 3: 运行前端测试**

  Run:

  ```powershell
  npm test
  ```

  Expected: 前端测试通过。

- [ ] **Step 4: 记录 PR 说明**

  PR 标题：

  ```text
  feat: add pdd capture adapter
  ```

  PR 说明必须包含：

  - 平台值：`pdd`
  - 登录成功 Cookie 判断依据
  - 拼多多字段映射表
  - 未映射字段说明
  - 手动验收结果
  - 已确认未新增页面、未修改 `App.vue` 平台分支

## 风险与处理

- 拼多多登录可能有短信、扫码、验证码或风控：保持登录流程非阻塞，失败只落账号状态。
- 拼多多数据接口可能随页面版本变化：适配器测试必须使用脱敏样本固定解析口径，接口失败要有明确日志。
- 拼多多字段语义可能和现有统一字段不完全一致：不强行映射，保留 `None` 和 `rawMetrics`。
- 如果后端必须新增平台字段或指标字段：单独开后端 PR，由用户在 IDEA 中重启后端验证。
- 如果拼多多需要店铺维度或客服账号二次选择：先把选择参数放在账号配置或适配器内部，不新增独立页面。

## 推荐执行顺序

1. 先确认或合入 `feat: add platform adapter foundation`。
2. 再执行本计划的 Task 2 到 Task 4，先让拼多多能创建账号、登录、保存 Cookie、进入适配器。
3. 现场实测 Task 5，拿到真实接口和字段。
4. 完成 Task 6 到 Task 8，把采集、上传、前端展示闭环。
5. 完成 Task 9 到 Task 10，做端到端验收和 PR 收尾。
