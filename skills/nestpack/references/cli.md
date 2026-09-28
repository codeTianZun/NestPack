# CLI 参数、结果与失败处理

## 入口与调用

源码在项目根运行 `python -m cli`（Linux 为 `python3`）；Windows 发布程序
使用 `nestpack-cli.exe`，Linux 发布程序使用 `nestpack-linux-cli`。
Linux 源码也可从任意目录调用 `platforms/linux/launcher.sh`，
它保持调用目录，参数相对路径按该目录解析。

无参数或 `--menu` 打开数字菜单，适合人类操作；无参数且无终端时显示帮助。
AI 直接调用参数入口，使用 `--non-interactive --json`；`--yes` 跳过确认，
它与产物覆盖策略分别控制。

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
| `--layer-name NAME` | 本层固定文件名，自动补后缀；自定义后清除默认层名模板 |
| `--layer-name-template TEMPLATE` | 分别打包用的模板，如 `{stem}_1`，优先于固定名 |
| `--layer-password VALUE` | 本层密码，空串不加密 |
| `--layer-password-file PATH` | UTF-8 单行密码，可有一个末尾换行，保留首尾空格；与本层直接密码互斥 |
| `--layer-level auto\|0..5` | 本层压缩级别 |
| `--layer-volume-size 100m` | 本层分卷大小 |
| `--layer-recovery 1..100` | RAR 恢复记录比例 |
| `--rar-path` / `--sevenzip-path` | 工具路径或 auto，压缩和解包都可用 |
| `--save-config PATH` | 保存本次配置，使用绝对路径，按 persist_passwords 决定密码落盘 |
| `--disguise-extension .bin` | 指定并启用最外层扩展名调整，显式布尔参数优先 |
| `--video MP4` | 设置默认载体并启用最外层视频融合 |
| `--source-video SOURCE MP4` | 分别打包时覆盖指定来源的载体，可重复 |
| `--video-fusion` / `--no-video-fusion` | 显式启用或停用本次视频融合 |

直接创建任务需来源与输出，省略层参数时使用一层 RAR。直接任务的覆盖和
运行前确认默认关闭，WinRAR 界面默认关闭；自检、删除中间层、保存配置时
保留密码默认开启。其它缺省与配置参考一致。

全部顶层布尔设置均可用连字符参数及对应 `--no-...` 设置：
`overwrite-existing`、`confirm-before-start`、`show-winrar-gui`、`add-padding`、
`randomize-layer-names`、`hide-source-name`、`disguise-outer-extension`、
`randomize-timestamps`、`verify-after-compress`、`cleanup-on-failure`、
`persist-passwords`、`delete-inner-after-verify`。

视频融合生成单个 `.mp4` 最外层成品；内部层可以分卷。已有单文件归档可
使用 `--fuse-archive archive --video carrier.mp4 --output out` 独立融合；
`--extract-video-archive fused.mp4 --output out` 提取原始归档。
两种独立模式的 `--output` 是目录，`--overwrite-existing` 控制同名覆盖，
`--json` 成功结果的 `mode` 分别为 `video_fusion` / `video_extract`，
`files` 为产物路径列表。`--unpack fused.mp4` 直接解开融合视频内的归档。

配置中的路径以配置文件目录为基准；命令行明确提供的路径按调用目录解析。
参数覆盖与随机层名只影响本次任务，只有 `--save-config` 才写配置；dry-run
不保存。另存配置使用绝对路径，避免移动配置后改变来源位置。

`--install-tools [rar|7z|all]` 显示 RAR 官网安装指引或安装 7-Zip，支持
`--json`；`manual_install: ["rar"]` 表示仍需用户自行安装 RAR。7-Zip
及许可材料安装到程序同目录的 dependencies/7z。
`--init` 交互创建配置并退出；自动化通过直接参数和 `--save-config` 保存。
完整参数可查询 `--help`；`--version` 显示版本。这两种查询保持文本输出。

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
      "files": ["/data/out/outer.rar"],
      "password": "example-password",
      "recovery_percent": null,
      "volume_size": null,
      "video_path": null
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
融合任务的计划顶层另有 `video_fusion`，各层的 `video_path` 为实际载体
绝对路径，普通层为 null；成品路径在 `final` 与 `expected_files` 中展示。

解包成功：`status: "ok"`、`mode: "unpack"`、`output_dir` 和 `entries` 数组。
初始化成功：`mode: "init"`、`config_path`。安装成功：`mode: "install"`、
`tools`（rar / 7z / all）。这些结果均有统一顶层字段。

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
