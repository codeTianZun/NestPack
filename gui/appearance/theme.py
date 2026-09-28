"""GUI 视觉资源：角色配色、层页签、Fluent 控件与应用图标。"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication, QWidget
from qfluentwidgets import Theme, setCustomStyleSheet, setTheme, setThemeColor

from gui.appearance.logo import APP_ICON_PATH

APP_NAME = "NestPack"
FONT_FAMILY = "Microsoft YaHei UI"
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12

ACCENT = "#725196"
DANGER = "#A23D59"


def init_fluent_theme() -> None:
    """在创建控件前应用浅色主题与紫色主色。"""
    setTheme(Theme.LIGHT)
    setThemeColor(ACCENT)


STYLE_SHEET = """
QWidget { color: #2D3249; font-family: "Microsoft YaHei UI"; font-size: 13px; }
QMainWindow, QWidget#appRoot, QDialog { background: #FCFAFE; }
QFrame#appHeader, QFrame#configBar { background: #FFFFFF; border-bottom: 1px solid #DAD2E6; }
QFrame#deliveryPanel { background: #F0EAF7; border-left: 1px solid #DAD2E6; }
QFrame#taskStatus { background: #F0EAF7; }
QLabel#appName { font-family: "Trebuchet MS"; font-size: 25px; font-weight: 700; }
QPushButton#workspaceTab {
    background: transparent; border: none; border-bottom: 3px solid transparent;
    border-radius: 0; padding: 12px 16px; color: #716A80;
}
QPushButton#workspaceTab:checked { color: #725196; border-bottom-color: #725196; font-weight: 600; }
QPushButton#workspaceTab:hover { background: #F0EAF7; }
QPushButton#workspaceTab:focus { background: #E8DDF1; border-bottom-color: #9E742D; }
QLabel#sectionTitle { font-size: 17px; font-weight: 600; }
QLabel#muted, QLabel#fieldLabel { color: #716A80; }
QLabel#fieldLabel { font-size: 12px; }
QLabel#warning { color: #926923; }
QLabel#success { color: #42756A; }
QLabel#statusLabel, QLabel#outputName { font-size: 14px; font-weight: 600; }
QScrollArea, QScrollArea > QWidget > QWidget { border: none; background: transparent; }
QFrame#card, QFrame#layerCard { background: transparent; border: none; }
QFrame#layerBody { background: #FFFFFF; border: 1px solid #DAD2E6; border-radius: 8px; }
QLabel#layerNumber {
    background: #E8DDF1; color: #725196; font-weight: 600;
    border: 1px solid #DAD2E6; border-bottom: none;
    border-top-left-radius: 8px; border-top-right-radius: 12px; padding: 5px 14px;
}
QLabel#layerNumber[outermost="true"] { border-top: 3px solid #9E742D; padding-top: 3px; }
QToolButton#sectionToggle {
    border: none; background: transparent; color: #716A80; padding: 6px 0;
    text-align: left;
}
QToolButton#sectionToggle:hover { color: #725196; }
QToolButton#sectionToggle:focus { background: #E8DDF1; border-radius: 4px; }
QPushButton#breadcrumbButton {
    background: transparent; color: #725196; border: none;
    padding: 2px 6px; border-radius: 4px; font-size: 12px;
}
QPushButton#breadcrumbButton:hover { background: #F0EAF7; }
QMenu { background: #FFFFFF; border: 1px solid #DAD2E6; padding: 4px; }
QMenu::item { padding: 7px 24px; }
QMenu::item:selected { background: #F0EAF7; }
"""


def load_application_fonts() -> None:
    """加载 Windows 中文字体，使用系统提供的中文字形。"""
    font_directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for filename in ("msyh.ttc", "msyhbd.ttc"):
        font_path = font_directory / filename
        if font_path.is_file():
            QFontDatabase.addApplicationFont(str(font_path))
    QApplication.instance().setFont(QFont(FONT_FAMILY, 10))


def apply_danger_style(widget: QWidget) -> None:
    """为删除与取消操作设置统一的强调色。"""
    style = f"QPushButton {{ color: {DANGER}; }}"
    setCustomStyleSheet(widget, style, style)


def create_app_icon() -> QIcon:
    """加载与 Windows exe 同源的应用图标。"""
    return QIcon(str(APP_ICON_PATH))
