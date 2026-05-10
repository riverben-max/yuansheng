$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$client = Join-Path (Split-Path -Parent $root) "desktop-client"
$binDir = Join-Path $root "src-tauri" "binaries"

Push-Location $client
try {
  python -m PyInstaller --noconfirm --clean --name yuansheng-sidecar --onefile sidecar_cli.py
}
finally {
  Pop-Location
}

New-Item -ItemType Directory -Force -Path $binDir | Out-Null
Copy-Item -Force (Join-Path $client "dist" "yuansheng-sidecar.exe") $binDir
Write-Host "Sidecar EXE copied to $binDir" -ForegroundColor Green
