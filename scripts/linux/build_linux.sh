#!/usr/bin/env bash
# NestPack Linux CLI 构建入口：产出 dist/NestPack-v1.1.0-linux-cli。
# 平台：Linux。选定 Python 解释器后调用 scripts/build.py。
#
# 用法（在项目根目录执行）：
#   ./scripts/linux/build_linux.sh          # 构建 Linux CLI 可执行文件
#   ./scripts/linux/build_linux.sh --help   # 查看 build.py 参数
set -e

if [ "$(uname -s)" != "Linux" ]; then
    echo "错误：此脚本仅支持 Linux。" >&2
    exit 1
fi

# 脚本在 scripts/linux/ 下，向上两层回到项目根。
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

# 有 .venv 用 .venv，否则回退系统 python3；构建需要 PyInstaller。
if [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
    echo "提示：未发现 .venv，使用系统 python3 构建。" >&2
else
    echo "错误：未找到可用的 Python 环境。请先安装 Python 3.10+，或在项目根目录创建 .venv 虚拟环境。" >&2
    exit 1
fi

"$PY" scripts/build.py "$@"
