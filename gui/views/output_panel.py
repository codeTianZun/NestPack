"""压缩输出：目录、最外层伪装、载体视频与输出选项。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from qfluentwidgets import CheckBox, PushButton

from core.config import validate_disguise_extension
from core.filesystem import normalize_user_path
from core.models import AppConfig
from gui.config.paths import selection_directory
from gui.views.file_dialog import pick_directory, pick_video
from gui.views.video_settings import VideoSettingsDialog
from gui.views.widgets import CollapsibleSection, ComboBox, text_field


class OutputPanel(QWidget):
    """保存输出字段，向应用交出已有归档的伪装动作。"""

    changed = Signal()
    directory_changed = Signal(str)
    disguise_existing_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._config_dir = Path.cwd()
        self._sources: list[str] = []
        self._separate = False
        self._source_video_paths: dict[str, str] = {}
        self._disguise_enabled = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        title = QLabel("输出")
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

        label = QLabel("输出伪装")
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        self.disguise_combo = ComboBox()
        for text, value in (
            ("原扩展名", "none"), ("修改扩展名", "extension"), ("视频伪装（MP4）", "video"),
        ):
            self.disguise_combo.addItem(text, userData=value)
        self.disguise_combo.currentIndexChanged.connect(self._mode_changed)
        layout.addWidget(self.disguise_combo)
        self.extension_box, self.extension_edit, _ = text_field("伪装扩展名", ".bin")
        self.extension_edit.setPlaceholderText("如 .bin、.dat")
        self.extension_edit.textChanged.connect(self.changed)
        layout.addWidget(self.extension_box)

        self.video_box = QWidget()
        video_layout = QVBoxLayout(self.video_box)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(8)
        video_field, self.video_edit, row = text_field("默认载体视频", "")
        self.video_edit.setPlaceholderText("选择 MP4 文件")
        self.video_edit.textChanged.connect(self.changed)
        browse_video = PushButton("浏览…")
        browse_video.clicked.connect(self._choose_video)
        row.addWidget(browse_video)
        video_layout.addWidget(video_field)
        self.source_videos_button = PushButton("逐来源指定视频…")
        self.source_videos_button.clicked.connect(self._choose_source_videos)
        video_layout.addWidget(self.source_videos_button)
        self.video_hint = QLabel("最外层使用单文件归档；可在内层分卷。")
        self.video_hint.setObjectName("muted")
        self.video_hint.setWordWrap(True)
        video_layout.addWidget(self.video_hint)
        layout.addWidget(self.video_box)
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
        self._update_visibility()

    def _options_changed(self) -> None:
        enabled = [
            check.text() for check in (self.overwrite_check, self.timestamp_check)
            if check.isChecked()
        ]
        self.options.set_summary("，".join(enabled))
        self.changed.emit()

    def mode(self) -> str:
        return self.disguise_combo.currentData()

    def _mode_changed(self) -> None:
        if self.mode() != "video":
            self._disguise_enabled = self.mode() == "extension"
        self._update_visibility()
        self.changed.emit()

    def _update_visibility(self) -> None:
        self.extension_box.setVisible(self.mode() == "extension")
        self.video_box.setVisible(self.mode() == "video")
        self.source_videos_button.setVisible(self._separate)

    def set_sources(self, sources: list[str], separate: bool) -> None:
        self._sources = list(sources)
        self._separate = separate
        self._update_visibility()

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

    def _choose_video(self) -> None:
        selected = pick_video(
            self.window(), str(selection_directory(self.video_edit.text(), self._config_dir))
        )
        if selected:
            self.video_edit.setText(selected)

    def _choose_source_videos(self) -> None:
        dialog = VideoSettingsDialog(
            self.window(), self._sources, self.video_edit.text(), self._source_video_paths,
            self._config_dir, separate=self._separate,
        )
        if dialog.exec():
            video, self._source_video_paths = dialog.values()
            self.video_edit.setText(video)
            self.changed.emit()

    def set_preview(self, name: str, hint: str) -> None:
        self.output_name.setText(name)
        self.output_hint.setText(hint)

    def collect(self, config: AppConfig, *, strict: bool = True) -> AppConfig:
        output = self.output_directory()
        extension = self.extension_edit.text().strip() or ".bin"
        if strict:
            if not output:
                raise ValueError("请选择输出目录")
            validate_disguise_extension(extension)
        return replace(
            config, output_directory=output,
            disguise_outer_extension=self._disguise_enabled, disguise_extension=extension,
            video_fusion=self.mode() == "video", video_path=self.video_edit.text().strip(),
            source_video_paths=dict(self._source_video_paths),
            overwrite_existing=self.overwrite_check.isChecked(),
            randomize_timestamps=self.timestamp_check.isChecked(),
        )

    def apply(self, config: AppConfig) -> None:
        self.set_output_directory(config.output_directory)
        self._disguise_enabled = config.disguise_outer_extension
        self.extension_edit.setText(config.disguise_extension)
        self.video_edit.setText(config.video_path)
        self._source_video_paths = dict(config.source_video_paths)
        mode = "video" if config.video_fusion else "extension" if self._disguise_enabled else "none"
        with QSignalBlocker(self.disguise_combo):
            self.disguise_combo.setCurrentIndex(self.disguise_combo.findData(mode))
        self.overwrite_check.setChecked(config.overwrite_existing)
        self.timestamp_check.setChecked(config.randomize_timestamps)
        self._update_visibility()
