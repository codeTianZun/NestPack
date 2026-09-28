"""单层伪装设置：按方式展开扩展名或载体视频。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from qfluentwidgets import PushButton

from core.models import DisguiseConfig, SfxConfig
from gui.config.paths import selection_directory
from gui.views.file_dialog import pick_video
from gui.views.video_settings import VideoSettingsDialog
from gui.views.widgets import CollapsibleSection, ComboBox, text_field


class DisguisePanel(QWidget):
    """管理本层伪装字段及逐来源视频，切换方式保留已填内容。"""

    changed = Signal()

    def __init__(self, config: DisguiseConfig) -> None:
        super().__init__()
        self._config_dir = Path.cwd()
        self._sources: list[str] = []
        self._separate = False
        self._source_video_paths = dict(config.source_video_paths)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        label = QLabel("伪装方式")
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        self.disguise_combo = ComboBox()
        for text, value in (
            ("原扩展名", "none"), ("修改扩展名", "extension"), ("视频伪装（MP4）", "video"),
        ):
            self.disguise_combo.addItem(text, userData=value)
        self.disguise_combo.setCurrentIndex(self.disguise_combo.findData(config.mode))
        self.disguise_combo.currentIndexChanged.connect(self._mode_changed)
        layout.addWidget(self.disguise_combo)
        self.extension_box, self.extension_edit, _ = text_field("伪装扩展名", config.extension)
        self.extension_edit.setPlaceholderText("如 .bin、.dat")
        self.extension_edit.textChanged.connect(self.changed)
        layout.addWidget(self.extension_box)

        self.video_box = QWidget()
        video_layout = QVBoxLayout(self.video_box)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(8)
        video_field, self.video_edit, row = text_field("本层默认载体视频", config.video_path)
        self.video_edit.setPlaceholderText("选择 MP4 文件")
        self.video_edit.textChanged.connect(self.changed)
        browse_video = PushButton("浏览…")
        browse_video.clicked.connect(self._choose_video)
        row.addWidget(browse_video)
        video_layout.addWidget(video_field)
        self.source_videos_button = PushButton("逐来源指定视频…")
        self.source_videos_button.clicked.connect(self._choose_source_videos)
        self.source_options = CollapsibleSection("按来源选择视频")
        self.source_options.body_layout.addWidget(self.source_videos_button)
        video_layout.addWidget(self.source_options)
        self.video_hint = QLabel("生成可播放的 MP4，后续压缩层将包裹这个文件。")
        self.video_hint.setObjectName("muted")
        self.video_hint.setWordWrap(True)
        video_layout.addWidget(self.video_hint)
        layout.addWidget(self.video_box)
        self.conflict_hint = QLabel()
        self.conflict_hint.setObjectName("warning")
        self.conflict_hint.setWordWrap(True)
        layout.addWidget(self.conflict_hint)
        self._update_visibility()

    def mode(self) -> str:
        return self.disguise_combo.currentData()

    def _mode_changed(self) -> None:
        self._update_visibility()
        self.changed.emit()

    def _update_visibility(self) -> None:
        self.extension_box.setVisible(self.mode() == "extension")
        self.video_box.setVisible(self.mode() == "video")
        self.source_options.setVisible(self._separate)
        count = len(self._source_video_paths)
        self.source_options.set_summary(f"已指定 {count} 个来源" if count else "")

    def set_sources(self, sources: list[str], separate: bool) -> None:
        self._sources = list(sources)
        self._separate = separate
        self._update_visibility()

    def set_config_directory(self, directory: Path) -> None:
        self._config_dir = directory

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
            self._update_visibility()
            self.changed.emit()

    def set_archive_options(self, volume: str, sfx: SfxConfig) -> None:
        """就地展示当前层组合冲突，草稿字段继续保留。"""
        message = ""
        if self.mode() == "video" and (volume or sfx.enabled):
            message = "视频伪装需要普通单文件归档，请在高级选项中关闭本层分卷和自解压。"
        elif (self.mode() == "extension" and sfx.enabled and sfx.target == "windows"
                and self.extension_edit.text().strip().casefold() != ".exe"):
            message = "Windows 自解压需要 .exe 后缀，请调整本层伪装方式或扩展名。"
        self.conflict_hint.setText(message)
        self.conflict_hint.setVisible(bool(message))

    def collect(self) -> DisguiseConfig:
        """返回本层字段快照，严格校验由层配置入口统一执行。"""
        return DisguiseConfig(
            mode=self.mode(), extension=self.extension_edit.text().strip(),
            video_path=self.video_edit.text().strip(),
            source_video_paths=dict(self._source_video_paths),
        )
