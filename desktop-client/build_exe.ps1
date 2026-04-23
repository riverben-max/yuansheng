param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Installing desktop runtime dependencies..." -ForegroundColor Cyan
& $PythonExe -m pip install -r (Join-Path $scriptDir "requirements.txt")

Write-Host "Installing build dependencies..." -ForegroundColor Cyan
& $PythonExe -m pip install -r (Join-Path $scriptDir "requirements-build.txt")

Write-Host "Cleaning previous build output..." -ForegroundColor Cyan
Remove-Item -LiteralPath (Join-Path $scriptDir "build") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $scriptDir "dist") -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Building Yuansheng desktop client..." -ForegroundColor Cyan
& $PythonExe -m PyInstaller (Join-Path $scriptDir "qingbird_data_assistant.spec") --noconfirm

Write-Host "Build complete. Output: $(Join-Path $scriptDir 'dist\\远盛数据助手')" -ForegroundColor Green
