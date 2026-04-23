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
- 默认使用 **外置影子 Chrome** 作为采集主流程，接管本地已登录态。
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

- 首次点击“打开影子浏览器登录”会把影子 Chrome 移回屏幕内，员工扫码登录一次即可长期复用。
- 登录成功后会立即自动采集一次。
- 后续按每日时间自动采集，也支持手动点“立即采集”。
- 主窗口关闭只缩到托盘，只有托盘菜单里的“退出程序”会真正退出并关闭影子 Chrome。
- 支持当前用户登录后自启，写入 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`，不需要管理员权限。
- 当前阶段以 **本地日志和主界面结果展示** 为准，不要求立即入库。

## 采集引擎配置

- `data/app_state.json` 里的 `captureEngine` 默认为 `external`。
- `shadowChromeProfileDir` 默认位于 `%LOCALAPPDATA%\YuanshengDataAssistant\shadow-chrome`。
- `shadowChromeAutoLaunch=true` 时，主程序启动会自动拉起或接管影子 Chrome。
- `autoStartEnabled=true` 时，启用 Windows 当前用户登录后自启。
- 运行状态文件和日志写入 `data/` 目录，打包产物写入 `build/`、`dist/`，这些目录不提交到 Git。
