# Linux 平台参考

## CLI 入口

- 发布程序：`./nestpack-linux-cli --config 路径`，首次下载后执行
  `chmod +x nestpack-linux-cli`，无需安装 Python。
- 源码入口：`./platforms/linux/launcher.sh --config 路径` 或
  `python3 -m cli ...`。launcher 将项目根加入 Python 模块路径，保持调用
  目录与参数路径基准。参数与 JSON 输出契约见 `cli.md`，解包见 `unpack.md`。
- 前置依赖：rarlab 官方 `rar` 命令（RAR 层用）；7z / zip 层另需
  7-Zip 官方 `7zz` 或 p7zip 的 `7z`（均支持 -tzip）。
  `python3 -m cli --install-tools` 显示 RAR 官网安装指引，并下载、校验
  7-Zip 到当前程序目录的 `dependencies/7z/`，保留许可材料。

## 平台差异（linux）

- `winrar_path: auto` 按当前程序目录 `dependencies/` → PATH 查 `rar`；
  `sevenzip_path: auto` 同序查 `7zz` / `7z` / `7za`。
- 无后台开关，`show_winrar_gui` 忽略；进度直接输出到终端。
- Linux 仅支持 CLI；GUI 入口在加载 Qt 前拒绝非 Windows 系统。

## Python 依赖一键安装

~~~bash
./scripts/linux/install_deps.sh             # 提示 CLI 无需第三方 Python 运行依赖
./scripts/linux/install_deps.sh --dev        # 安装 ruff / mypy 静态检查工具
./scripts/linux/install_deps.sh --dev --upgrade  # 升级开发依赖
~~~

源码运行 CLI 只需 Python 3.10+ 标准库。安装开发依赖时自动选择
`.venv/bin/python` 或回退系统 `python3`，未建 `.venv` 时会提示先建。Windows 对称入口为
`scripts/windows/install_deps.ps1`。

## 单文件构建

Linux 构建入口为 `./scripts/linux/build_linux.sh`（内部调
`scripts/build.py`），产物为 `dist/nestpack-linux-cli`。
