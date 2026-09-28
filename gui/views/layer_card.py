"""紧凑层条目：选择、顺序调整与当前设置摘要。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QScrollArea, QSizePolicy
from qfluentwidgets import FluentIcon, ToolButton

from core.models import LayerConfig
from gui.appearance.theme import SPACE_XS
from gui.views.layer_editor import LayerEditor


class LayerCard(QFrame):
    """将层摘要与右侧表单关联，移动时保持同一份编辑状态。"""

    changed = Signal()
    selected = Signal(object)
    remove_requested = Signal(object)
    move_requested = Signal(object, int)

    def __init__(self, layer: LayerConfig) -> None:
        super().__init__()
        self.setObjectName("layerCard")
        self.editor = LayerEditor(layer)
        self.page = QScrollArea()
        self.page.setWidgetResizable(True)
        self.page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.page.setWidget(self.editor)
        self._number = 1
        self._total = 1
        self._editable = True
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_XS)
        self.select_button = QPushButton()
        self.select_button.setObjectName("layerSelect")
        self.select_button.setCheckable(True)
        self.select_button.setMinimumHeight(76)
        self.select_button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.select_button.clicked.connect(lambda: self.selected.emit(self))
        layout.addWidget(self.select_button, 1)
        self.up_button = ToolButton(FluentIcon.UP)
        self.down_button = ToolButton(FluentIcon.DOWN)
        self.remove_button = ToolButton(FluentIcon.DELETE)
        for button, title in (
            (self.up_button, "向内移动一层"), (self.down_button, "向外移动一层"),
            (self.remove_button, "删除这一层"),
        ):
            button.setToolTip(title)
            button.setAccessibleName(title)
            layout.addWidget(button)
        self.up_button.clicked.connect(lambda: self.move_requested.emit(self, -1))
        self.down_button.clicked.connect(lambda: self.move_requested.emit(self, 1))
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        self.editor.changed.connect(self._refresh)
        self.editor.changed.connect(self.changed)
        self._refresh()

    def _refresh(self) -> None:
        layer = self.collect(strict=False)
        disguise = {
            "none": "原扩展名",
            "extension": f"伪装 {layer.disguise.extension}",
            "video": "MP4 视频",
        }[layer.disguise.mode]
        password = (
            "密码已设置" if layer.password else "密码待补充" if layer.password_set else "无密码"
        )
        role = " · 最外层" if self._number == self._total else ""
        name = self.editor.name_edit.text().strip() or "待填写文件名"
        text = (
            f"第 {self._number} 层{role}  {name}\n"
            f"{layer.format.upper()} · {disguise} · {password}"
        )
        self.select_button.setText(text)
        self.select_button.setToolTip(text)
        self.select_button.setAccessibleName(text.replace("\n", "，"))

    def set_number(self, number: int, total: int) -> None:
        self._number, self._total = number, total
        self.editor.set_number(number, total)
        self.set_editable(self._editable)
        self._refresh()

    def set_editable(self, editable: bool) -> None:
        """锁定编辑和结构操作，仍允许切换查看各层设置。"""
        self._editable = editable
        self.editor.setEnabled(editable)
        self.up_button.setEnabled(editable and self._number > 1)
        self.down_button.setEnabled(editable and self._number < self._total)
        self.remove_button.setEnabled(editable and self._total > 1)

    def collect(self, *, strict: bool = True) -> LayerConfig:
        return self.editor.collect(self._number, strict=strict)
