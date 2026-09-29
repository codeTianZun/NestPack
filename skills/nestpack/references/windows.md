# Windows 平台参考

CLI 入口参数与 JSON 输出契约跨平台一致，见 [cli.md](cli.md)；
解包见 [unpack.md](unpack.md)。

## CLI

源码在项目根目录使用 `python -m cli`，只需 Python 3.10+ 标准库；
发布程序使用 `NestPack-v1.1.0-windows-cli.exe`，无需 Python。PowerShell 调用示例：

```powershell
.\NestPack-v1.1.0-windows-cli.exe --source "D:\data" --output "D:\out" --layer rar --yes --non-interactive --json
```

可执行文件路径含空格时用 PowerShell 调用运算符，例如
`& 'D:\NestPack Tools\NestPack-v1.1.0-windows-cli.exe' --help`。为任务路径加引号；
密码可用 `--layer-password-file` 或解包的 `--password-file` 传入。

## 平台差异（win32）

- 自动检测 WinRAR.exe/Rar.exe（dependencies → PATH → 注册表 → ProgramFiles）。
- 7z / zip 层先按同序查找 7z.exe / 7za.exe / 7zz.exe；7z 请求在完整工具
  缺失时再查找 7zr.exe。含 ZIP 层的压缩任务在规划时要求完整工具，解包在
  识别到 ZIP 层时校验工具能力。`--install-tools` 或 `scripts/fetch_tools.py`
  会装 7zr.exe（仅 .7z）与支持 -tzip 的 7za.exe。
- `show_winrar_gui: false` 时追加 `-ibck` 切后台。

## 归档工具安装与路径

```powershell
.\NestPack-v1.1.0-windows-cli.exe --install-tools 7z --non-interactive --json
.\NestPack-v1.1.0-windows-cli.exe --install-tools rar --non-interactive --json
```

7-Zip 从官方来源下载并校验 SHA256，程序与许可材料安装到 exe 同目录的
`dependencies/7z`；源码运行时位于项目根。RAR 命令返回官网安装指引，
`manual_install: ["rar"]` 表示还需用户自行安装；再次执行同一命令不会自动安装 RAR。
明确工具位置后使用 `--rar-path` / `--sevenzip-path`，或配置对应字段。

配置中的本机路径按配置目录解析，命令行指定的路径按调用目录解析。
从 Linux 迁移任务时需更新来源、输出、工具、载体和自解压素材路径。
默认配置为程序目录下的 `nestpack_config.json`；日志位于
`%LOCALAPPDATA%\NestPack\logs\nestpack.log`。

实现依据：`platforms/win32/detection.py`、`platforms/tools.py`、
`platforms/tool_installer.py`、`core/logging_utils.py`。
