# 一键解包参考（跨平台，`core/unpack/`）

## CLI 用法

```bash
python3 -m cli --unpack ./out/outer.7z --password-file ./passwords.txt --output ./restored --non-interactive --json
```

Windows 源码将 `python3` 换成 `python`；发布程序使用对应 CLI 入口。
`--password VALUE` 可重复提供候选，`--password-file` 为可选的候选列表文件。
`--output` 为目录，缺省在归档旁生成 `归档主名_unpacked`。
解包可搭配 `--config`、工具路径与 `--layers N`；`--dry-run` 和压缩设置属于压缩模式。

- 密码可乱序、每层自动尝试；`--password-file` 每行一个，调用 NestPack
  时只需传入文件路径；文件使用 UTF-8（可带 BOM），保留密码首尾空格。实际解压仍通过归档工具的命令行传递密码。
  每层实际尝试顺序为：无密码探针 → 已成功密码 →
  `--password` → `--password-file` → `--config` 指定的配置文件（或默认配置文件）
  里各层已保存的密码。
- `--non-interactive` 在候选全部失败后直接报错；交互调用逐层补问；终端中隐藏输入，stdin 重定向时读取一行，
  空输入或输入流结束表示放弃。
- `--json`：结束时 stdout 输出单个 JSON 对象（成功为
  `{"tool":"nestpack","schema_version":1,"status":"ok","mode":"unpack",
  "output_dir":"...","entries":["..."]}`，失败为
  `{"tool":"nestpack","schema_version":1,"status":"error",
  "error_kind":"...","error":"..."}`），进度与 rar 输出走 stderr；
   退出码不变。压缩包不存在时 `error_kind` 为 `input_not_found`；
   完整 schema 与 error_kind 枚举见 [cli.md](cli.md) 的「结果 schema」段。
- 解包专用参数（--password/--password-file/--layers）在压缩模式下会报
  用法错误（退出码 2），不会被静默忽略。

## 解包行为

- 按文件头识别格式（RAR / 7z / ZIP；.bin 等伪装扩展名无需改回），
  每层遇到 NestPack 融合 MP4 会先提取并校验原归档，再按原层数逐层解包；
  每层自动选用对应工具（zip 层与 7z 层共用 7-Zip 命令行）；
  分卷从第 1 卷开始。
- 标准首卷为 `名称.part1.rar`、`名称.7z.001` 或 `名称.zip.001`，整套放在
  同一目录。Windows / Linux RAR 自解压也按内容读取，首卷可为
  `名称.part1.exe` / `名称.part1.sfx`，后续为 `.rar`；解包不执行 SFX 或 Setup。
- 伪装扩展名的分卷套（`set.part1.bin`… / `set.bin.001`…，
  各层“修改扩展名 + 分卷”组合的产物）自动识别：在工作目录以硬链接接出
  标准 `.partN.rar` / `.7z.001` / `.zip.001` 卷名再解，原文件不动，
  无需手动改名。
- 逐层解出「单个压缩包或从 1 起连续编号的分卷套」→ 继续解下一层，
  其余内容即最终载荷；`--layers N` 是最大解包层数，N 为不小于 1 的整数，
  先遇到最终载荷时提前结束。载荷本身是归档时用此参数避免多解一层，
  每层提取融合 MP4 不额外计数。每次密码尝试失败会清掉该层半解出的残留再重试。
- RAR 退出码自动翻译（rc=11 密码错误、rc=3 CRC 损坏等），7z/zip 使用
  7-Zip 的退出码表；各格式表见 `core/backends/rar.py` 与 `core/backends/sevenzip.py`。
- 工作目录 `<输出>/.nestpack_unpack_tmp`：成功即删，失败保留供手动续解；
  同一输出目录重跑会清空上次工作目录，需手动续解时先处理保留内容。
  12 位十六进制名的 `.dat` 填充文件自动清理，并兼容 `stack_pad_` 加
  8 位十六进制名的 `.bin` 填充文件；输出目录同名文件冲突时报错不覆盖。

## 无人值守注意

使用 `--non-interactive --json`，提供完整候选密码；该模式不从 stdin 读取
补充密码。未设置此参数的交互调用在 stdin 重定向时逐行读取，EOF 结束补问。
显式 `--config` 缺失或无效会报错；默认配置无效会给出提示并继续使用显式候选
与工具自动检测。`--rar-path`、`--sevenzip-path` 可直接指定工具。

`persist_passwords=false` 保存的配置只有密码标记，不能提供缺失密码；
需使用实际候选列表。隐藏来源名称的归档会解出随机根名称，原名无法恢复。
只需恢复融合前的归档时用 `--extract-video-archive`，见 [video.md](video.md)。

实现依据：`cli/unpack_cmd.py`、`core/unpack/workflow.py`、
`core/unpack/extraction.py`、`core/unpack/content.py`、`core/unpack/volumes.py`。
