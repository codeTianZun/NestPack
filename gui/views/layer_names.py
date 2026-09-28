"""当前来源、当前层的文件名编辑。"""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from qfluentwidgets import PushButton

from core.models import LayerConfig
from core.naming import archive_extension, default_archive_name, replace_archive_extension
from gui.views.widgets import text_field


class LayerNames(QWidget):
    """单个层名表单，自动名称随来源、层号与格式更新。"""

    changed = Signal()

    def __init__(self, layer: LayerConfig) -> None:
        super().__init__()
        self.auto_name = layer.auto_name
        self._source: Path | None = None
        self._number = 1
        self._extension = archive_extension(layer)
        self._template = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.random_hint = QLabel("执行时将为本次打包重新生成名称，覆盖已填写的名称。")
        self.random_hint.setObjectName("warning")
        self.random_hint.setWordWrap(True)
        self.random_hint.hide()
        layout.addWidget(self.random_hint)
        self.name_box, self.name_edit, row = text_field("文件名", layer.archive_name)
        self.reset_button = PushButton("恢复默认")
        self.reset_button.clicked.connect(self._reset_name)
        row.addWidget(self.reset_button)
        self.name_edit.textEdited.connect(self._edit_name)
        layout.addWidget(self.name_box)
        self.template_hint = QLabel()
        self.template_hint.setObjectName("muted")
        self.template_hint.setWordWrap(True)
        layout.addWidget(self.template_hint)
        self.set_source(None)

    def set_source(self, source: Path | None, *, template: bool = False) -> None:
        self._source, self._template = source, template
        self.name_box.setVisible(not template)
        self.template_hint.setVisible(template)
        self._refresh_name()

    def _refresh_name(self) -> None:
        if self.auto_name:
            self.name_edit.setText(default_archive_name(
                self._source.stem if self._source else "layer", self._number, self._extension,
            ))
        self.reset_button.setEnabled(not self.auto_name)
        self.template_hint.setText(
            f"默认文件名：来源名_{self._number}{self._extension}。选中来源后可单独修改。"
        )

    def _edit_name(self, _text: str) -> None:
        self.auto_name = False
        self.reset_button.setEnabled(True)
        self.changed.emit()

    def _reset_name(self) -> None:
        self.auto_name = True
        self._refresh_name()
        self.changed.emit()

    def set_number(self, number: int) -> None:
        self._number = number
        self._refresh_name()

    def set_extension(self, extension: str) -> None:
        self._extension = extension
        self.name_edit.setText(replace_archive_extension(self.name_edit.text(), extension))
        self._refresh_name()

    def set_random_names(self, enabled: bool) -> None:
        self.random_hint.setVisible(enabled)

    def summary(self) -> str:
        if self._template:
            return f"来源名_{self._number}{self._extension}"
        return self.name_edit.text().strip() or "待填写文件名"
