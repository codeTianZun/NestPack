<p align="center">
  <img src="gui/appearance/assets/idle.png" width="180" alt="NestPack 项目 Logo">
</p>

<h1 align="center">NestPack</h1>

**RAR、7z、ZIP 自由组合，一次打包，逐层解包。**

![Version](https://img.shields.io/badge/version-1.0.0-4C6EF5)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-GUI%20%2B%20CLI-0078D4?logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-CLI-FCC624?logo=linux&logoColor=black)
![PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)
![Formats](https://img.shields.io/badge/formats-RAR%20%7C%207z%20%7C%20ZIP-7950F2)
[![License](https://img.shields.io/badge/license-GPL--3.0--only-2F9E44)](LICENSE)

NestPack 可以把文件或文件夹依次包进 RAR、7z、ZIP 压缩层中，格式可以混用。
每层都能单独设置密码、压缩级别和分卷大小；收到最外层压缩包后，也能逐层解包。
Windows 图形界面、Windows 命令行和 Linux 命令行共用同一种 JSON 任务配置。

## ✨ 主要功能

| | 你可以做什么 |
|---|---|
| 🧱 多层打包 | 自由安排 RAR、7z、ZIP 的顺序，为每层设置文件名、密码、压缩级别和分卷大小。 |
| 📦 RAR 自解压 | 每个 RAR 层可交付为 Windows EXE 或 Linux 终端自解压文件；Linux 服务器可复用 Windows 品牌模板。 |
| 🔓 逐层解包 | 选择最外层文件，自动识别每层格式；支持混合格式、分卷和调整过扩展名的归档。 |
| 🎬 视频融合 | 将完整归档融合为可播放的 MP4；支持默认视频、逐来源专用视频、已有归档独立融合与原归档提取。 |
| 🖥️ 多种入口 | Windows 使用图形界面或命令行，Linux 使用命令行；命令行还提供数字菜单。 |
| 🧩 复用任务 | 将设置保存为 JSON，图形界面和命令行都能读取。 |
| 🛠️ 更多选项 | RAR 层可添加恢复记录；还可选择源名称别名、随机填充、最外层扩展名调整和逐层自检。 |

例如，`资料/ → 内层.rar → 中层.7z → 外层.zip`。解包时从最外层开始，NestPack 按相反顺序释放原始内容。

## 🚀 快速开始

### 使用发布程序

| 系统 | 入口 | 操作 |
|---|---|---|
| Windows 图形界面 | `NestPack.exe` | 双击启动，选择来源和输出目录，设置压缩层后点击「开始压缩」。 |
| Windows 命令行 | `nestpack-cli.exe` | 双击进入数字菜单，按提示新建任务或解包。 |
| Linux 命令行 | `./nestpack-linux-cli` | 下载可执行文件，赋予执行权限后运行，无需安装 Python。 |

三个程序分别下载、直接运行。文件组成与构建方式见 [打包说明](打包说明.md)。

### 从源码运行

源码运行需要 Python 3.10+。先获取项目：

```bash
git clone https://github.com/codeTianZun/NestPack.git
cd NestPack
```

**Windows 图形界面**（PowerShell）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m gui
```

**Windows / Linux 命令行**（无需安装第三方 Python 运行依赖）：

```powershell
python -m cli
```

Linux 将命令中的 `python` 换成 `python3`。启动后可用数字菜单创建任务、解包、编辑配置或检测工具。

### 准备归档工具

NestPack 按所选格式调用外部工具：RAR 层需要 WinRAR（Windows）或 RARLAB `rar`（Linux）；7z 和 ZIP 层需要 7-Zip。图形界面的「⚙ 设定」提供工具检测、RAR 安装指引及 7-Zip 安装入口。命令行可运行：

```bash
python -m cli --install-tools
```

该命令显示 RARLAB 官网安装指引，并下载、校验和安装 7-Zip；Linux 使用 `python3 -m cli --install-tools`。RAR / WinRAR 由用户自行安装并遵守 [RARLAB 许可条款](https://www.rarlab.com/license.htm)。

## 📖 压缩与解包

图形界面中，选择来源和输出目录，按从内到外的顺序添加压缩层，然后开始压缩。完成后可查看产物与密码清单；点击「解包…」即可选择最外层文件进行解包。

命令行除了数字菜单，也支持直接给出任务参数。下面创建一个 RAR 内层和 7z 外层，再解包外层文件：

```bash
python -m cli --source ./data --output ./out --layer rar --layer-name inner --layer 7z --layer-name outer --yes
python -m cli --unpack ./out/outer.7z
```

Linux 源码运行将 `python` 换成 `python3`；Windows 发布程序将 `python -m cli` 换成 `nestpack-cli.exe`。分卷归档请从第一卷开始解包，并将同一套分卷放在同一目录。更多参数、密码文件及 JSON 配置用法见 [使用说明](使用说明.md)。

视频融合可在 GUI「任务来源」中启用，也可使用参数：

```bash
python -m cli --source ./data --output ./out --layer 7z --layer-password-file ./password.txt --video ./cover.mp4 --yes
python -m cli --fuse-archive ./existing.zip --video ./cover.mp4 --output ./out
python -m cli --extract-video-archive ./out/existing.mp4 --output ./restored
```

每套归档输出一个 MP4，内部压缩层仍可分卷。融合保留原视频的画面和声音，
加密沿用归档密码。NestPack 可直接解包融合视频；外部工具与网盘在线预览的
兼容性、已验证环境见[视频融合说明](使用说明.md#视频融合)。

RAR 自解压可在每层设置中启用。为 Windows 用户分享资源时，先在 Windows
制作带图标和 Logo 的品牌样包，再让 Linux 服务器通过 `--layer-sfx windows
--layer-sfx-template /data/brands/site.exe` 复用。完整命令、Linux 原生自解压
及嵌套规则见[自解压说明](使用说明.md#rar-自解压)。

## 🔐 密码与文件名

- JSON 配置默认会保存明文密码。需要避免密码写入配置时，可在图形界面关闭「在 JSON 中保存密码」，或在配置中设置 `persist_passwords=false`；请妥善保存完成时显示的密码清单。
- ZIP 层不支持文件名加密，归档内文件名仍可见。需要隐藏文件名时，请使用支持文件名加密的 RAR 或 7z 层。
- 最外层扩展名调整只改变文件名，不改变归档内容；NestPack 解包时按内容识别格式。
- 请只处理有权使用的文件，并遵守存储服务条款、适用法律与组织的安全规范。

## 📚 更多文档

| 文档 | 内容 |
|---|---|
| [使用说明](使用说明.md) | 图形界面、命令行、解包和 JSON 配置的完整说明 |
| [打包说明](打包说明.md) | 三个单文件程序和源码运行方式 |
| [开发文档](开发文档.md) | 项目架构与模块职责 |

## 许可与反馈

项目代码和文档采用 [GPL-3.0-only](LICENSE)，第三方版权与许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。问题和建议请提交至 [GitHub Issues](https://github.com/codeTianZun/NestPack/issues)，并注明版本、系统和复现步骤。
