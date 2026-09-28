# CLI 参数、结果与失败处理

## 入口与调用

源码在项目根运行 `python -m cli`（Linux 为 `python3`）；Windows 发布程序
使用 `nestpack-cli.exe`，Linux 发布程序使用 `nestpack-linux-cli`。
Linux 源码也可从任意目录调用 `platforms/linux/launcher.sh`，
它保持调用目录，参数相对路径按该目录解析。

使用显式任务参数和 `--non-interactive --json`；`--yes` 跳过确认，
它与产物覆盖策略分别控制。无参数、`--menu` 和 `--init` 是交互入口；
无参数且无终端时仅显示帮助，不执行任务。

## 按任务选择模式

| 任务 | 参数 / 操作 | 产物字段 |
|---|---|---|
| 生成配置文件 | 按 [config.md](config.md) 写 UTF-8 JSON | 配置文件路径 |
| 预览压缩 | 压缩参数加 `--dry-run`，自身即输出 JSON | `status=plan`，`groups[].final` 为预期路径 |
| 执行压缩 | `--source` / `--output` / `--layer`，或 `--config` | `groups[].final` |
| 逐层解包 | `--unpack`，见 [unpack.md](unpack.md) | `entries` |
| 已有归档融合 / 原归档提取 | `--fuse-archive` / `--extract-video-archive`，见 [video.md](video.md) | `files` |
| 归档工具安装 | `--install-tools [rar\|7z\|all]` | `tools`、`manual_install` |

`--dry-run` 仅用于压缩。解包、工具安装、独立融合、提取各为独立模式，
不能与压缩层参数混用；`--password`、`--password-file`、`--layers` 专用于解包。
`--help`、`--version`、`--license` 为文本查询，即使带 `--json` 也不返回任务 JSON。

## 压缩调用

最小直接压缩：

```bash
python3 -m cli --source /data/input --output /data/out --layer rar --yes --non-interactive --json
```

多层混合压缩（层顺序从内到外，层设置属于最近的 `--layer`）：

```bash
python3 -m cli --source /data/input --output /data/out --layer rar --layer-name inner --layer-password-file /private/inner.txt --layer 7z --layer-name outer --layer-password-file /private/outer.txt --layer-volume-size 100m --yes --non-interactive --json
```

预览：在同一组参数后加 `--dry-run`；复用配置时：

```bash
python3 -m cli --config /data/task.json --dry-run --json
python3 -m cli --config /data/task.json --yes --non-interactive --json
```

不要从预览推断完整分卷数或实际随机名称，成功结果提供最终文件。
预览检查配置、工具、来源、层名和已有目标冲突，不创建输出目录、不写配置，
也不补问密码。缺少密码的计划可预览，正式执行仍需完整密码。

## 参数分组

| 参数 | 语义 |
|---|---|
| `--source PATH` | 可重复；替换整个来源列表 |
| `--output PATH` | 本次输出目录 |
| `--compress-mode combined\|separate` | 合并或分别打包 |
| `--layer rar\|7z\|zip` | 添加一层；提供时替换配置的整个层列表 |
| `--layer-name NAME` | 本层合并打包文件名，自动补后缀，并关闭合并名称的自动生成 |
| `--layer-password VALUE` | 本层密码，空串不加密 |
| `--layer-password-file PATH` | UTF-8 单行密码，可有一个末尾换行，保留首尾空格；与本层直接密码互斥 |
| `--layer-level auto\|0..5` | 本层压缩级别 |
| `--layer-volume-size 100m` | 本层分卷大小 |
| `--layer-disguise none\|extension\|video` | 本层伪装方式，显式方式优先 |
| `--layer-disguise-extension .bin` | 本层扩展名，并启用扩展名伪装 |
| `--layer-video MP4` | 本层默认载体，并启用视频伪装 |
| `--layer-source-video SOURCE MP4` | 本层来源专用载体，并启用视频伪装，可重复 |
| `--layer-recovery 1..100` | RAR 恢复记录比例 |
| `--layer-sfx windows\|linux` | 启用本 RAR 层自解压；模板、品牌、脚本等参数见 [sfx.md](sfx.md) |
| `--rar-path` / `--sevenzip-path` | 工具路径或 auto，压缩和解包都可用 |
| `--save-config PATH` | 压缩前保存本次配置，配置中的本机路径固定为绝对路径，按 persist_passwords 决定密码落盘 |
| `--disguise-extension .bin` | 指定并启用最外层扩展名调整，显式布尔参数优先 |
| `--video MP4` | 设置默认载体并启用最外层视频融合 |
| `--source-video SOURCE MP4` | 最外层按来源选择视频并启用视频融合，可重复 |
| `--video-fusion` / `--no-video-fusion` | 显式启用或停用最外层视频融合 |

直接创建任务需来源与输出，省略层参数时使用一层 RAR。直接任务的覆盖和
运行前确认默认关闭，WinRAR 界面默认关闭；自检、删除中间层、保存配置时
保留密码默认开启。其它缺省与配置参考一致。
所有 `--layer-*` 参数都需要前面的 `--layer`，不能单独修改配置中的某一层。
提供 `--layer` 就替换整个层列表，需完整重述要保留的层及设置；仅改已有配置
中的单层时可编辑 JSON。含空格的参数值加引号，以连字符开头的普通值使用
`--参数=值`；压缩密码本身不允许以 `-` 开头。

全部顶层布尔设置均可用连字符参数及对应 `--no-...` 设置：
`overwrite-existing`、`confirm-before-start`、`show-winrar-gui`、`add-padding`、
`randomize-layer-names`、`hide-source-name`、`disguise-outer-extension`、
`randomize-timestamps`、`verify-after-compress`、`cleanup-on-failure`、
`persist-passwords`、`delete-inner-after-verify`。
关闭自检须同时关闭删除中间层，即
`--no-verify-after-compress --no-delete-inner-after-verify`。

