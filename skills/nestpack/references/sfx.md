# RAR 自解压与品牌交付

## 制作端与接收者

任意 RAR 层可启用自解压。`target` 指接收者系统，Windows 输出 `.exe`，
Linux 输出终端用 `.sfx`；制作端可以不同，例如 Linux 服务器生成 Windows EXE。
模板的可执行格式和 CPU 架构须适合接收者。

`template_path` 可以是官方模块或已有品牌样包。NestPack 只复用样包的
可执行模块及品牌资源，本次文件、密码与说明脚本由当前任务生成。
模板可执行前缀最多 1 MiB；该限制不针对品牌样包中原有归档内容的大小。

## 字段与直接层参数

以下 JSON 字段位于 `layers[].sfx`，缺省关闭。任何 `--layer-sfx-*` 参数都会
启用当前层自解压，目标缺省为 windows；所有层参数必须跟在所属 `--layer rar` 后。

| JSON 字段 | 默认值 / 取值 | CLI 参数 |
|---|---|---|
| `enabled` / `target` | false / windows；windows 或 linux | `--layer-sfx windows` / `linux` |
| `template_path` | auto；官方模块或品牌样包路径 | `--layer-sfx-template PATH` |
| `icon_path` | 空；ICO | `--layer-sfx-icon PATH` |
| `logo_path` | 空；PNG / BMP | `--layer-sfx-logo PATH` |
| `title` / `text` | 空；标题 / 多行说明 | `--layer-sfx-title` / `--layer-sfx-text` |
| `extract_path` / `setup` | 空；接收者解压路径 / 本层成功解压后执行的命令 | `--layer-sfx-path` / `--layer-sfx-setup` |
| `overwrite` | ask；ask / overwrite / skip | `--layer-sfx-overwrite` |
| `silent` | show；show / hide_start / hide_all | `--layer-sfx-silent` |

模板和图片属于制作端路径：配置相对配置目录，CLI 显式值相对调用目录。
`extract_path` 和 `setup` 属于接收者环境，保存与另存时保持原文。
标题、解压路径和命令为单行且不含控制字符；说明允许换行和制表符，
每行去掉前置空白后不能以 `}` 开头，这是 RAR 的文本块结束符。

`auto` 在所选 RAR 工具旁和程序目录的 `dependencies/rar` 中查找
Windows 的 `Default.SFX` 或 Linux 的 `default.sfx`。Linux 目标还查找用户
主目录、`/usr/local/lib` 与 `/usr/lib`。未找到时指定用户提供的模块或样包路径。

## Windows 品牌样包与服务器复用

修改图标或 Logo 需要 Windows 制作端和 `WinRAR.exe`。先在 Windows 制作样包：

```powershell
python -m cli --source .\品牌说明.txt --output .\brands --rar-path "C:\Program Files\WinRAR\WinRAR.exe" --layer rar --layer-name site --layer-sfx windows --layer-sfx-icon .\favicon.ico --layer-sfx-logo .\logo.png --yes --non-interactive --json
```

把样包放到服务器后，可用 Linux `rar` 复用其品牌资源：

```bash
python3 -m cli --source /data/input --output /data/out --layer rar --layer-name resources --layer-sfx windows --layer-sfx-template /data/brands/site.exe --layer-sfx-title '站点资源' --yes --non-interactive --json
```

Windows `Rar.exe` 同样可复用已有模板。品牌图片在接收者下载并运行 SFX 时展示，
网盘页面展示由网盘决定。Windows 单文件或分卷首卷必须小于 4 GiB，
大资源可以设置分卷并交付整套。

`setup` 默认留空；按用户指定的命令填写。原生 SFX 在本层成功解压后执行它，
工作目录为解压目录，相对路径须包含实际的根文件夹。随机层名与来源别名化
不会重写手填命令，使用这些选项时按计划提示核对路径。

## Linux 原生自解压

```bash
python3 -m cli --source ./data --output ./out --layer rar --layer-name resource --layer-sfx linux --layer-sfx-template /opt/rar/default.sfx --yes --non-interactive --json
```

Linux ELF 模块使用原生终端行为。图标、Logo、标题、说明、预设解压路径和
启动命令保持空，`overwrite=ask`、`silent=show`。Linux 制作端给首卷增加
所有者执行权限，下载后可能需重新 `chmod u+x`；接收者在匹配的系统和架构运行。

## 嵌套、分卷与伪装

- Windows 分卷首卷为 `名称.part1.exe`，Linux 为 `名称.part1.sfx`，后续为
  `名称.part2.rar` 等；不足一卷时仍使用首卷名，分享成功清单 `final` 中的全部文件。
- Windows SFX 层使用 `.exe` 后缀。Linux SFX 可调整扩展名，`.bin` 等伪装
  应用于整套分卷；首卷后缀为 `.exe` / `.sfx` 时，后续卷仍使用 `.rar`。
- 同一层的 SFX 和 MP4 融合互斥。可以用普通外层包裹 SFX 后，对外层改扩展名
  或融合视频。7z / ZIP 层是普通归档层。
- 原生运行只解开自身这一层；内层归档由接收者继续处理。NestPack `--unpack`
  通过归档工具读取 Windows / Linux SFX，可逐层解包且不执行模块或 Setup。
- 开启随机填充时，原生自解压会释放填充文件，NestPack 解包会自动清理。
  Windows 首层来源还需满足 Windows 文件名和同目录大小写规则。

预览与执行见 [cli.md](cli.md)。实现依据：
`core/config/sfx.py`、`core/sfx.py`、`core/rar_content.py`、
`core/compression/planning.py`、`core/compression/archive.py`。
