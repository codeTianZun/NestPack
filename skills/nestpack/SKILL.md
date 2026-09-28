---
name: nestpack
description: 通过 NestPack 的 Windows 或 Linux CLI 执行多层 RAR/7z/ZIP 压缩与解包、逐层扩展名伪装、MP4 视频融合与原归档提取、RAR 自解压交付。用于 AI 编排任务参数、读写 JSON 配置、预览计划、配置归档工具、解析结果与处理失败。
---

# NestPack

使用 NestPack 的 Linux 或 Windows CLI 执行归档任务。每个任务的压缩层
从内到外排列，下一层包裹上一层的全部产物，包括分卷与伪装后的文件。
合并打包产生一套归档，分别打包为每个来源产生一套。

## 按任务读取

- 执行命令、直接层参数、结果 schema、错误处理：先读 [references/cli.md](references/cli.md)。
- 创建或修改 JSON 配置：读 [references/config.md](references/config.md)。
- 逐层解包、分卷与密码候选：读 [references/unpack.md](references/unpack.md)。
- MP4 载体、逐来源视频、已有归档融合或提取：读 [references/video.md](references/video.md)。
- Windows / Linux 自解压、品牌模板与接收者行为：读 [references/sfx.md](references/sfx.md)。
- 平台入口和工具检测：按需读 [references/windows.md](references/windows.md) 或
  [references/linux.md](references/linux.md)。

只读取当前任务需要的参考。源码命令在 NestPack 项目根目录执行，发布程序
使用其实际路径。参考中的源码路径均相对
项目根。需要核对实现时，对照 `使用说明.md`、`开发文档.md` 和参考所列模块。

## 执行约定

执行任务使用参数入口和 `--non-interactive --json`；需要跳过确认时加 `--yes`。
压缩可直接传 `--source`、`--output` 和重复的 `--layer`，也可使用 `--config`。
压缩执行前用同一任务参数加 `--dry-run` 预览；该参数仅适用于压缩。
正式执行后以成功清单中的 `groups[].final` 作为交付路径，分卷交付整套。
随机层名、分卷数量可能与预览不同。解包读取 `entries`，独立融合或提取读取 `files`。

直接参数以调用目录为路径基准，配置内路径以配置所在目录为基准。
参数覆盖只用于本次运行，显式 `--save-config` 才保存；预览不创建目录或保存文件。
stdout 为任务结果 JSON，stderr 为进度与诊断；帮助、版本和许可查询使用文本输出。

成功压缩清单包含明文密码；向用户汇报时按需要摘取交付路径与状态。
`persist_passwords=false` 只控制保存配置，归档工具执行时仍通过命令行接收密码。
加密任务的密码必须完整；无交互模式不能补问缺失密码。直接层参数可通过
`--layer-password-file` 读取单行密码，解包通过 `--password-file` 读取候选列表。

`delete_inner_after_verify` 依赖 `verify_after_compress`；交替删除只处理本次
生成的中间层。ZIP 文件名公开，ZIP 密码仅支持 ASCII。源名称别名化只改根条目，
解包不会恢复原名。任意层调整扩展名或融合 MP4 后仍可逐层解包。

只处理用户指定的来源与输出。覆盖由任务的 `overwrite_existing` 控制；
`--yes` 只跳过确认。失败后的处理见 CLI 参考，已有输出冲突应先确定交付位置
或用户要求的覆盖策略。

本项目不编写或运行自动化测试；验证使用静态检查和实际需要的人工操作。
