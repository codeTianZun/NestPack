#Requires -Version 7
# 安装 NestPack 的 Python 依赖（requirements.txt；-Dev 另装 requirements-dev.txt）。
# 平台：Windows（PowerShell 7）。脚本会优先使用项目根的 .venv，没有则回退系统 python。
# 用法（在项目根目录执行）：
#   pwsh -ExecutionPolicy Bypass -File scripts\windows\install_deps.ps1             # 只装运行依赖
#   pwsh -ExecutionPolicy Bypass -File scripts\windows\install_deps.ps1 -Dev        # 同时装静态检查依赖
#   pwsh -ExecutionPolicy Bypass -File scripts\windows\install_deps.ps1 -Upgrade    # 带 --upgrade 重新解析依赖
#   pwsh -ExecutionPolicy Bypass -File scripts\windows\install_deps.ps1 -Dev -Upgrade
# 缺少 .venv 时会提示用户先建虚拟环境；不会自动创建，避免污染系统 Python。
[CmdletBinding()]
param(
    [switch]$Dev,
    [switch]$Upgrade
)
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw '此脚本仅支持 Windows。' }

# 脚本在 scripts\windows\ 下，向上两层回到项目根。
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot

# 有 .venv 用 .venv，否则回退系统 python（缺 pip 时单独报错）。
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    $py = $venvPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $py = 'python'
} else {
    throw '未找到可用的 Python 环境。请先安装 Python，或在项目根目录创建 .venv 虚拟环境。'
}

# 顺带提示没建 .venv 的用户，避免依赖装到系统 Python 污染全局。
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host '提示：未发现 .venv，依赖将装到系统 Python；建议先创建虚拟环境：' -ForegroundColor Yellow
    Write-Host "  $py -m venv .venv ; .\.venv\Scripts\python.exe -m pip install -U pip" -ForegroundColor Yellow
}

$targets = @('requirements.txt')
if ($Dev) { $targets += 'requirements-dev.txt' }

$installArgs = @('-m', 'pip', 'install')
if ($Upgrade) { $installArgs += '--upgrade' }
$installArgs += '-r'

foreach ($req in $targets) {
    $reqPath = Join-Path $projectRoot $req
    if (-not (Test-Path -LiteralPath $reqPath)) {
        Write-Host "跳过缺失的依赖清单：$req" -ForegroundColor Yellow
        continue
    }
    Write-Host "安装 $req ..."
    & $py @installArgs $reqPath
    if ($LASTEXITCODE -ne 0) { throw "安装 $req 失败（退出码 $LASTEXITCODE）。" }
}

Write-Host ''
Write-Host '依赖安装完成。'
if ($Dev) {
    Write-Host '已含静态检查依赖：ruff / mypy（按需使用）。'
} else {
    Write-Host '仅安装了运行依赖；开发依赖请加 -Dev 重跑。'
}
