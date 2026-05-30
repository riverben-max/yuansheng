$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$client = Join-Path (Split-Path -Parent $root) "desktop-client"
$binDir = Join-Path (Join-Path $root "src-tauri") "binaries"
$template = Join-Path "data" "direct_api_capture.template.json"

Push-Location $client
try {
  python -m PyInstaller --noconfirm --clean --name yuansheng-sidecar --onefile --add-data "$template;data" sidecar_cli.py
}
finally {
  Pop-Location
}

New-Item -ItemType Directory -Force -Path $binDir | Out-Null
$sidecarExe = Join-Path (Join-Path $client "dist") "yuansheng-sidecar.exe"
Copy-Item -Force $sidecarExe $binDir
Write-Host "Sidecar EXE copied to $binDir" -ForegroundColor Green
