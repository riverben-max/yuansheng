# 京东平台接入实施计划

## 目标

在不破坏千牛已跑通链路的前提下，把桌面端扩展为多平台账号和统一字段采集，京东作为第一个新增平台接入。

## 京东已确认入口

- 登录页：`https://passport.jd.com/new/login.aspx?ReturnUrl=http%3A%2F%2Fkf.jd.com%2F`
- 登录后客服入口：`http://kf.jd.com/`
- 客服数据页：`https://kf.jd.com/#/43`

## 京东登录态观测

- 未登录停留在 `passport.jd.com` 时，常见 Cookie 名称包括 `__jda`、`__jdb`、`__jdc`、`__jdu`、`__jdv`、`QRCodeKey`、`NID`、`JSESSIONID`、`guid`、`wlfstk_smdl` 等；这些不能作为已登录依据。
- 手动登录成功后会进入 `kf.jd.com`，实测成功页可为 `https://kf.jd.com/#/218`，不应限定为 `/` 或 `#/43`。
- 京东登录成功后实测 Cookie 名称包含 `pin`、`thor`、`ceshi3.com`、`_pst`、`_tp`、`unick` 等。
- 本阶段京东登录成功判断口径：当前 URL host 为 `kf.jd.com`，且 Cookie 同时包含 `pin` 和 `thor`。
- 实测登录成功时未出现 `pt_pin`，因此第五步不把 `pt_pin` 作为必需字段。
- 诊断日志只能输出 URL、Cookie 名称列表、数量和布尔标记，不输出 Cookie 值。

## 存放原则

这个文件记录阶段性实施步骤。`AGENTS.md` 只保留长期有效规则，不记录每一步实现计划。

## 实施步骤

### 1. 账号模型增加平台字段

- 给登录账号增加 `platform` 字段，老千牛账号默认补为 `qn`。
- 京东账号使用 `platform=jd`。
- 账号数据保留店铺名、登录账号、子账号识别名、Cookie 状态、最近登录、最近采集和最近结果。
- 验收：原千牛账号仍可显示、登录、采集；新增账号可选择京东。

### 2. 用户管理页升级为多平台账号矩阵

- 顶部增加平台筛选：全部、千牛、京东。
- 表格字段调整为：平台、店铺、登录账号、子账号、启用、Cookie状态、最近登录、最近采集、最近结果、操作。
- 操作保持账号维度：登录、采集、编辑、删除。
- 验收：千牛账号展示不回退；京东账号可新增、编辑、删除，并可按平台筛选。

### 3. 数据采集页增加平台卡片总览

- 保留数据采集页，不新增京东独立页。
- 增加平台卡片：千牛、京东。
- 卡片展示启用账号数、已登录账号数、最近采集状态和主要操作按钮。
- 验收：页面能同时看出千牛和京东状态；京东状态异常不影响千牛卡片。

### 4. 采集命令增加平台分发底座

- 继续复用 `capture_account` / `capture_all`。
- `platform=qn` 走现有千牛采集器。
- `platform=jd` 暂不采集，只返回“京东采集暂未接入”，防止误走千牛链路。
- 验收：单独采集千牛正常；单独采集京东不会进入千牛采集；全部采集时千牛和京东结果互不影响。

### 5. 京东登录链路打通，只保存 Cookie

- 继续复用 `start_login` / `poll_login` 的非阻塞流程。
- `platform=jd` 时打开已确认京东登录页，由用户手动登录。
- 京东 Cookie 检测规则独立实现，不套用千牛 `_m_h5_tk` 规则；当前以 `kf.jd.com` + `pin` + `thor` 为保存条件。
- 登录成功后只加密保存 Cookie，关闭临时登录窗口，刷新账号状态。
- 本步不做京东数据采集，京东采集仍保持“京东采集暂未接入”。
- 验收：京东登录不阻塞主窗口；Cookie 能保存；千牛登录不受影响。

### 6. 京东采集适配器映射统一字段

