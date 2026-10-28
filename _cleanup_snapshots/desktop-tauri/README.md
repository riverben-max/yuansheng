# 远盛数据助手 Tauri 壳

这是新的桌面壳，界面使用 Vue3 + Element Plus，采集核心暂时沿用 `../desktop-client/sidecar_cli.py`。

## 本地前端预览

```powershell
npm install
npm run build
```

## Tauri 运行前置条件

当前机器需要先安装 Rust/Cargo 和 Windows C++ Build Tools，之后再运行：

```powershell
npm run tauri:dev
```

开发模式下 Rust 命令会调用：

```text
../desktop-client/sidecar_cli.py
```

生产打包前可先构建 Python sidecar：

```powershell
pwsh ./scripts/build_sidecar.ps1
```

如要显式指定 sidecar 可执行文件：

```powershell
$env:YUANSHENG_SIDECAR_EXE="D:\Tools\work_project\desktop-client\dist\yuansheng-sidecar.exe"
npm run tauri:dev
```
