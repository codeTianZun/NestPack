# 配置 JSON 参考（跨平台）

## 执行方式

自动化可直接传来源与逐层参数，见 [cli.md](cli.md)；复用任务时使用
`--config task.json --yes --non-interactive --json`。
配置与密码文件使用 UTF-8（可带 BOM）。

最小配置示例（相对路径以配置文件所在目录为基准）：

```json
{
  "config_version": 1,
  "winrar_path": "auto",
  "source_paths": ["input.txt"],
  "output_directory": "out",
  "overwrite_existing": false,
  "confirm_before_start": false,
  "show_winrar_gui": false,
  "layers": [{
    "archive_name": "outer.rar",
    "format": "rar",
    "password": "",
    "recovery_record": {"enabled": false, "percent": 3}
  }]
}
```

`recovery_record` 对所有格式都是必填对象，关闭时也要提供 `enabled: false`。
省略 `percent` 时取 3，提供时即使关闭恢复记录也必须是 1–100 的整数。
布尔字段使用 JSON 的 true / false，级别、比例等数值按字段类型填写。
CLI 读取配置后应用本次参数覆盖；`--source` 替换来源列表，`--layer` 替换
整个层列表，其它明确给出的设置覆盖同名字段。`--save-config` 显式保存，
密码持久化由 `persist_passwords` 控制；否则本次参数与随机层名不写回。
`--save-config` 保存后继续执行压缩；仅生成配置时直接写 JSON。

`password_set=true` 且密码为空时，交互运行会补问（空输入表示本层不加密）；
`--non-interactive` 会直接报配置错误。预览无需补问密码：
`--config task.json --dry-run --json`。计划与成功清单结构见 [cli.md](cli.md)。

## 字段总览

必填：`config_version`（1）、`winrar_path`（auto 或可执行文件路径；
仅在存在 RAR 层时解析）、`source_path`（或 `source_paths`）、
`output_directory`、`overwrite_existing`、`confirm_before_start`、`layers`（至少 1 项）。

可选：`sevenzip_path`（默认 auto，语义同 winrar_path，仅在存在 7z /
zip 层时解析；7z 家族工具可用 7z.exe / 7za.exe / 7zr.exe / 7zz / 7z，
其中 7zr 只认 .7z，创建 zip 需要 7za / 7z / 7zz）。
`show_winrar_gui` 可省略，默认为 true，控制 Windows 的 WinRAR 压缩界面。

多来源打包：

- `source_paths`：来源数组，可含多个文件或文件夹；空时回退到
  `source_path`（旧配置兼容）。多个来源名称不能重复（不区分大小写）。
- `compress_mode`：`"combined"`（默认，全部来源合并压成一个压缩包）
  或 `"separate"`（每个来源分别压成自己的一套，输出目录下按 `Path.stem`
  即去掉最后后缀的来源名分目录，最多并行 3 个任务）。separate 模式的来源
  主名也不能重复，例如 `a.txt` 和 `a.pdf` 会冲突。

任务级 `source_layers` 是「来源路径 → 完整层数组」映射，缺省 `{}`。
分别打包时，有独立层的来源使用自己的层数、名称、格式和密码等参数；其余来源
共用 `layers` 并按 `来源主名_当前层号.格式后缀` 命名。移除对应项恢复共用默认。
路径键按配置目录解析，合并打包使用 `layers`。

每层（`layers[]` 或 `source_layers` 中的层数组）：

- `disguise`：逐层伪装对象，缺省为 `{"mode":"none","extension":".bin","video_path":"","source_video_paths":{}}`。
  mode 可选 none / extension / video。extension 为以点开头的 1–8 位字母数字。
  video_path 是本层默认载体，source_video_paths 按来源覆盖本层载体，合并打包使用默认值。
  视频层使用完整单文件归档，volume_size 为 null、sfx.enabled 为 false。
  下一层打包本层伪装后的全部产物。载体映射与完整示例见 [video.md](video.md)。
- `format`：`"rar"`（缺省）、`"7z"` 或 `"zip"`；逐层独立、允许混合
  嵌套（RAR 套 7z 套 zip 等）。7z 层密码用 `-p + -mhe=on`（全加密头，
  等价 -hp）；zip 层由 7-Zip 以 `-tzip` 创建，密码用 `-p` +
  `-mem=AES256`（AES-256），**文件名不加密**（ZIP 格式无头加密）。
