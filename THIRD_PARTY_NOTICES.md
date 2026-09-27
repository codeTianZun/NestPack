# 第三方许可

NestPack 的代码和文档采用 GPL-3.0-only：
Copyright (C) 2026 codeTianZun，许可全文见 [LICENSE](LICENSE)。
第三方代码与资源保留各自版权，适用下列许可。

| 组件 | 版权主体 / 许可 | 上游及源码 |
|---|---|---|
| PySide6 / shiboken6 / Qt | The Qt Company Ltd. 与贡献者；按模块适用 LGPLv3 / GPLv3 / 商业许可，本项目使用开源许可 | [Qt for Python 许可](https://doc.qt.io/qtforpython-6/licenses.html)、[PySide6 源码](https://download.qt.io/official_releases/QtForPython/pyside6/)、[Qt 源码](https://download.qt.io/official_releases/qt/) |
| PySide6-Fluent-Widgets | zhiyiYo；本项目使用 GPLv3 | [项目及源码](https://github.com/zhiyiYo/PyQt-Fluent-Widgets/tree/PySide6) |
| PySideSix-Frameless-Window | zhiyiYo；LGPLv3 | [项目及源码](https://github.com/zhiyiYo/PyQt-Frameless-Window) |
| darkdetect | Alberto Sottile；BSD-3-Clause | [项目及源码](https://github.com/albertosottile/darkdetect) |
| pywin32 | Mark Hammond 与贡献者；PSF 及包内声明 | [项目及源码](https://github.com/mhammond/pywin32) |
| tomli（Python 3.10 的条件依赖） | Taneli Hukkinen；MIT | [项目及源码](https://github.com/hukkin/tomli) |
| Python 运行时 | Python Software Foundation 与贡献者；PSF 及内含组件许可 | [许可](https://docs.python.org/3/license.html)、[源码](https://www.python.org/downloads/source/) |
| PyInstaller 引导程序 | PyInstaller 贡献者；GPL 加引导程序例外，部分文件为 Apache-2.0 | [许可及例外](https://pyinstaller.org/en/stable/license.html)、[源码](https://github.com/pyinstaller/pyinstaller) |

Windows GUI 使用上述 GUI 依赖；CLI 源码只使用标准库。Windows 构建会把
安装包中的原始许可收集到 `licenses/` 并嵌入 exe，目录名标明依赖版本。
LGPLv3 与 darkdetect 的许可原文也保存在源码的 `licenses/`。
Qt 内含组件的声明见 [Qt 第三方许可](https://doc.qt.io/qt-6/licenses-used-in-qt.html)；
Windows 二进制发布前须按实际 Qt 版本和所用模块补齐其版权及许可原文。

## 外部归档工具

- **7-Zip 26.02**：Copyright (C) 1999–2026 Igor Pavlov。主要采用
  LGPL-2.1-or-later，部分代码采用 BSD 3-Clause 或 unRAR 限制条款，见
  [官方许可](https://www.7-zip.org/license.txt)。自动安装从官方获取工具，
  保留 `License.txt`、`readme.txt` 及随包帮助文件，并写入对应源码入口
  `SOURCE.txt`。[对应源码](https://github.com/ip7z/7zip/tree/26.02)。
- **RAR / WinRAR**：win.rar GmbH 的专有试用软件，最长免费试用 40 天，
  之后继续使用需要购买许可。由用户从 [RARLAB 官网](https://www.rarlab.com/download.htm)
  自行安装，详见 [许可条款](https://www.rarlab.com/license.htm)。

## 再分发与源码

NestPack 源码：[codeTianZun/NestPack](https://github.com/codeTianZun/NestPack)。
分发二进制时，应在同一下载页面提供对应版本的完整项目源码和依赖源码获取
入口，并保留随包许可及版权声明。上游源码应与实际分发版本对应，获取途径
应持续可用。构建及替换依赖的方法见项目的《打包说明.md》。
你可以修改 LGPL 组件并重新构建，或从源码运行并使用修改后的库；允许为调试
这些修改进行必要的逆向工程。