任务级视频和扩展名参数在逐层参数之后应用到最外层。显式布尔参数覆盖各自
快捷参数的启用状态；两种方式同时启用时视频优先。使用逐层参数时，
显式 `--layer-disguise` 优先于该层扩展名和视频参数的隐式启用。
视频层输出、来源载体映射与独立处理见 [video.md](video.md)。

配置中的路径以配置文件目录为基准；命令行明确提供的路径按调用目录解析。
参数覆盖与随机层名只影响本次任务，只有 `--save-config` 才写配置；dry-run
不保存。另存配置使用绝对路径，避免移动配置后改变来源位置。
`--save-config` 会在确认后、压缩开始前保存并继续压缩，不是仅保存命令；
压缩失败时配置可能已经写入。只需生成配置时直接写 JSON。
目标配置已存在且不同于输入配置时，`--yes` 也会确认替换配置；
归档覆盖仍由 `overwrite_existing` 控制。

既未指定 `--source` 也未指定 `--config` 的压缩参数调用读取项目根或发布程序同目录的
`nestpack_config.json`；新任务显式提供来源和输出可避免使用默认配置。

`--install-tools [rar|7z|all]` 显示 RAR 官网安装指引或安装 7-Zip，支持
`--json`；`manual_install: ["rar"]` 表示仍需用户自行安装 RAR。7-Zip
及许可材料安装到程序同目录的 dependencies/7z。

## 结果 schema（schema_version = 1）

所有任务结果包含 `tool: "nestpack"`、`schema_version: 1`、`status`。
将 stdout 作为一个 JSON 对象解析，stderr 仅用于诊断。

压缩成功例：

```json
{
  "tool": "nestpack",
  "schema_version": 1,
  "status": "ok",
  "mode": "compress",
  "compress_mode": "combined",
  "delete_inner_after_verify": true,
  "warnings": [],
  "groups": [{
    "source": "",
    "layers": [{
      "name": "outer.rar",
      "format": "rar",
      "disguise_mode": "none",
      "files": ["/data/out/outer.rar"],
      "password": "example-password",
      "recovery_percent": null,
      "volume_size": null,
      "video_path": null,
      "sfx_target": null
    }],
    "final": ["/data/out/outer.rar"]
  }]
}
```

`groups` 按任务顺序排列，`layers` 从内到外。多个任务时 `source` 为该任务
来源路径，只有一个任务时为空串。`layers[].files` 保留各层产物记录，已删除
的中间层也在其中；`final` 才是交付文件。密码字段是明文。

计划使用 `status: "plan"`、`mode: "compress"`，顶层还包含：
`config_path`（直接任务为 null）、`sources`、`output_directory`、`winrar`、
`sevenzip`（未用的工具为 null）、`overwrite_existing`、
`delete_inner_after_verify`、`disguise_outer_extension`、`randomize_layer_names`、
`compress_mode`、`warnings`、`groups`。层结构为 `name`、`format`、
`expected_files`、`password_set`、`recovery_percent`、`compression_level`、
`volume_size`；分卷仅列首卷，密码只提供标记。
计划顶层的 `video_fusion` 和 `disguise_outer_extension` 表示最外层方式；
各层另有 `disguise_mode`，`video_path` 为实际载体
绝对路径，普通层为 null；成品路径在 `final` 与 `expected_files` 中展示。
层记录还含 `sfx_target`（windows / linux / null）；自解压的 format 仍为 rar。
计划的层记录另含 `sfx_template`（实际模板绝对路径或 null）、`sfx_setup_set`（布尔）。

解包成功：`status: "ok"`、`mode: "unpack"`、`output_dir` 和 `entries` 数组。
初始化成功：`mode: "init"`、`config_path`。安装成功：`mode: "install"`、
`tools`（rar / 7z / all）、`manual_install`（需要用户安装的工具列表）。
独立融合 / 提取成功：`mode: "video_fusion"` / `"video_extract"`、`files`。
这些结果均有统一顶层字段。

失败例：

```json
{"tool":"nestpack","schema_version":1,"status":"error","error_kind":"usage_error","error":"--password、--password-file 和 --layers 仅用于 --unpack"}
```

| error_kind | 退出码 | 处理 |
|---|---|---|
| `usage_error` | 2 | 修正参数值、层参数顺序或互斥组合 |
| `config_error` | 1 | 按 error 修正字段、路径、UTF-8 编码、工具或补齐密码；需要确认时加 --yes |
| `not_found` / `input_not_found` | 1 | 核实路径，解包分卷使用首卷 |
| `io_error` | 1 | 根据具体原因处理目录、权限或磁盘问题 |
| `runtime_error` | 1 | 查看 error 与 stderr；已有输出选择新位置或按用户要求覆盖，密码/损坏问题核实候选和文件完整性 |
| `cancelled` | 130 | 操作已取消，汇报当前状态 |
| `unknown` | 1 | 意外异常，保留诊断供排查 |

成功退出码为 0。参数确认被拒绝和 Ctrl+C 均返回 130，JSON 状态与退出码一致。
分别打包失败时，已经完成的其它任务产物仍可能存在；错误结果不提供完整的
部分成功清单，重试前查看输出目录。解包失败工作目录保留，但同目录重跑会
清空该现场；需手动恢复时先处理保留的内容。

读取退出码、`status` 与产物字段后再报告完成；`status=plan` 仅表示预览。
重试前按错误修改输入、配置或环境；缺失密码、工具或文件等信息时向用户补齐。
实现依据：`cli/args.py`、`cli/configuration.py`、`cli/compress_cmd.py`、
`cli/main.py`、`cli/display.py`、`core/result_summary.py`。
