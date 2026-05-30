param(
  [string]$Version = "",
  [string]$InstallerPath = "",
  [string]$BaseUrl = "http://120.27.22.50",
  [string]$Notes = "",
  [switch]$ForceUpdate,
  [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

function Read-Json($path) {
  return Get-Content -Path $path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-Sha256Hex($path) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  $stream = [System.IO.File]::OpenRead($path)
  try {
    $hashBytes = $sha.ComputeHash($stream)
  }
  finally {
    $stream.Dispose()
    $sha.Dispose()
  }
  return (($hashBytes | ForEach-Object { $_.ToString("x2") }) -join "")
}

if (-not $Version) {
  $packageJson = Read-Json (Join-Path $root "package.json")
  $Version = [string]$packageJson.version
}

if (-not $InstallerPath) {
  $nsisDir = Join-Path (Join-Path (Join-Path $root "src-tauri") "target") "release\bundle\nsis"
  $installer = Get-ChildItem -LiteralPath $nsisDir -Filter "*_x64-setup.exe" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($null -eq $installer) {
    throw "No NSIS installer found under $nsisDir. Run npm run tauri:build first."
  }
  $InstallerPath = $installer.FullName
}

if (-not (Test-Path -LiteralPath $InstallerPath)) {
  throw "Installer not found: $InstallerPath"
}

if (-not $OutDir) {
  $OutDir = Join-Path $root "release-upload"
}

$stageDesktopDir = Join-Path $OutDir "desktop"
$stageDownloadsDir = Join-Path $OutDir "downloads"
New-Item -ItemType Directory -Force -Path $stageDesktopDir | Out-Null
New-Item -ItemType Directory -Force -Path $stageDownloadsDir | Out-Null

$downloadName = "yuansheng-data-assistant-$Version-x64-setup.exe"
$stagedInstaller = Join-Path $stageDownloadsDir $downloadName
Copy-Item -LiteralPath $InstallerPath -Destination $stagedInstaller -Force

$sha256 = Get-Sha256Hex $stagedInstaller
$cleanBaseUrl = $BaseUrl.TrimEnd("/")
$manifest = [ordered]@{
  version = $Version
  downloadUrl = "$cleanBaseUrl/downloads/$downloadName"
  sha256 = $sha256
  notes = $Notes
  force = [bool]$ForceUpdate
}

$manifestPath = Join-Path $stageDesktopDir "update.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($manifestPath, (($manifest | ConvertTo-Json -Depth 4) + "`n"), $utf8NoBom)

Write-Host "Prepared update manifest: $manifestPath" -ForegroundColor Green
Write-Host "Prepared installer: $stagedInstaller" -ForegroundColor Green
Write-Host "Upload the contents of $OutDir to the server web root." -ForegroundColor Cyan
