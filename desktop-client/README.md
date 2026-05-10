# 远盛数据助手桌面端

## 启动

```bash
python main.py
```

## 依赖

```bash
python -m pip install -r requirements.txt
```

## 打包 EXE

先安装打包依赖：

```bash
python -m pip install -r requirements-build.txt
```

然后执行：

```powershell
pwsh ./build_exe.ps1
```

默认会产出到：

```text
desktop-client/dist/远盛数据助手
```

说明：

- 采用 `PyInstaller` 的 `onedir` 方式打包，便于携带 Qt WebEngine 运行库。
- EXE 图标和窗口图标复用 `RuoYi-Vue3/src/assets/logo/logo1.png` 转出的品牌图标。
- Windows 文件版本信息由 `version_info.txt` 注入，可按发版批次继续调整。
- 运行后本地状态写入 `data/` 目录。

## 当前采集口径

- 本轮只采集 **当前登录千牛客服员工本人** 的绩效数据。
- 不再依赖店铺映射，不再读取 `shop_mapping.json`。
- 不再调用旧的店铺口径 `/spider/upload` 接口。
- 默认使用 `data/direct_api_capture.json` 的 F12 接口直采；Cookie 有效时不需要启动浏览器。
- 接口失败时不再回落到表格采集；Cookie 过期时仅打开 **外置影子 Chrome** 用于重新登录刷新 Cookie。
- 影子浏览器由主程序自动托管，默认调试端口为 `9222`。
- 登录账号优先从千牛登录态识别，例如 `远盛电商:林志玲` 会按 `林志玲` 匹配表格行。
- 主流程会在页面内分两轮切换指标复选框，再直接读取表格数据并合并。
- 内置浏览器相关代码仅保留为过渡兼容，不作为生产采集入口。

## 当前采集字段

- `loginAccount`
- `recordDate`
- `subAccount`
- `consultationCount`
- `receiveCount`
- `validReceiveCount`
- `inquiryCount`
- `conversionRate`
- `firstReplyTime`
- `avgReplyTime`
- `wwReplyRate`
- `satisfaction`
- `rawMetrics`

## 当前运行方式

- Cookie 有效时可直接点击“立即采集”，不需要先打开影子浏览器。
- 只有 Cookie 失效时，才点击“重新登录”打开影子浏览器刷新 Cookie。
- 后续按每日时间自动采集，也支持手动点“立即采集”。
- 主窗口关闭只缩到托盘，只有托盘菜单里的“退出程序”会真正退出并关闭影子 Chrome。
- 支持当前用户登录后自启，写入 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`，不需要管理员权限。
- 当前阶段以 **本地日志和主界面结果展示** 为准，不要求立即入库。

## F12 接口直采配置

接口直采只需要手动准备一次配置：

1. 打开千牛并进入客服绩效排名页面。
2. 按 F12 打开 Network 面板。
3. 点击页面查询按钮。
4. 找到返回客服数据的请求，复制完整 Request URL、Request Headers 里的 Cookie、请求方式和 Payload。
5. 在 `desktop-client/data/direct_api_capture.json` 创建本地配置文件。

配置示例：

```json
{
  "enabled": true,
  "method": "GET",
  "apiUrl": "https://xxxxx.taobao.com/api/xxxx",
  "cookie": "your_cookie_here",
  "referer": "https://myseller.taobao.com/home.htm/op-sycm-svc/overview",
  "params": {
    "startDate": "2026-04-01",
    "endDate": "2026-04-25"
  },
  "body": {},
  "loginAccount": "远盛电商",
  "subAccount": "林志玲"
}
```

填写规则：

- `method` 只能填 `GET` 或 `POST`。
- GET 请求把 F12 里的查询参数放到 `params`。
- POST 请求优先把 F12 Payload 放到 `body`；如果只填 `params`，程序会按 JSON body 发送。
- `loginAccount` 填主账号或完整账号，例如 `远盛电商` / `远盛电商:林志玲`。
- `subAccount` 填当前客服员工名，用于从多行客服数据里锁定当前员工。
- Cookie 过期时日志会提示“Cookie 已过期或无权限”，重新登录千牛后复制新的 Cookie 覆盖即可。
- 真实 Cookie 只放在 `data/direct_api_capture.json`，不要写进代码或 README。

## 采集引擎配置

- `data/app_state.json` 里的 `captureEngine` 默认为 `external`。
- `data/app_state.json` 里的 `directApiPreferred=true` 时，自动采集优先走接口直采。
- `shadowChromeProfileDir` 默认位于 `%LOCALAPPDATA%\YuanshengDataAssistant\shadow-chrome`。
- `shadowChromeAutoLaunch=true` 时，主程序启动会自动拉起或接管影子 Chrome。
- `autoStartEnabled=true` 时，启用 Windows 当前用户登录后自启。
- 运行状态文件和日志写入 `data/` 目录，打包产物写入 `build/`、`dist/`，这些目录不提交到 Git。
