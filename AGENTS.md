# AGENTS.md

本仓库是远盛项目正式 Git 仓库。

## 路径约定

- 仓库根目录：`D:\Tools\work_project\yuansheng-push`
- 远程仓库：`git@github.com:riverben-max/yuansheng.git`
- 默认分支：`main`
- 桌面端 Tauri：`desktop-tauri`
- 桌面端采集核心：`desktop-client`
- 管理后台前端：`RuoYi-Vue3`

## 工作约定

- 修改远盛代码、查看 Git 状态、提交、测试、构建时，以本仓库根目录为准。
- 不要误改外层副本 `D:\Tools\work_project\desktop-tauri` 或 `D:\Tools\work_project\desktop-client`。
- 所有文件使用 UTF-8 无 BOM；包含中文的文件保持 LF 换行。
- 后端由用户在 IntelliJ IDEA 中用 JDK 17 运行；不要自行启动或重启后端服务。
- 桌面端发版（升版本号、打包、生成 update.json、上传服务器）按 [`docs/release-process.md`](docs/release-process.md) 执行。
- 千牛「从浏览器导入 Cookie」的完整性校验、自动跳转 myseller 工作台、dev 模式 sidecar 重启注意事项见 [`docs/qn-cookie-handling.md`](docs/qn-cookie-handling.md)。**不要轻易删 `sidecar_cli.py::grab_browser_cookie` 千牛分支里的逻辑。**

### 「从浏览器导入 Cookie」核心边界（任何后续修改前必读）

桌面端「浏览器」按钮的整套流程依赖下面这些模块和数据结构。**修改时只能往里面增量加平台或字段，不要重命名、删除、合并、或推翻已有逻辑**。除非用户明确要求废弃整个流程，否则保留下面这些不动：

1. **`desktop-client/browser_debug_setup.py`**
   - `PLATFORM_COOKIE_DOMAINS`：四个平台 cookie 域名过滤白名单。新增平台时往这里加。
   - `PLATFORM_LOGIN_URLS`：四个平台登录/工作台 URL。千牛特意用 `myseller.taobao.com/home.htm/QnworkbenchHome/` 而不是 `loginmyseller`，是为了登录后自动落到工作台触发 `_m_h5_tk` 颁发，**不能改回登录页 URL**。
   - `grab_cookies_via_cdp(port, target_domains)`：通过 DrissionPage 连接 360 调试端口，读 cookie store 按域名过滤。这就是「不打开对应平台网页也能拿 cookie」的实现机制——cookie 持久化在 360 profile 里，CDP 直接读取。
   - `open_url_in_existing_browser(port, url)`：用 DrissionPage 在已运行的 360 里 `new_tab(url)`，**不重启浏览器**。用于自动跳工作台/登录页。
   - `detect_browser_debug_status(port)`：检测 360 是否在调试端口模式运行。

2. **`desktop-client/sidecar_cli.py::grab_browser_cookie` 千牛分支**
   - `_qn_cookie_complete(c)`：必须 `_m_h5_tk` + (`unb`/`sn`/`tracknick`/`_nk_` 任一)。`_tb_token_` 是 CSRF token **不算**用户身份。
   - `_log_qn_cookie_fields(c, tag)`：诊断日志，客户反馈问题时第一时间看这条。
   - 不完整时自动跳 myseller 工作台 → `time.sleep(5)` → 重抓 → 仍不完整则返回 `cookieSaved=False, loginPageOpened=True` + 再开一次工作台引导客户登录。

3. **`desktop-client/sidecar_cli.py::relaunch_browser_for_debug`**
   - 杀 360 进程 + 用调试端口重启 + 跳指定 `startupUrl`。**不依赖 360 桌面快捷方式**（解决"客户机器没有 360 快捷方式"的场景）。
   - 接受 `platformLabel` payload，日志和提示文案动态化。

4. **响应字段约定（前端依赖）**
   - `cookieSaved: bool`：cookie 是否保存成功，前端据此显示"导入成功"消息。
   - `loginPageOpened: bool`：cookie 不完整时软件已自动开了登录/工作台页面，前端弹"请登录后再点浏览器"对话框。
   - `needsSetup: bool`：浏览器没启动或没开调试端口，前端弹"重启浏览器"对话框走 `relaunch_browser_for_debug`。
   - `platformLabel: str`：动态平台名，用于前端文案。

5. **识别名生成（`desktop-client/sidecar_cli.py` + `desktop-client/login_accounts.py`）**
   - `_resolve_qn_identity_from_cookie`：千牛 cookie 解析中文昵称，**跳过 `tb<纯数字>` 这种内部 ID**。
   - `_capture_identity_for_account`（`login_accounts.py`）：采集成功后从 payload 算识别名（`loginAccount:subAccount` 形式），**无条件覆盖 `account.loginHint`**——这是用户明确要求的简化逻辑，不要再加 `if loginHint != ...` 之类的保护条件。

6. **dev 模式 sidecar 生效**
   - 改 Python 代码后必须执行 `pwsh -ExecutionPolicy Bypass -File desktop-tauri/scripts/build_sidecar.ps1` 重打 `yuansheng-sidecar.exe`，再彻底重启 dev。理由见 `docs/qn-cookie-handling.md` 第 5 节。

### 不能动的前端 UI 边界

- 用户管理页每行只保留「浏览器」+「采集」两个按钮，顶部保留「新增登录账户」+「删除选中账户」+「采集选中账号」三个按钮。
- 「登录」「编辑」「直采」「导入Cookie」这些按钮和对应 `onStartLogin` / `onCaptureAccountDirect` / `onImportCookie` 已被刻意删除——客户用「浏览器」+「采集」两个按钮就够了，不要加回来。
- 抖店账号的 `usesCookieImportLogin` 旧分支（粘贴 cURL）已废弃。客户嫌复杂回退过的方案不要再加回来。

## 桌面端前端结构约束

- `desktop-tauri/src` 根目录只保留入口级文件，例如 `App.vue`、`main.js`、全局样式和少量启动配置。
- 纯 JS 工具、状态计算、sidecar 通信、轮询策略等放在 `desktop-tauri/src/lib/`，测试文件尽量与对应模块放在同一目录。
- 页面级 Vue 组件后续放在 `desktop-tauri/src/views/`，不要继续把完整页面堆进 `App.vue`。
- 可复用 UI 组件后续放在 `desktop-tauri/src/components/`，例如平台卡片、账号表格、运行日志、设置面板、弹窗。
- 平台差异和平台定义后续放在 `desktop-tauri/src/platforms/`；新增平台不要直接把平台专属判断散落到 `App.vue`。
- 结构整理应分步提交，每一步都要保持 `npm run build` 和对应前端测试可通过。
