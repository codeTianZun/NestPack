#Requires -Version 7
# NestPack Windows 打包入口：产出 dist\NestPack.exe（GUI）与 dist\nestpack-cli.exe（CLI）。
# 平台：Windows（PowerShell 7）。实际构建逻辑在 scripts\build.py，
# 本脚本只负责选定 Python 解释器并转交参数。
# 用法（在项目根目录执行）：
#   pwsh -ExecutionPolicy Bypass -File scripts\windows\build_exe.ps1
#   pwsh -ExecutionPolicy Bypass -File scripts\windows\build_exe.ps1 --yes
# 其余参数原样传给 build.py（--yes / --no-kill，说明见 python scripts\build.py --help）。
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw '此脚本仅支持 Windows。' }

# 脚本在 scripts\windows\ 下，向上两层回到项目根。
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot

# 有 .venv 用 .venv，否则回退系统 python。
$py = if (Test-Path -LiteralPath '.venv\Scripts\python.exe') { '.venv\Scripts\python.exe' } else { 'python' }

& $py scripts\build.py @args
exit $LASTEXITCODE
