#Requires -Version 7
# 启动 NestPack 图形界面（PySide6 桌面程序）。平台：Windows（PowerShell 7）。
# 用法：pwsh -ExecutionPolicy Bypass -File scripts\windows\start_gui.ps1
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw '此脚本仅支持 Windows。' }

# 脚本在 scripts\windows\ 下，向上两层回到项目根。
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# 有 .venv 用 .venv（pythonw 启动无控制台窗口），否则回退系统 python/pythonw。
$venvPy  = Join-Path $projectRoot '.venv\Scripts\python.exe'
$venvPyw = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
$pyExe   = if (Test-Path -LiteralPath $venvPy) { $venvPy } else { $null }
$pywExe  = if (Test-Path -LiteralPath $venvPyw) { $venvPyw } else { $null }

if (-not $pyExe) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw '未找到可用的 Python 环境。请先安装 Python，或在项目根目录创建 .venv 虚拟环境。'
    }
    $pyExe = 'python'
}
if (-not $pywExe) { $pywExe = 'pythonw' }

& $pyExe -c 'import PySide6' *> $null
if ($LASTEXITCODE -ne 0) {
    throw "未找到可用的 PySide6 环境。请先执行：$pyExe -m pip install -r requirements.txt"
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'gui\__main__.py'))) {
    throw '未找到程序文件 gui\__main__.py。'
}

# GUI 从项目根启动，默认配置等文件落在项目根。
Start-Process -FilePath $pywExe -ArgumentList '-m', 'gui' -WorkingDirectory $projectRoot
