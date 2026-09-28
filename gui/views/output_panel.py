"""压缩输出：目录、最终产物预览与任务级输出选项。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from qfluentwidgets import CheckBox, PushButton

from core.filesystem import normalize_user_path
from core.models import AppConfig
from gui.config.paths import selection_directory
from gui.views.file_dialog import pick_directory
from gui.views.widgets import CollapsibleSection, text_field


class OutputPanel(QWidget):
    """保存输出字段，向应用交出已有归档的伪装动作。"""

    changed = Signal()
    directory_changed = Signal(str)
    disguise_existing_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._config_dir = Path.cwd()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        title = QLabel("任务输出")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        self.output_name = QLabel("请选择来源并设置压缩层")
        self.output_name.setObjectName("outputName")
        self.output_name.setWordWrap(True)
        layout.addWidget(self.output_name)
        self.output_hint = QLabel()
        self.output_hint.setObjectName("muted")
        self.output_hint.setWordWrap(True)
        layout.addWidget(self.output_hint)
        directory_box, self.output_edit, row = text_field("输出目录", "")
        browse = PushButton("浏览…")
        browse.clicked.connect(self._choose_output)
        row.addWidget(browse)
        self.output_edit.textChanged.connect(self.directory_changed)
        self.output_edit.textChanged.connect(self.changed)
        layout.addWidget(directory_box)

        self.existing_button = PushButton("伪装已有压缩包…")
        self.existing_button.clicked.connect(self.disguise_existing_requested.emit)
        layout.addWidget(self.existing_button)
        self.options = CollapsibleSection("输出选项")
        self.overwrite_check = CheckBox("覆盖同名输出")
        self.timestamp_check = CheckBox("随机最外层时间戳")
        for check in (self.overwrite_check, self.timestamp_check):
            self.options.body_layout.addWidget(check)
            check.toggled.connect(self._options_changed)
        layout.addWidget(self.options)
        layout.addStretch(1)

    def _options_changed(self) -> None:
        enabled = [
            check.text() for check in (self.overwrite_check, self.timestamp_check)
            if check.isChecked()
        ]
        self.options.set_summary("，".join(enabled))
        self.changed.emit()

    def set_config_directory(self, directory: Path) -> None:
        self._config_dir = directory

    def output_directory(self) -> str:
        return self.output_edit.text().strip()

    def set_output_directory(self, value: str) -> None:
        self.output_edit.setText(value)

    def _choose_output(self) -> None:
        raw = self.output_directory()
        selected = pick_directory(
            self.window(), title="选择压缩输出目录",
            start_path=str(selection_directory(raw, self._config_dir)),
            default_output=str(normalize_user_path(raw, self._config_dir)) if raw else "",
        )
        if selected:
            self.set_output_directory(selected)

    def set_preview(self, name: str, hint: str) -> None:
        self.output_name.setText(name)
        self.output_hint.setText(hint)

    def collect(self, config: AppConfig, *, strict: bool = True) -> AppConfig:
        output = self.output_directory()
        if strict:
            if not output:
                raise ValueError("请选择输出目录")
        return replace(
            config, output_directory=output,
            overwrite_existing=self.overwrite_check.isChecked(),
            randomize_timestamps=self.timestamp_check.isChecked(),
        )

    def apply(self, config: AppConfig) -> None:
        self.set_output_directory(config.output_directory)
        self.overwrite_check.setChecked(config.overwrite_existing)
        self.timestamp_check.setChecked(config.randomize_timestamps)
