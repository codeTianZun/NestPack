"""可复用的界面小组件：区块卡片、布局构造器与 Fluent 控件导出。

下拉框、输入框、按钮、进度条统一使用 qfluentwidgets 组件，
本模块按项目惯用名称导出。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import ComboBox, LineEdit, ProgressBar, PushButton

from gui.appearance.theme import SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XS, apply_card_shadow

# 路径行等行内标签的固定宽度，保证同一行内多个标签纵向对齐。
FIELD_LABEL_WIDTH = 68


class SectionCard(QFrame):
    """带标题、说明和右上角操作区的通用卡片。"""

    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__()
        self.setObjectName("card")
        apply_card_shadow(self)
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(SPACE_LG, SPACE_MD, SPACE_LG, SPACE_MD)
        self.outer_layout.setSpacing(SPACE_MD)

        header = QHBoxLayout()
        header.setSpacing(SPACE_SM)
        text_box = QVBoxLayout()
        text_box.setSpacing(SPACE_XS)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        text_box.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("muted")
            subtitle_label.setWordWrap(True)
            text_box.addWidget(subtitle_label)
        header.addLayout(text_box, 1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(SPACE_XS)
        header.addLayout(self.actions)
        self.outer_layout.addLayout(header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(SPACE_SM)
        self.outer_layout.addWidget(self.body, 1)


def text_field(
    title: str, value: str
) -> tuple[QWidget, LineEdit, QHBoxLayout]:
    """带标题标签与行布局的输入框。"""
    box = QWidget()
    box_layout = QVBoxLayout(box)
    box_layout.setContentsMargins(0, 0, 0, 0)
    box_layout.setSpacing(SPACE_XS)
    label = QLabel(title)
    label.setObjectName("fieldLabel")
    box_layout.addWidget(label)
    line = QHBoxLayout()
    line.setContentsMargins(0, 0, 0, 0)
    line.setSpacing(SPACE_XS)
    edit = LineEdit()
    edit.setText(value)
    line.addWidget(edit)
    box_layout.addLayout(line)
    return box, edit, line


def path_row(
    title: str,
    edit: LineEdit,
    buttons: tuple[tuple[str, object], ...],
) -> QHBoxLayout:
    """带固定宽度标题和多个操作按钮的路径输入行。"""
    row = QHBoxLayout()
    row.setSpacing(SPACE_SM)
    label = QLabel(title)
    label.setObjectName("fieldLabel")
    label.setFixedWidth(FIELD_LABEL_WIDTH)
    row.addWidget(label)
    row.addWidget(edit, 1)
    for text, callback in buttons:
        button = PushButton(text)
        button.clicked.connect(callback)
        row.addWidget(button)
    return row


def stat_box(value: str, caption: str) -> tuple[QFrame, QLabel]:
    """任务概览中的统计小卡片。"""
    frame = QFrame()
    frame.setObjectName("statBox")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(SPACE_SM, SPACE_SM, SPACE_SM, SPACE_SM)
    layout.setSpacing(SPACE_XS)
    value_label = QLabel(value)
    value_label.setObjectName("statValue")
    value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    caption_label = QLabel(caption)
    caption_label.setObjectName("statCaption")
    caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(value_label)
    layout.addWidget(caption_label)
    return frame, value_label


__all__ = [
    "ComboBox",
    "ProgressBar",
    "PushButton",
    "SectionCard",
    "path_row",
    "stat_box",
    "text_field",
]
