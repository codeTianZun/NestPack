# 配置 JSON 参考（跨平台）

## 执行方式

自动化可直接传来源与逐层参数，见 [cli.md](cli.md)；复用任务时使用
`--config task.json --yes --non-interactive --json`。无参数入口是数字菜单。
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
CLI 读取配置后应用本次参数覆盖；`--source` 替换来源列表，`--layer` 替换
整个层列表，其它明确给出的设置覆盖同名字段。`--save-config` 显式保存，
密码持久化由 `persist_passwords` 控制；否则本次参数与随机层名不写回。

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
  或 `"separate"`（每个来源分别压成自己的压缩包，输出目录下按来源名
  分目录）。

每层（`layers[]`）：

- `format`：`"rar"`（缺省）、`"7z"` 或 `"zip"`；逐层独立、允许混合
  嵌套（RAR 套 7z 套 zip 等）。7z 层密码用 `-p + -mhe=on`（全加密头，
  等价 -hp）；zip 层由 7-Zip 以 `-tzip` 创建，密码用 `-p` +
  `-mem=AES256`（AES-256），**文件名不加密**（ZIP 格式无头加密）。
- `archive_name`：输出文件名，扩展名按 format 补全（.rar / .7z / .zip）。
- `name_template`：分别打包时按来源展开的模板，如 `{stem}_1`，优先于固定文件名；固定自定义名称使用 null。
- `password`：密码；空串不设密码（rar `-hp` / 7z `-mhe=on` 同时加密
  文件名）。**zip 层密码仅支持 ASCII 字符**（7-Zip 限制，非 ASCII
  密码在加载配置时报 ConfigError）。
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

顶层隐私与归档开关为布尔值（`disguise_extension` 为字符串）；`verify_after_compress`、
`delete_inner_after_verify` 与 `persist_passwords` 缺省 true，其余缺省 false：

- `add_padding`：每层加入 16KiB~1MiB 的随机填充文件，使每次归档的
  内容与体积特征随之变化。
- `randomize_layer_names`：开始压缩时生成 8 位随机文件名；CLI 显式保存配置时才落盘。
- `hide_source_name`：第 1 层用随机别名打包（文件硬链接/文件夹复制），
  隐藏根条目原名；内部文件名不变。解包后根条目是别名，原名不可恢复。
- `disguise_outer_extension`：把最外层压缩包改为 `disguise_extension` 指定的扩展名。
- `disguise_extension`：字符串，默认 `.bin`，以点开头的 1–8 位字母数字。
- `randomize_timestamps`：随机化最外层修改时间。
- `verify_after_compress`：每层后运行 t 自检，失败保留旧包。
- `cleanup_on_failure`：任务失败或取消时删除该任务本次已生成的层产物；
  分别打包时保留其他已完成任务的产物。
- `persist_passwords`：false 时保存配置密码写空，运行时用界面/输入值。
- `delete_inner_after_verify`：交替删除——每层自检通过后删除上一层，
  只保留最外层，省磁盘。

相对路径以 JSON 配置文件所在目录为基准。

## 推荐组合

- 隐私保护归档（按需使用）：`add_padding` + `randomize_layer_names` +
  `hide_source_name` + `disguise_outer_extension`，每层设密码。
- 归档省磁盘：`verify_after_compress` + `delete_inner_after_verify`。
- 大体积已压缩源（视频/镜像）：`compression_level` 用 auto 或 0，
  别用 -m5 烧 CPU。
- 网盘单文件限额：给最外层（或任意层）设 `volume_size`。