- 京东工作量页面路由是 `https://kf.jd.com/#/43`，真实数据接口为 `GET https://kf.jd.com/waiterPerson/workload/queryList`。
- 京东采集适配器负责使用已保存的 DPAPI Cookie 调用工作量接口获取数据。
- 默认采集本机日期“昨天”的数据，符合页面 `整体数据即T+1数据` 提示。
- 请求参数固定为：`page=1`、`pageSize=15`、`startTime=昨天`、`endTime=昨天`、`transferType=1`、`type=1`、`servicePin=京东客服账号`。
- `servicePin` 来源优先级：`lastKnownLoginAccount` > `loginHint`；缺失时采集失败，提示先登录或补登录识别名。
- 适配器内部把京东原始字段映射为当前已存在的上传 payload 字段，不新增上传字段，不修改后端接口。
- 当前上传字段保持：`loginAccount`、`recordDate`、`subAccount`、`consultationCount`、`receiveCount`、`validReceiveCount`、`inquiryCount`、`conversionRate`、`firstReplyTime`、`avgReplyTime`、`wwReplyRate`、`satisfaction`、`rawMetrics`。
- 能映射的字段直接填值，京东页面没有对应含义的字段保持空值；京东额外字段只保存在 `rawMetrics` 中用于排查和后续扩展。
- 接口响应使用 `workKpiList[0]` 作为单日明细主数据；`totalDetail`、`AvgDetail` 只进入 `rawMetrics` 备查，不参与上传主字段。
- Cookie 为空、解密失败、HTTP 401/403 视为需要重新登录；接口 `code != success` 或 `workKpiList` 为空视为采集失败。
- 验收：京东 payload 字段结构和千牛现有上传结构一致；缺字段保持空值，不为了凑数误映射。

#### 第 6 步字段映射口径

| 当前上传字段 | 京东接口字段或来源 | 处理口径 |
| --- | --- | --- |
| `loginAccount` | 账号配置或识别身份 | 优先 `shopName`，否则 `lastKnownLoginAccount` |
| `recordDate` | `dayStr` | 直接映射 |
| `subAccount` | `waiter` / `servicePin` | 优先 `waiter`，否则 `servicePin` |
| `consultationCount` | `consultNum` | 直接映射 |
| `receiveCount` | `servicedNum` / `receiveNum` | 优先 `servicedNum`，缺失时 fallback 到 `receiveNum` |
| `validReceiveCount` | 无明确对应 | 保持空值 |
| `inquiryCount` | 无明确对应 | 保持空值 |
| `conversionRate` | 无明确对应 | 保持空值 |
| `firstReplyTime` | `responseAvgSpeed` | 直接映射 |
| `avgReplyTime` | `responseAvgDurationWithLeave` | 直接映射；不要映射为 `sessionAvgDuration` |
| `wwReplyRate` | `responseRate` | 直接映射 |
| `satisfaction` | `satisfiedRate` | 直接映射 |
| `rawMetrics` | 京东原始响应 | 保存 `source=jd_workload`、请求参数、`rowData`、`totalDetail`、`AvgDetail` |

京东额外字段如 `onlineTime`、`serviceTime`、`receiveNum30Rate`、`waiterPhaseNoMore180sResponseRate`、`sessionAvgDuration`、`solvedRate`、`inviteEvaluationRate`、`secondConsultNum`、`imSecondConsultNum`、`tbSecondConsultNum`、`notSelfResolveRate`、`sessionAvgSend`、留言相关字段等只进 `rawMetrics`，不新增上传字段。

### 7. 上传和批量验收

- 上传 payload 先不新增字段，保持当前后端接口兼容；如后续必须区分平台，再单独进入第 7 步评估。
- 服务端如后续需要扩展平台字段或新增指标字段，由用户在 IDEA 中重启后端验证。
- 验收：京东数据能上传；千牛数据仍能上传；全部采集结果能按账号显示成功或失败。

## 风险点

- 京东登录态 Cookie 判断需要单独确认，不能套千牛规则。
- 京东页面字段名和接口返回可能与统一字段不同，只能在适配器内部转换。
- 当前阶段不改上传字段，京东缺失指标保持空值；不要把“平均会话时长”等相近但含义不同的字段误映射到现有字段。
- 如果服务端后续需要区分平台或支持京东新增指标，需要同步扩展平台字段和新增指标字段。
- 验证码、人机校验等登录问题不能阻塞主窗口，只能反映为账号状态。
