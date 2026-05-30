$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$repo = Split-Path -Parent $root
$client = Join-Path $repo "desktop-client"

function Read-Json($path) {
  return Get-Content -Path $path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Match-Required($text, $pattern, $label) {
  $match = [regex]::Match($text, $pattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
  if (-not $match.Success) {
    throw "Unable to read $label."
  }
  return $match.Groups[1].Value
}

$packageJsonPath = Join-Path $root "package.json"
$tauriConfigPath = Join-Path (Join-Path $root "src-tauri") "tauri.conf.json"
$cargoTomlPath = Join-Path (Join-Path $root "src-tauri") "Cargo.toml"
$sidecarPath = Join-Path $client "sidecar_cli.py"
$templatePath = Join-Path (Join-Path $client "data") "direct_api_capture.template.json"
$buildSidecarPath = Join-Path (Join-Path $root "scripts") "build_sidecar.ps1"
$prepareUpdatePath = Join-Path (Join-Path $root "scripts") "prepare_update_release.ps1"

$packageJson = Read-Json $packageJsonPath
$tauriConfig = Read-Json $tauriConfigPath
$cargoText = Get-Content -Path $cargoTomlPath -Raw -Encoding UTF8
$sidecarText = Get-Content -Path $sidecarPath -Raw -Encoding UTF8

$versions = @(
  [string]$packageJson.version
  [string]$tauriConfig.version
  (Match-Required $cargoText '^version\s*=\s*"([^"]+)"' "Cargo package version")
  (Match-Required $sidecarText '^SIDECAR_VERSION\s*=\s*"([^"]+)"' "sidecar version")
)

if (($versions | Select-Object -Unique).Count -ne 1) {
  throw "Release versions must match. Found: $($versions -join ', ')"
}

$resources = @($tauriConfig.bundle.resources)
if ($resources -notcontains "binaries/yuansheng-sidecar.exe") {
  throw "tauri.conf.json must preserve binaries/yuansheng-sidecar.exe as a resource path."
}

if (-not (Test-Path -LiteralPath $templatePath)) {
  throw "Missing direct_api_capture.template.json."
}

$template = Read-Json $templatePath
if ($template.PSObject.Properties.Name -contains "cookie" -or $template.PSObject.Properties.Name -contains "cookieProtected") {
  throw "Direct API template must not contain cookie or cookieProtected."
}
foreach ($request in @($template.requests)) {
  if ($request.PSObject.Properties.Name -contains "cookie" -or $request.PSObject.Properties.Name -contains "cookieProtected") {
    throw "Direct API template request entries must not contain cookie or cookieProtected."
  }
}

$buildSidecarText = Get-Content -Path $buildSidecarPath -Raw -Encoding UTF8
if ($buildSidecarText -notmatch '--add-data "\$template;data"') {
  throw "build_sidecar.ps1 must package the direct API template into the sidecar."
}

if (-not (Test-Path -LiteralPath $prepareUpdatePath)) {
  throw "Missing prepare_update_release.ps1 for update manifest generation."
}

$releaseScript = [string]$packageJson.scripts."release:update-files"
if ($releaseScript -notmatch "prepare_update_release\.ps1") {
  throw "package.json must expose release:update-files to generate desktop/update.json and downloads installer."
}

Write-Host "Release config OK: version $($versions[0])" -ForegroundColor Green
