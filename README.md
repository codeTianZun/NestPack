# NestPack 1.0.0

多层嵌套压缩工具：按层调用 WinRAR / rarlab `rar` 或 7-Zip 命令行，支持 RAR、
7z 与 ZIP 混合嵌套；每层可独立加密、分卷，RAR 层还支持恢复记录，并支持随机
填充、源文件名别名化、最外层扩展名调整等隐私与归档选项，可减少归档与传输
过程中不必要的元数据暴露，以及重复归档之间的直接关联。仅提供 Linux CLI、
Windows CLI 与 Windows PySide6 GUI，共用同一份 JSON 配置与同一套 `core/` 逻辑；另有一键解包
（`--unpack`）反向逐层释放原始文件。

请仅处理有权使用的文件，并遵守存储服务条款、适用法律与组织的安全规范。

## 快速开始

支持 Python 3.10+。CLI 仅使用 Python 标准库；第三方归档工具按需安装。
先获取源码并进入项目目录：

~~~bash
git clone https://github.com/codeTianZun/NestPack.git
cd NestPack
~~~

Windows（GUI）：

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\.venv\Scripts\python.exe -m gui
~~~

也可改用 `scripts\windows\install_deps.ps1` 一键装依赖（含 `.venv` 检测
与 `-Dev` 静态检查依赖开关）。Linux CLI 无需安装 Python 运行依赖；
需要静态检查工具时可用 `./scripts/linux/install_deps.sh --dev`。

Windows / Linux（CLI；Linux 将 `python` 换为 `python3`）：

~~~bash
python -m cli                             # 数字菜单：新建、解包、编辑配置、工具安装
python -m cli --source data --output out --layer rar --yes --non-interactive --json
python -m cli --config task.json --dry-run --json
python -m cli --config task.json --yes --non-interactive --json
python -m cli --unpack outer.bin --password-file pw.txt --non-interactive --json
python -m cli --install-tools
~~~

Windows 打包版双击 `nestpack-cli.exe` 即打开菜单。已有配置的来源失效时，
可在菜单中重新选择路径。完整逐层设置同时支持数字交互和直接参数；新任务
按需保存，参数调用使用 `--save-config` 显式保存。所有调用方式见
[使用说明.md](使用说明.md)。

`--install-tools rar` 显示 RARLAB 官网安装指引；`--install-tools 7z`
从官方下载安装 7-Zip 并保留许可材料；省略工具名时执行这两项。
RAR / WinRAR 由用户自行安装和授权，见 [RARLAB 许可条款](https://www.rarlab.com/license.htm)。

退出码约定：0 成功，1 配置/运行错误，2 用法错误，130 用户中止。
智能体使用 `--non-interactive --json` 获得无交互调用与结构化结果；
`--yes` 跳过确认。无终端且无参数启动时显示帮助。

## 文档索引

| 文档 | 内容 |
|---|---|
| [使用说明.md](使用说明.md) | CLI/GUI 用法、JSON 配置字段语义、安全注意事项 |
| [打包说明.md](打包说明.md) | 源码 / Windows exe / Linux 精简包三种分发形态 |
| [开发文档.md](开发文档.md) | 现行架构（core/platforms/cli/gui 分层）、模块职责、设计决策 |
| [skills/nestpack/](skills/nestpack/) | CLI 使用参考：Windows/Linux、配置与解包 |

## 目录结构

~~~text
core/        平台无关核心引擎（仅 Python 标准库）
cli/         命令行入口（python -m cli）
gui/         PySide6 图形界面（仅 Windows 桌面）
platforms/   平台差异、工具检测、RAR 安装指引与 7-Zip 下载/校验/安装
skills/      CLI 使用参考（导航 SKILL.md + references/）
scripts/     Windows exe / Linux CLI 打包与本地依赖安装脚本
~~~

工程配置在 `pyproject.toml`（ruff / mypy），CI 见
`.github/workflows/ci.yml`（仅静态检查）。本项目不编写或运行自动化测试。

## 许可与反馈

Copyright (C) 2026 codeTianZun。项目代码、文档和程序化图形采用
[GPL-3.0-only](LICENSE)，允许按许可条款使用、修改和再分发，不提供担保。
第三方版权与许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
CLI 使用 `--license`、GUI 点击「关于/许可」可查看许可。

问题和建议统一通过 [GitHub Issues](https://github.com/codeTianZun/NestPack/issues)
反馈，注明版本、系统与复现步骤。提交贡献时须有权按项目许可提供相应内容。
Issue、提交和附件中请使用脱敏示例；任务配置、密码清单与私人资料放在仓库外
或已忽略的 `.private/`，自行命名的配置文件需自行检查是否被 Git 跟踪。
