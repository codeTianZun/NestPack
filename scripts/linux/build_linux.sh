#!/usr/bin/env bash
# NestPack Linux CLI 精简包入口：产出 dist/nestpack-linux-cli.tar.gz。
# 平台：Linux；Windows 可直接调用 python scripts/build.py pack-linux。
# 选定 Python 解释器后调用 scripts/build.py 的 pack-linux 子命令。
#
# 用法（在项目根目录执行）：
#   ./scripts/linux/build_linux.sh                          # 打包 Linux CLI 精简包
#   ./scripts/linux/build_linux.sh --help                    # 查看 build.py pack-linux 的其余参数
# 其余参数原样传给 build.py pack-linux（详见 python scripts/build.py --help）。
set -e

if [ "$(uname -s)" != "Linux" ]; then
    echo "错误：此脚本仅支持 Linux。" >&2
    exit 1
fi

# 脚本在 scripts/linux/ 下，向上两层回到项目根。
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

# 有 .venv 用 .venv，否则回退系统 python3；pack-linux 不需要 PyInstaller，仅依赖 Python 标准库。
if [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
    echo "提示：未发现 .venv，使用系统 python3；打包逻辑只需标准库，不影响构建。" >&2
else
    echo "错误：未找到可用的 Python 环境。请先安装 Python 3.10+，或在项目根目录创建 .venv 虚拟环境。" >&2
    exit 1
fi

"$PY" scripts/build.py pack-linux "$@"
