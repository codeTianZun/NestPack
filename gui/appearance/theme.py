"""GUI 主题资源：Fluent 浅色主题初始化、精简 QSS 与应用图标。"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QWidget
from qfluentwidgets import Theme, setCustomStyleSheet, setTheme, setThemeColor

from gui.appearance.mascot import MascotState, render_mascot

APP_NAME = "NestPack"
FONT_FAMILY = "Microsoft YaHei UI"

# 设计 token：间距与圆角梯度，QSS 与部件 margins/spacing 共用同一组数值，
# 避免各处随手写零散数字导致排版失序。
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24

RADIUS_SM = 4
RADIUS_MD = 8
RADIUS_LG = 16

# 天空蓝柔和配色：主色与语义色集中在此，供程序化绘制与 Fluent 主题复用。
ACCENT = "#5EB2EF"
ACCENT_HOVER = "#7CC2F4"
ACCENT_SOFT = "#DCEEFB"
ACCENT_DEEP = "#2F74B5"
TEXT_PRIMARY = "#33475F"
TEXT_MUTED = "#8296AC"
TEXT_FAINT = "#A9B8CB"
CARD_BORDER = "#E4EDF8"
TINT_BACKGROUND = "#F5F9FE"
DANGER = "#EE7A8C"


def init_fluent_theme() -> None:
    """初始化 Fluent 浅色主题并注入天空蓝主色，须在创建任何控件前调用。"""
    setTheme(Theme.LIGHT)
    setThemeColor(ACCENT)


# 主界面 QSS 定义背景、标签、卡片与专用按钮样式；
# 通用交互控件由 Fluent 组件库绘制。
STYLE_SHEET = """
QWidget { color: #33475F; font-family: "Microsoft YaHei UI"; font-size: 13px; }
QMainWindow, QWidget#appRoot {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #F8FBFE, stop:1 #EAF2FB);
}
QDialog { background: #F4F8FD; }
QLabel#title { color: #2C3E56; }
QLabel#sectionTitle { color: #2C3E56; font-size: 16px; font-weight: 700; }
QLabel#muted, QLabel#fieldLabel, QLabel#statusLabel, QLabel#statCaption {
    color: #8296AC;
}
QLabel#fieldLabel, QLabel#statCaption { font-size: 12px; }
QLabel#warning { color: #E2A63D; font-size: 12px; }
QLabel#success { color: #43BD8C; font-size: 12px; }
QLabel#layerNumber {
    background: #DCEEFB; color: #2F74B5; border-radius: 10px;
    font-family: Consolas, "Microsoft YaHei UI"; font-weight: 800;
    min-width: 34px; max-width: 34px; min-height: 30px; max-height: 30px;
}
QLabel#statValue { color: #2C3E56; font-size: 14px; font-weight: 700; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QFrame#card, QFrame#actionCard {
    background: #FFFFFF; border: 1px solid #E4EDF8; border-radius: 16px;
}
QFrame#layerCard, QFrame#statBox {
    background: #F5F9FE; border: 1px solid #E4EDF8; border-radius: 12px;
}
QPushButton#breadcrumbButton {
    background: transparent; color: #2F74B5; border: none;
    padding: 2px 6px; border-radius: 8px; font-size: 12px;
}
QPushButton#breadcrumbButton:hover {
    background: #EAF3FC; color: #2C3E56;
}
"""


def load_application_fonts() -> None:
    """加载 Windows 中文字体并设为应用字体。"""
    font_directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for filename in ("msyh.ttc", "msyhbd.ttc"):
        font_path = font_directory / filename
        if font_path.is_file():
            QFontDatabase.addApplicationFont(str(font_path))
    QApplication.instance().setFont(QFont(FONT_FAMILY, 10))


def apply_card_shadow(widget: QWidget) -> None:
    """为卡片叠加淡蓝色阴影。"""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(22)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(126, 168, 214, 55))
    widget.setGraphicsEffect(shadow)


def apply_danger_style(widget: QWidget) -> None:
    """给删除和取消按钮应用统一的危险色。"""
    style = f"QPushButton {{ color: {DANGER}; }}"
    setCustomStyleSheet(widget, style, style)


def apply_accent_glow(widget: QWidget) -> None:
    """为主操作按钮叠加主色柔光，作为整页唯一的发光记忆点。"""
    glow = QGraphicsDropShadowEffect(widget)
    glow.setBlurRadius(24)
    glow.setOffset(0, 6)
    glow.setColor(QColor(94, 178, 239, 110))
    widget.setGraphicsEffect(glow)


def create_app_icon() -> QIcon:
    """绘制吉祥物头像图标，无需外部资源。"""
    pixmap = QPixmap(256, 256)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#A5D3F4"))
    painter.drawRoundedRect(12, 12, 232, 232, 52, 52)
    painter.drawPixmap(0, 0, render_mascot(MascotState.IDLE, 256))
    painter.end()
    return QIcon(pixmap)
