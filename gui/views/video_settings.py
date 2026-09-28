"""单层的视频设置：默认载体与逐来源覆盖。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import LineEdit, PrimaryPushButton, PushButton, ScrollArea

from core.filesystem import normalize_user_path
from gui.config.paths import selection_directory
from gui.views.file_dialog import pick_video
from gui.views.widgets import path_row


class VideoSettingsDialog(QDialog):
    """空的来源专用视频表示沿用默认视频。"""

    def __init__(
        self, parent: QWidget, sources: list[str], video_path: str,
        overrides: dict[str, str], config_dir: Path, *, separate: bool,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("载体视频设置")
        self.resize(720, 420)
        self._config_dir = config_dir
        self._overrides = dict(overrides)
        self._editors: dict[str, LineEdit] = {}
        root = QVBoxLayout(self)
        hint = QLabel("为本层选择载体视频，保留原视频画面和声音。本层使用单文件归档。")
        hint.setWordWrap(True)
        root.addWidget(hint)
        self.default_edit = LineEdit()
        self.default_edit.setText(video_path)
        root.addLayout(path_row("默认视频", self.default_edit,
                                (("选择视频", lambda: self._choose(self.default_edit)),)))
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        rows = QVBoxLayout(content)
        if separate:
            rows.addWidget(QLabel("来源专用视频（留空沿用默认视频）："))
            resolved = {
                normalize_user_path(source, config_dir): video
                for source, video in overrides.items()
            }
            for source in sources:
                label = QLabel(source)
                label.setWordWrap(True)
                rows.addWidget(label)
                editor = LineEdit()
                editor.setPlaceholderText("使用默认视频")
                editor.setText(resolved.get(normalize_user_path(source, config_dir), ""))
                self._editors[source] = editor
                rows.addLayout(path_row("专用视频", editor, (
                    ("选择视频", lambda checked=False, edit=editor: self._choose(edit)),
                    ("使用默认", editor.clear),
                )))
        rows.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save = PrimaryPushButton("应用")
        save.clicked.connect(self.accept)
        cancel = PushButton("取消")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _choose(self, editor: LineEdit) -> None:
        start = selection_directory(editor.text(), self._config_dir)
        selected = pick_video(self, str(start))
        if selected:
            editor.setText(selected)

    def values(self) -> tuple[str, dict[str, str]]:
        """返回编辑后的路径，分别打包时按当前来源重建覆盖表。"""
        overrides = (
            {source: edit.text().strip() for source, edit in self._editors.items()
             if edit.text().strip()} if self._editors else self._overrides
        )
        return self.default_edit.text().strip(), overrides
