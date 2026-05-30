# 发版流程

桌面端（远盛数据助手 Tauri）发版操作手册。每次发布新版本必须按本文件流程执行。

## 一、版本号约束

发版必须同时升级四个文件的版本号，保持完全一致。`scripts/validate_release_config.ps1` 会在打包前强制校验，缺一处即失败。

| 文件 | 字段 |
| --- | --- |
| `desktop-tauri/package.json` | `"version": "..."` |
| `desktop-tauri/src-tauri/tauri.conf.json` | `"version": "..."` |
| `desktop-tauri/src-tauri/Cargo.toml` | `version = "..."` |
| `desktop-client/sidecar_cli.py` | `SIDECAR_VERSION = "..."` |

### 版本号选择（语义化版本 SemVer）

- **PATCH（如 1.0.0 → 1.0.1）**：只修 Bug，无新功能、无界面变化、无字段变化
- **MINOR（如 1.0.1 → 1.1.0）**：新增功能或显著增强（如新增平台、新增按钮）
- **MAJOR（如 1.x.x → 2.0.0）**：重大变化或不兼容改动（如配置文件格式变化、删除字段）

## 二、发版步骤

### 1. 改版本号

四个文件同时改成新版本号（参考第一节表格）。

### 2. 打包

```powershell
cd D:\Tools\work_project\yuansheng-push\desktop-tauri
npm run tauri:build
```

`tauri:build` 会自动按以下顺序执行：

1. `validate:release`：校验四处版本号一致、`tauri.conf.json` 资源配置完整、`direct_api_capture.template.json` 不含 cookie 等
2. `build:sidecar`：用 PyInstaller 重新打包 `desktop-client/sidecar_cli.py` → `src-tauri/binaries/yuansheng-sidecar.exe`
3. `vite build`：编译前端
4. Cargo release 编译 + NSIS 打包

产物路径：

```
src-tauri/target/release/bundle/nsis/远盛数据助手_<版本>_x64-setup.exe
```

### 3. 生成更新清单

```powershell
npm run release:update-files
```

产物会输出到 `desktop-tauri/release-upload/`：

```
release-upload/
├── desktop/
│   └── update.json                                        # 客户端检查更新读这个
└── downloads/
    └── yuansheng-data-assistant-<版本>-x64-setup.exe       # 实际下载文件
```

`update.json` 内容示例：

```json
{
  "version": "1.1.0",
  "downloadUrl": "http://120.27.22.50/downloads/yuansheng-data-assistant-1.1.0-x64-setup.exe",
  "sha256": "...",
  "notes": "",
  "force": false
}
```

可选参数（手动调用 `scripts/prepare_update_release.ps1`）：

- `-Notes "本次更新内容..."`：填写更新说明
- `-ForceUpdate`：强制升级（客户端不能跳过）
- `-Version "1.1.0"`：覆盖版本号
- `-BaseUrl "http://..."`：覆盖下载基础地址

### 4. 上传到服务器

服务器：`root@120.27.22.50`，本地已配置 SSH 密钥免密登录。Web 根目录：`/var/www/yuansheng/`。

```powershell
cd D:\Tools\work_project\yuansheng-push\desktop-tauri

# 1) 备份服务器现有 update.json（带时间戳，方便回滚）
ssh root@120.27.22.50 'cp /var/www/yuansheng/desktop/update.json /var/www/yuansheng/desktop/update.json.bak.$(date +%Y%m%d-%H%M%S)'

# 2) 上传新安装包（先传 .exe，避免客户端拉到新 update.json 但下载链接 404）
scp "release-upload\downloads\yuansheng-data-assistant-<版本>-x64-setup.exe" root@120.27.22.50:/var/www/yuansheng/downloads/

# 3) 上传新 update.json
scp "release-upload\desktop\update.json" root@120.27.22.50:/var/www/yuansheng/desktop/update.json

# 4) HTTP 验证
(Invoke-RestMethod "http://120.27.22.50/desktop/update.json").version
(Invoke-WebRequest "http://120.27.22.50/downloads/yuansheng-data-assistant-<版本>-x64-setup.exe" -Method Head).StatusCode
```

注意 SSH 命令里的 `$(date +...)` 必须用**单引号**包裹，否则 PowerShell 会把它当作本地表达式解析掉，导致备份文件名后面没有时间戳。

服务器目录结构：

```
/var/www/yuansheng/
├── desktop/
│   ├── update.json                                          # 当前版本清单
│   └── update.json.bak.YYYYmmdd-HHMMSS                      # 历史备份
└── downloads/
    └── yuansheng-data-assistant-<版本>-x64-setup.exe         # 历次安装包，全部保留作回滚兜底
```

上传后客户端下次启动时调 `check_update` 命令，对比版本号发现新版即弹更新提示。

## 三、常见问题

### Q1：版本号校验失败 `Release versions must match`

四个文件版本号没全改完。运行下面快速对照：

```powershell
cd D:\Tools\work_project\yuansheng-push\desktop-tauri
Select-String '"version"' package.json src-tauri\tauri.conf.json
Select-String '^version' src-tauri\Cargo.toml
Select-String '^SIDECAR_VERSION' ..\desktop-client\sidecar_cli.py
```

### Q2：`build_sidecar.ps1` 失败：缺少 PyInstaller

```powershell
pip install pyinstaller
```

### Q3：`build_sidecar.ps1` 失败：缺少 pywin32

打包后 sidecar.exe 运行时报 `No module named 'win32com'`。安装：

```powershell
pip install "pywin32>=306"
```

并确保 `desktop-client/requirements.txt` 包含 `pywin32>=306; sys_platform == "win32"`。

### Q4：客户那边 check_update 不弹更新

排查顺序：

