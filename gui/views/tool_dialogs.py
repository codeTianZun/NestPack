"""依赖安装的确认与完成提示。"""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget

from gui.views.dialogs import ask_yes_no, show_info
from platforms.tool_installer import RAR_DOWNLOAD_URL, rar_install_guide
from platforms.tools import TOOLS_DIRECTORY


def confirm_missing_tools(
    parent: QWidget, winrar: Path | None, sevenzip: Path | None
) -> str | None:
    """缺少工具时询问用户，返回需要安装的工具种类。"""
    if winrar is None:
        show_rar_install_guide(parent)
    if sevenzip is not None:
        return None
    if not ask_yes_no(
        parent, "安装 7-Zip",
        "未检测到 7-Zip。\n\n"
        "是否从官方网站下载、校验并安装到：\n"
        f"{TOOLS_DIRECTORY / '7z'}\n\n"
        "安装后可查看同目录下的许可与说明文件。",
        yes_text="下载安装", cancel_text="稍后处理",
    ):
        return None
    return "7z"


def show_rar_install_guide(parent: QWidget) -> None:
    """展示 WinRAR 安装指引，由用户选择打开官网。"""
    if ask_yes_no(
        parent, "WinRAR 安装指引", rar_install_guide("win32"),
        yes_text="打开官网", cancel_text="关闭",
    ):
        QDesktopServices.openUrl(QUrl(RAR_DOWNLOAD_URL))


def confirm_tool_install(parent: QWidget) -> bool:
    """确认自动安装 7-Zip 及其许可材料。"""
    return ask_yes_no(
        parent, "安装 7-Zip",
        "将从官方网站下载并校验 7-Zip，然后安装到：\n"
        f"{TOOLS_DIRECTORY / '7z'}\n\n"
        "保留随包许可和说明文件；已完整安装时会跳过。",
        yes_text="开始安装",
    )


def show_installed_tools(
    parent: QWidget, winrar: Path | None, sevenzip: Path | None
) -> None:
    """展示安装后实际检测到的工具。"""
    installed = [
        name for name, path in (("WinRAR", winrar), ("7-Zip", sevenzip))
        if path is not None
    ]
    show_info(
        parent, "依赖安装完成",
        f"已检测到：{'、'.join(installed)}。\n本地依赖目录：\n{TOOLS_DIRECTORY}",
    )
