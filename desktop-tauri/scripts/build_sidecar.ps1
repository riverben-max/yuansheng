$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$client = Join-Path (Split-Path -Parent $root) "desktop-client"
$binDir = Join-Path (Join-Path $root "src-tauri") "binaries"
$template = Join-Path "data" "direct_api_capture.template.json"

Push-Location $client
try {
  python -m PyInstaller --noconfirm --clean --name yuansheng-sidecar --onedir --add-data "$template;data" sidecar_cli.py
}
finally {
  Pop-Location
}

New-Item -ItemType Directory -Force -Path $binDir | Out-Null
# 清理旧产物：onefile 时代的单文件 exe，以及上一次 onedir 目录
$legacyExe = Join-Path $binDir "yuansheng-sidecar.exe"
if (Test-Path -LiteralPath $legacyExe) { Remove-Item -Force $legacyExe }
$targetDir = Join-Path $binDir "yuansheng-sidecar"
if (Test-Path -LiteralPath $targetDir) { Remove-Item -Recurse -Force $targetDir }

$sidecarDir = Join-Path (Join-Path $client "dist") "yuansheng-sidecar"
Copy-Item -Recurse -Force $sidecarDir $binDir
Write-Host "Sidecar (onedir) copied to $targetDir" -ForegroundColor Green