1. 服务器上的 `update.json` 版本号是不是真的比客户当前装的版本高
2. 服务器路径是不是 `http://120.27.22.50/desktop/update.json`（路径要带 `/desktop/`）
3. `update.json` 里的 `downloadUrl` 是不是可访问
4. 客户端 `check_update` 默认 24 小时跑一次，可以让客户重启软件触发
5. 客户端 settings 里 `updateCheckUrl` 是否被改成别的地址

### Q5：客户端运行时弹黑色控制台窗口

sidecar.exe 是 PyInstaller console 模式打包的（必须保留 console 才能跟 Tauri 走 stdin/stdout 通信）。Tauri 启动 sidecar 时必须用 `CREATE_NO_WINDOW` 标志（已在 `main.rs::spawn_sidecar` 处理）。如果还出现，检查：

- `main.rs` 里 `spawn_sidecar` 是否包含 `command_builder.creation_flags(CREATE_NO_WINDOW)`
- 是否有别的地方直接启动 sidecar.exe 没走 `spawn_sidecar`

### Q6：客户安装时报 `Error opening file for writing: ...\yuansheng-sidecar.exe`

NSIS 写不进 sidecar.exe，几种可能的根因：

**情况 A：旧版本进程还在跑（最常见）**
- 客户的旧版本主程序、sidecar 或托盘图标还在后台
- 修复：`installer.nsh` 已加 `NSIS_HOOK_PREINSTALL` 自动 `taskkill /F /IM yuansheng-data-assistant.exe` 和 `yuansheng-sidecar.exe`
- 如果客户那边 hook 没生效（例如杀毒软件拦截 taskkill），让客户手动从托盘退出 + 任务管理器结束所有 `yuansheng-*` 进程后再装

**情况 B：1.0.0 残留的 `binaries` 文件挡住了 `binaries\` 目录创建**
- 早期 1.0.0 有个 bug，把 sidecar.exe 错误地直接命名成 `binaries`（无扩展名）写入安装目录
- 新版本想创建 `binaries\` 目录，但同名文件挡住 → "Can't write" 报错
- 修复：`installer.nsh` 已加 `Delete "$INSTDIR\binaries"`（NSIS 的 Delete 只删文件不删目录，幂等安全）

**情况 C：杀毒软件实时锁文件**
- 国内客户机器常装 360 安全卫士，PyInstaller exe 经常被 AV 扫描时锁住
- 排查方法：让客户**临时关闭 360 主动防御**再装

### Q7：客户机器上没有 360 桌面快捷方式（只找到 Chrome 等其他浏览器）

诊断特征（客户截图运行日志看到）：

```
诊断 3/3：浏览器快捷方式  →  ⚠ 没找到 360 极速浏览器的快捷方式（只找到 N 个其他浏览器的）
```

原因：客户从 360 安全卫士的"软件启动器"、任务栏固定区、或者桌面非标 .lnk 启动 360，**标准 .lnk 路径下没有 360 快捷方式**可改。

历史尝试：

1. ~~改 .lnk 加 `--remote-debugging-port=9527`（1.1.0~1.1.4）~~：找不到 360 .lnk，方案失效
2. ~~自动创建"抖店采集专用浏览器"快捷方式（1.1.5）~~：客户嫌多个图标，弃用
3. **`relaunch_browser_for_debug` 命令（1.1.6 起）**：软件直接 `taskkill` 所有 360 + `subprocess.Popen` 自己 spawn 一个 360.exe（带调试端口 + 抖店登录页），完全不依赖客户的快捷方式

`relaunch_browser_for_debug` 实现细节见 `desktop-client/sidecar_cli.py`，它通过 `_get_running_360_exe()` 从已运行的 360 进程读 `proc.exe()` 拿到客户机器实际安装的 exe 路径（即使装在非标位置也能命中）。

### Q8：客户端无法导入 Cookie，怎么远程诊断（不能远程操作客户电脑时）

从 1.1.4 起，每次点「浏览器」按钮失败时，运行日志里会自动输出 3 项诊断：

```
[HH:MM:SS] 导入登录信息未成功（<状态>）。详细诊断：
[HH:MM:SS] 诊断 1/3：360 浏览器进程  →  ✓/✗ 是否带调试端口启动
[HH:MM:SS] 诊断 2/3：调试端口 9527    →  ✓/✗ 是否在监听
[HH:MM:SS] 诊断 3/3：浏览器快捷方式  →  ✓/✗ 360 快捷方式状态
[HH:MM:SS] → 解决：<具体下一步指引>
```

让客户**截图运行日志框**发回来即可对照定位。诊断逻辑入口：`desktop-client/browser_debug_setup.py::collect_browser_diagnostics`。

## 四、回滚

如果新版本发布后发现严重问题：

1. 把上一版的 `update.json` 重新上传覆盖（versionRoll back）
2. 上一版的安装包应该还留在服务器 `/downloads/`，不要删
3. 客户端下次 check_update 不会回滚（只比较"服务器版本 > 当前版本"），要让已升级客户回滚需手动卸载重装老版本

建议：每次新版本发布前，先备份服务器现有 `update.json` 和当前最新 `*.exe`。

## 五、发版前自检

发版前确认：

- [ ] 四处版本号一致
- [ ] 关键功能在本机完整跑通（至少：登录、采集、上传、Cookie 导入）
- [ ] `npm run tauri:build` 成功无警告
- [ ] 在干净环境（新建用户/虚拟机/同事电脑）装一遍验证安装包
- [ ] update.json 里的 sha256 跟实际安装包一致（脚本自动算，理论上不会出错）
- [ ] 上传后用浏览器访问 `http://120.27.22.50/desktop/update.json` 能直接拿到 JSON
