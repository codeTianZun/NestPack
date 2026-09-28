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
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import ComboBox, LineEdit, ProgressBar, PushButton

from gui.appearance.theme import SPACE_MD, SPACE_SM, SPACE_XS

# 路径行等行内标签的固定宽度，保证同一行内多个标签纵向对齐。
FIELD_LABEL_WIDTH = 68


class SectionCard(QFrame):
    """带标题、说明和右上角操作区的通用卡片。"""

    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__()
        self.setObjectName("card")
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
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


class CollapsibleSection(QWidget):
    """带摘要的可展开区域，展开状态只影响展示。"""

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_SM)
        self.toggle = QToolButton()
        self.toggle.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.toggle.setObjectName("sectionToggle")
        self.toggle.setText(title)
        self.toggle.setCheckable(True)
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle.toggled.connect(self._set_expanded)
        layout.addWidget(self.toggle)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(SPACE_SM)
        self.body.hide()
        layout.addWidget(self.body)

    def _set_expanded(self, expanded: bool) -> None:
        self.body.setVisible(expanded)
        self.toggle.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )

    def set_summary(self, summary: str) -> None:
        self.toggle.setText(f"{self._title}  {summary}" if summary else self._title)
        self.toggle.setToolTip(summary)


__all__ = [
    "ComboBox",
    "CollapsibleSection",
    "ProgressBar",
    "PushButton",
    "SectionCard",
    "path_row",
    "text_field",
]
