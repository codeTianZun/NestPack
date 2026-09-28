# Linux 平台参考

## CLI 入口

- 发布程序：`./nestpack-linux-cli --config 路径`，首次下载后执行
  `chmod +x nestpack-linux-cli`，无需安装 Python。
- 源码入口：`./platforms/linux/launcher.sh --config 路径` 或
  `python3 -m cli ...`。launcher 将项目根加入 Python 模块路径，保持调用
  目录与参数路径基准。源码运行只需 Python 3.10+ 标准库。
  参数与 JSON 输出契约见 [cli.md](cli.md)，解包见 [unpack.md](unpack.md)。
- 前置依赖：rarlab 官方 `rar` 命令（RAR 层用）；7z / zip 层另需
  7-Zip 官方 `7zz` 或 p7zip 的 `7z`（均支持 -tzip）。
  `python3 -m cli --install-tools` 显示 RAR 官网安装指引，并下载、校验
  7-Zip 到当前程序目录的 `dependencies/7z/`，保留许可材料。

## 平台差异（linux）

- `winrar_path: auto` 按当前程序目录 `dependencies/` → PATH 查 `rar`；
  `sevenzip_path: auto` 同序查 `7zz` / `7z` / `7za`。
- `show_winrar_gui` 在 Linux 忽略；使用 `--json` 时进度与诊断走 stderr。
- 显式工具路径须指向有执行权限的文件；RAR 层使用 `rar`。

## 无交互调用与工具安装

```bash
python3 -m cli --config /data/task.json --dry-run --json
python3 -m cli --config /data/task.json --yes --non-interactive --json
python3 -m cli --install-tools 7z --non-interactive --json
```

仅在需要相应归档工具时安装。7-Zip 下载校验 SHA256 并保留许可材料；
RAR 安装入口提供官网指引，结果中的 `manual_install: ["rar"]` 表示仍需
用户安装，重新调用不会自动装好。发布程序将命令前缀换成 `./nestpack-linux-cli`。

从 Windows 迁移任务时，更新来源、输出、工具、视频及自解压素材的本机路径；
SFX 的接收者解压路径和命令保持目标系统语义，见 [sfx.md](sfx.md)。
默认配置在项目根或发布程序同目录，安装工具写入该目录的 `dependencies/7z`。
日志位于 `$XDG_DATA_HOME/nestpack/logs/nestpack.log`；未设置该变量时使用
`~/.local/share/nestpack/logs/nestpack.log`。

实现依据：`platforms/linux/launcher.sh`、`platforms/linux/detection.py`、
`platforms/tools.py`、`platforms/tool_installer.py`、`core/logging_utils.py`。
