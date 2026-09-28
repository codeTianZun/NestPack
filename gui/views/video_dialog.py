"""独立视频融合与原归档提取窗口。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    CheckBox,
    IndeterminateProgressBar,
    LineEdit,
    PlainTextEdit,
    PrimaryPushButton,
    PushButton,
)

from core.filesystem import normalize_user_path
from gui.config.paths import selection_directory
from gui.tasks.video import VideoTask
from gui.views.dialogs import show_error, show_info
from gui.views.file_dialog import pick_archive, pick_directory, pick_video
from gui.views.widgets import ComboBox, path_row


class VideoDialog(QDialog):
    """选择输入后在后台生成 MP4 或提取原归档。"""

    def __init__(self, parent: QWidget, config_dir: Path) -> None:
        super().__init__(parent)
        self.setWindowTitle("视频融合 / 提取原归档 · NestPack")
        self.setModal(True)
        self.resize(700, 500)
        self._config_dir = config_dir
        self._close_when_finished = False
        self._task = VideoTask(self)
        self._task.log.connect(self._log)
        self._task.completed.connect(self._completed)
        self._task.failed.connect(lambda message: show_error(self, "处理失败", message))
        self._task.active_changed.connect(self._set_active)
        self._task.finished.connect(self._finished)
        root = QVBoxLayout(self)
        self.form = QWidget()
        form = QVBoxLayout(self.form)
        form.setContentsMargins(0, 0, 0, 0)
        self.mode = ComboBox()
        self.mode.addItems(["融合已有归档与 MP4", "从融合视频提取原归档"])
        self.mode.currentIndexChanged.connect(self._mode_changed)
        form.addWidget(self.mode)
        hint = QLabel("融合保留已有归档的内容与密码，输出一个 MP4。提取归档后可继续使用“解包”。")
        hint.setWordWrap(True)
        form.addWidget(hint)
        self.source_edit = LineEdit()
        form.addLayout(path_row("输入文件", self.source_edit,
                                (("选择文件", self._choose_source),)))
        self.video_row = QWidget()
        self.video_edit = LineEdit()
        video_layout = QVBoxLayout(self.video_row)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.addLayout(path_row("载体 MP4", self.video_edit,
                                        (("选择视频", self._choose_video),)))
        form.addWidget(self.video_row)
        self.output_edit = LineEdit()
        form.addLayout(path_row("输出目录", self.output_edit,
                                (("选择目录", self._choose_output),)))
        self.overwrite = CheckBox("覆盖输出目录中的同名成品")
        form.addWidget(self.overwrite)
        root.addWidget(self.form)
        self.busy = IndeterminateProgressBar(start=False)
        self.busy.hide()
        root.addWidget(self.busy)
        self.log = PlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        root.addWidget(self.log, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.start = PrimaryPushButton("开始处理")
        self.start.clicked.connect(self._start)
        self.cancel = PushButton("取消处理")
        self.cancel.clicked.connect(self._cancel)
        self.cancel.hide()
        close = PushButton("关闭")
        close.clicked.connect(self.reject)
        buttons.addWidget(self.start)
        buttons.addWidget(self.cancel)
        buttons.addWidget(close)
        root.addLayout(buttons)

    def _mode_changed(self) -> None:
        self.video_row.setVisible(self.mode.currentIndex() == 0)
        self.source_edit.clear()

    def _choose_source(self) -> None:
        start = selection_directory(self.source_edit.text(), self._config_dir)
        picker = pick_archive if self.mode.currentIndex() == 0 else pick_video
        selected = picker(self, str(start))
        if selected:
            self.source_edit.setText(selected)
            if not self.output_edit.text().strip():
                self.output_edit.setText(str(Path(selected).parent / "video_output"))

    def _choose_video(self) -> None:
        start = selection_directory(self.video_edit.text(), self._config_dir)
        selected = pick_video(self, str(start))
        if selected:
            self.video_edit.setText(selected)

    def _choose_output(self) -> None:
        start = selection_directory(self.output_edit.text(), self._config_dir)
        selected = pick_directory(self, title="选择输出目录", start_path=str(start))
        if selected:
            self.output_edit.setText(selected)

    def _start(self) -> None:
        if self._task.active:
            return
        source = self.source_edit.text().strip()
        video = self.video_edit.text().strip() if self.mode.currentIndex() == 0 else None
        output = self.output_edit.text().strip()
        if not source or not output or video == "":
            show_error(self, "无法开始", "请选择输入文件、输出目录，以及融合所需的载体视频。")
            return
        self.log.clear()
        self._task.start(
            normalize_user_path(source, self._config_dir),
            normalize_user_path(video, self._config_dir) if video is not None else None,
            normalize_user_path(output, self._config_dir), self.overwrite.isChecked(),
        )

    def _set_active(self, active: bool) -> None:
        self.form.setEnabled(not active)
        self.start.setVisible(not active)
        self.cancel.setVisible(active)
        self.cancel.setEnabled(active)
        self.busy.setVisible(active)
        if active:
            self.busy.start()
        else:
            self.busy.stop()

    def _log(self, message: str) -> None:
        self.log.appendPlainText(message)

    def _completed(self, result: Path) -> None:
        self._log(f"已完成：{result}")
        if not self._close_when_finished:
            show_info(self, "处理完成", str(result))

    def _cancel(self) -> None:
        self._task.cancel()
        self.cancel.setEnabled(False)
        self._log("正在取消…")

    def _finished(self) -> None:
        if self._close_when_finished:
            super().reject()

    def reject(self) -> None:
        if self._task.active:
            self._close_when_finished = True
            self._cancel()
        else:
            super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._task.active:
            event.ignore()
            self.reject()
        else:
            super().closeEvent(event)