- `archive_name`：本层手动文件名；默认层用于合并打包，来源独立层用于对应来源。后缀按 format 或 SFX 目标补全。
- `auto_name`：缺省 false；为 true 时，按当前来源主名与层号生成名称，合并任务使用首来源。
- `sfx`：缺省关闭。`enabled: true` 仅适用于 RAR；`target` 为 windows / linux，
  默认 windows，输出后缀为 .exe / .sfx。`template_path` 默认 auto，可填官方
  模块或品牌样包；`icon_path`、`logo_path`、`title`、`text`、`extract_path`、
  `setup` 默认空。`overwrite` 默认为 ask，可选 overwrite / skip；`silent`
  默认 show，可选 hide_start / hide_all。Linux 原生目标只设置目标与模板。
  模板和图片路径按配置目录解析；解压路径和启动命令保持原文。
  品牌模板工作流、约束和直接参数见 [sfx.md](sfx.md)。
- `password`：密码；空串不设密码（rar `-hp` / 7z `-mhe=on` 同时加密
  文件名）。**zip 层密码仅支持 ASCII 字符**（7-Zip 限制，非 ASCII
  密码在加载配置时报 ConfigError）。所有格式的压缩密码均不能以 `-` 开头。
- `password_set`：该层本应设密码的标记；`persist_passwords=false` 时
  密码不落盘只留标记，CLI 据此补问。缺省按 password 是否非空推断。
- `recovery_record.enabled / percent`：恢复记录，percent 1-100；
  **仅 rar 层可用**，7z / zip 层开启会在加载配置时报 ConfigError。
- `compression_level`：`"auto"`（默认）或 0-5 整数。
  auto 语义：第 1 层探测内容可压缩性（可压最高档，不可压仅存储），
  第 2 层起输入是上一层的压缩包，一律仅存储。rar 映射 -m0..-m5，
  7z / zip 映射 -mx0/1/3/5/7/9。
- `volume_size`：分卷大小（各格式均使用对应工具的 `-v`），如 `500k`/`100m`/`1g`；
  null 不分卷。分卷层输出：rar 为 `名.partN.rar`、7z 为 `名.7z.001`、
  zip 为 `名.zip.001`；外层包裹全部分卷，交替删除整层全删，伪装对
  每卷改扩展名并保留卷号。

顶层隐私与归档开关为布尔值；`verify_after_compress`、
`delete_inner_after_verify` 与 `persist_passwords` 缺省 true，其余缺省 false：

- `add_padding`：每层加入 16KiB~1MiB 的随机填充文件，使每次归档的
  内容与体积特征随之变化。
- `randomize_layer_names`：开始压缩时覆盖当前模式的名称，生成 8 位字母数字主名；
  分别打包为每个来源的每层独立生成，合并打包为每层生成一个。
  CLI 显式保存配置时才落盘，预览使用当前名称并保留此标记。
- `hide_source_name`：第 1 层用随机别名打包（文件硬链接/文件夹复制），
  隐藏根条目原名；内部文件名不变。解包后根条目是别名，原名不可恢复。
- `randomize_timestamps`：随机化最外层修改时间。
- `verify_after_compress`：每层后运行 t 自检，失败保留旧包。
- `cleanup_on_failure`：任务失败或取消时删除该任务本次已生成的层产物；
  分别打包时保留其他已完成任务的产物。
- `persist_passwords`：false 时由 CLI 保存配置将密码写空并保留 password_set，
  执行仍使用本次完整密码；AI 直接写 JSON 时也应按此字段决定是否写入密码。
- `delete_inner_after_verify`：交替删除——每层自检通过后删除上一层，
  只保留最外层，省磁盘；启用时必须同时开启 `verify_after_compress`。

旧 v1 顶层 `disguise_outer_extension`、`disguise_extension`、`video_fusion`、
`video_path`、`source_video_paths` 在加载时迁入最外层，显式逐层 `disguise`
优先；两种旧方式同时启用时视频优先。保存和新建配置统一写逐层结构。

相对路径以 JSON 配置文件所在目录为基准。
视频路径与来源覆盖表的键和值同样以该目录为基准。融合成品使用 `.mp4`
后缀，原归档格式及密码保持原有层设置。

## 推荐组合

- 隐私保护归档（按需使用）：`add_padding` + `randomize_layer_names` +
  `hide_source_name`，需要伪装的层设置 `disguise.mode=extension`，每层设密码。
- 归档省磁盘：`verify_after_compress` + `delete_inner_after_verify`。
- 大体积已压缩源（视频/镜像）：`compression_level` 用 auto 或 0，
  避免高档重复压缩耗时。
- 单文件限额：在需要交付分卷的层设置 `volume_size`，该层使用原扩展名或
  扩展名伪装；视频层保持单文件。

规划会检查来源、各层产物以及视频与自解压素材的路径冲突，包括调整后扩展名
导致的重名；每层使用不同主名，并按 `--dry-run` 的路径和提示修正。
磁盘估算只是提醒，复制来源、保留中间层及多层视频会增加占用。

实现依据：`core/models.py`、`core/config/schema.py`、`core/config/validation.py`、
`core/config/naming.py`、`core/compression/planning.py`、`cli/configuration.py`。
