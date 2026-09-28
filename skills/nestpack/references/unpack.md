# 一键解包参考（跨平台，`core/unpack/`）

## CLI 用法

~~~bash
python -m cli --unpack 最外层文件 [--password 密码 ...] [--password-file 文件] [--layers N] [--output 目录] [--non-interactive] [--json]
~~~

（Linux 为 `python3 -m cli ...`）

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
   完整 schema 与 error_kind 枚举见 `cli.md` 的「结果 schema」段。
- 解包专用参数（--password/--password-file/--layers）在压缩模式下会报
  用法错误（退出码 2），不会被静默忽略。
- GUI 入口：主界面「解包…」按钮（仅 Windows，见 `windows.md`）。

## 解包行为

- 按文件头识别格式（RAR / 7z / ZIP；.bin 等伪装扩展名无需改回），
  NestPack 融合 MP4 会先提取并校验原归档，再按原层数逐层解包；
  每层自动选用对应工具（zip 层与 7z 层共用 7-Zip 命令行）；
  分卷从第 1 卷开始。
- 伪装扩展名的分卷套（`set.part1.bin`… / `set.bin.001`…，
  "最外层伪装 + 分卷"组合的产物）自动识别：在工作目录以硬链接接出
  标准 `.partN.rar` / `.7z.001` / `.zip.001` 卷名再解，原文件不动，
  无需手动改名。
- 逐层解出「单个压缩包或从 1 起连续编号的分卷套」→ 继续解下一层，
  其余内容即最终载荷；`--layers N` 可强制层数（载荷本身是压缩包时
  防多解）。
- **解密命令必须始终带 `-p`**：加密包不带 -p 会弹密码对话框卡死
  （WinRAR.exe 实测），错误密码在 RAR 中通常为 rc=11，在 7z/zip 中由
  7-Zip 返回对应的错误码。每次尝试失败会先清掉该层半解出的残留文件再试下一个密码。
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
