# 远盛数据助手 - 浏览器调试端口诊断脚本
# 用法：在客户电脑用 PowerShell 运行 (右键 PowerShell → 以管理员身份运行)
#       cd 到这个文件所在目录, 执行 powershell -ExecutionPolicy Bypass -File diagnose.ps1
# 或者: 直接复制下面所有内容粘贴到 PowerShell 窗口回车

$ErrorActionPreference = "Continue"
Write-Host "`n========== 远盛数据助手浏览器诊断 ==========" -ForegroundColor Cyan

# 1. 查 360 浏览器进程及启动参数
Write-Host "`n[1] 360 浏览器进程及启动参数：" -ForegroundColor Yellow
$procs = Get-CimInstance Win32_Process -Filter "Name = '360ChromeX.exe' OR Name = 'chrome.exe' OR Name = '360Chrome.exe'" -ErrorAction SilentlyContinue
if (-not $procs) {
    Write-Host "  没有 360/Chrome 浏览器进程在运行" -ForegroundColor Red
} else {
    $procs | ForEach-Object {
        $hasDebug = $_.CommandLine -like "*--remote-debugging-port=*"
        $tag = if ($hasDebug) { "✓ 带调试端口" } else { "✗ 未带调试端口" }
        $color = if ($hasDebug) { "Green" } else { "Red" }
        Write-Host ("  PID={0} {1}" -f $_.ProcessId, $tag) -ForegroundColor $color
        Write-Host ("    {0}" -f $_.CommandLine) -ForegroundColor DarkGray
    }
}

# 2. 查端口 9527 监听
Write-Host "`n[2] 端口 9527 状态：" -ForegroundColor Yellow
$listen = netstat -ano | Select-String "127.0.0.1:9527" | Select-String "LISTENING"
if ($listen) {
    Write-Host "  ✓ 在监听" -ForegroundColor Green
    $listen | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
} else {
    Write-Host "  ✗ 未监听（CDP 连不上）" -ForegroundColor Red
}

# 3. 查所有 360 快捷方式参数
Write-Host "`n[3] 系统中所有 360/Chrome 快捷方式：" -ForegroundColor Yellow
$shell = New-Object -ComObject WScript.Shell
$searchDirs = @(
    [Environment]::GetFolderPath("Desktop"),
    [Environment]::GetFolderPath("CommonDesktopDirectory"),
    "$env:APPDATA\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar",
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs",
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs"
)
$found = 0
foreach ($d in $searchDirs) {
    if (-not (Test-Path $d)) { continue }
    Get-ChildItem $d -Recurse -Filter "*.lnk" -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $sc = $shell.CreateShortcut($_.FullName)
            $tgt = [string]$sc.TargetPath
            if ($tgt -match "360ChromeX|chrome\.exe|360Chrome") {
                $found++
                $ok = $sc.Arguments -like "*--remote-debugging-port=9527*"
                $tag = if ($ok) { "✓" } else { "✗" }
                $color = if ($ok) { "Green" } else { "Red" }
                Write-Host "  $tag $($_.FullName)" -ForegroundColor $color
                Write-Host "      target = $tgt" -ForegroundColor DarkGray
                Write-Host "      args   = $($sc.Arguments)" -ForegroundColor DarkGray
            }
        } catch {}
    }
}
if ($found -eq 0) { Write-Host "  没找到任何 360/Chrome 快捷方式" -ForegroundColor Red }

# 4. 查远盛软件相关进程
Write-Host "`n[4] 远盛数据助手相关进程：" -ForegroundColor Yellow
Get-Process -Name "yuansheng-data-assistant","yuansheng-sidecar" -ErrorAction SilentlyContinue | Select-Object Id,ProcessName | Format-Table -AutoSize

# 5. 给出建议
Write-Host "`n========== 诊断结论 ==========" -ForegroundColor Cyan
$hasDebugProc = $procs | Where-Object { $_.CommandLine -like "*--remote-debugging-port=9527*" }
if ($hasDebugProc -and $listen) {
    Write-Host "状态：✓ 浏览器调试端口正常监听，可以读 Cookie。" -ForegroundColor Green
    Write-Host "如软件还报错，让它点一下「浏览器」按钮，把弹窗截图发出来。" -ForegroundColor Green
} elseif ($procs -and -not $hasDebugProc) {
    Write-Host "问题：浏览器在运行但未带调试端口启动。" -ForegroundColor Red
    Write-Host "解决：" -ForegroundColor Yellow
    Write-Host "  1) 关闭所有 360 浏览器：Get-Process 360ChromeX | Stop-Process -Force"
    Write-Host "  2) 用桌面 360 极速浏览器X.lnk 双击重启"
    Write-Host "  3) 在浏览器里登录抖店"
    Write-Host "  4) 在远盛软件点抖店行的「浏览器」按钮"
} elseif (-not $procs) {
    Write-Host "状态：浏览器没在运行。" -ForegroundColor Yellow
    Write-Host "解决：双击桌面 360 极速浏览器X.lnk 启动，登录抖店后再到软件点「浏览器」按钮" -ForegroundColor Yellow
}
Write-Host ""
