#!/usr/bin/env bash
# 在 Linux 上运行命令行版。
set -e
if [ "$(uname -s)" != "Linux" ]; then
    echo "错误：此入口仅支持 Linux。" >&2
    exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NESTPACK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
exec python3 -c 'import runpy, sys; sys.path.insert(0, sys.argv.pop(1)); runpy.run_module("cli", run_name="__main__")' "$NESTPACK_ROOT" "$@"
