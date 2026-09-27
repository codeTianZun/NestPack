---
name: nestpack
description: Use NestPack on Windows or Linux to create or unpack nested RAR, 7z and ZIP archives, prepare task configuration, preview output paths, install archive tools, or consume CLI JSON results. Covers direct per-layer arguments, reusable JSON configuration, and the human-facing numeric menu.
---

# NestPack

NestPack 支持 Windows CLI / GUI 与 Linux CLI，各层可选择 RAR、7z 或 ZIP。
AI 使用参数入口；无参数启动是面向人类的数字菜单。

## 按任务读取

- 执行命令、直接层参数、结果 schema、错误处理：先读 [references/cli.md](references/cli.md)。
- 创建或修改 JSON 配置：读 [references/config.md](references/config.md)。
- 逐层解包、分卷与密码候选：读 [references/unpack.md](references/unpack.md)。
- 平台入口和工具检测：按需读 [references/windows.md](references/windows.md) 或
  [references/linux.md](references/linux.md)。

## 执行约定

使用 `--non-interactive --json`；需要跳过确认时加 `--yes`。
可以直接传 `--source`、`--output` 和重复的 `--layer`，也可以使用 `--config`。
先用同一任务参数加 `--dry-run` 预览，正式执行后以成功清单中的
`groups[].final` 作为交付路径。随机层名、分卷数量可能与预览不同。

直接参数以调用目录为路径基准，配置内路径以配置所在目录为基准。
参数覆盖只用于本次运行，显式 `--save-config` 才保存；预览不创建目录或保存文件。
stdout 为任务结果 JSON，stderr 为进度与诊断；帮助和版本查询使用文本输出。

成功压缩清单包含明文密码；向用户汇报时按需要摘取交付路径与状态。
`persist_passwords=false` 只控制保存配置，归档工具执行时仍通过命令行接收密码。
加密任务的密码必须完整；无交互模式不能补问缺失密码。直接层参数可通过
`--layer-password-file` 读取单行密码，解包通过 `--password-file` 读取候选列表。

`delete_inner_after_verify` 依赖 `verify_after_compress`；交替删除只处理本次
生成的中间层。ZIP 文件名公开，ZIP 密码仅支持 ASCII。源名称别名化只改根条目，
解包不会恢复原名。最外层调整扩展名后仍可按内容解包。

只处理用户指定的来源与输出。覆盖由任务的 `overwrite_existing` 控制；
`--yes` 只跳过确认。失败后的处理见 CLI 参考，已有输出冲突应先确定交付位置
或用户要求的覆盖策略。

本项目不编写或运行自动化测试；验证使用静态检查和实际需要的人工操作。
