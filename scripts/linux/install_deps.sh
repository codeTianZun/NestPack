#!/usr/bin/env bash
# 安装 Linux CLI 的开发依赖；运行本身只需 Python 标准库。
# 平台：Linux。脚本会优先使用项目根的 .venv，没有则回退系统 python3。
#
# 用法（在项目根目录执行）：
#   ./scripts/linux/install_deps.sh             # 提示无需安装 Python 运行依赖
#   ./scripts/linux/install_deps.sh --dev        # 安装静态检查依赖
#   ./scripts/linux/install_deps.sh --dev --upgrade  # 升级开发依赖
#
# 缺少 .venv 时会提示用户先建虚拟环境；不会自动创建，避免污染系统 Python。
set -e

if [ "$(uname -s)" != "Linux" ]; then
    echo "错误：此脚本仅支持 Linux。" >&2
    exit 1
fi

# 脚本在 scripts/linux/ 下，向上两层回到项目根。
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

# 有 .venv 用 .venv，否则回退系统 python3（缺 pip 时单独报错）。
if [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
else
    echo "错误：未找到可用的 Python 环境。请先安装 Python 3.10+，或在项目根目录创建 .venv 虚拟环境。" >&2
    exit 1
fi

DEV=0
UPGRADE=0
for arg in "$@"; do
    case "$arg" in
        --dev)     DEV=1 ;;
        --upgrade) UPGRADE=1 ;;
        *) echo "未知参数：$arg（可用：--dev、--upgrade）" >&2; exit 2 ;;
    esac
done

if [ "$DEV" = 0 ]; then
    echo "Linux CLI 仅需 Python 3.10+ 标准库，无需安装第三方 Python 运行依赖。"
    echo "python3 -m cli --install-tools 提供 RAR 官网指引并安装 7-Zip；开发依赖请加 --dev。"
    exit 0
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "提示：未发现 .venv，依赖将装到系统 Python；建议先创建虚拟环境：" >&2
    echo "  $PY -m venv .venv && ./.venv/bin/python -m pip install -U pip" >&2
fi

INSTALL_ARGS=(install)
if [ "$UPGRADE" = 1 ]; then
    INSTALL_ARGS+=(--upgrade)
fi
"$PY" -m pip "${INSTALL_ARGS[@]}" -r requirements-dev.txt
echo "静态检查依赖安装完成：ruff / mypy。"
