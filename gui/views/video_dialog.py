"""已有归档的 MP4 伪装与原归档提取表单。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from PySide6.QtCore import QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
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
from gui.views.dialogs import show_error
from gui.views.file_dialog import pick_archive, pick_directory, pick_video
from gui.views.widgets import path_row


class VideoDialog(QDialog):
    """选择输入后在后台生成 MP4 或提取原归档。"""

    def __init__(
        self, parent: QWidget, config_dir: Path, operation: Literal["fuse", "extract"],
        *, source: str = "", video: str = "", output: str = "",
    ) -> None:
        super().__init__(parent)
        self._fuse = operation == "fuse"
        self.setWindowTitle(
            "伪装已有归档为 MP4 · NestPack" if self._fuse else "提取原归档 · NestPack"
        )
        self.setModal(True)
        self.resize(700, 500)
        self._config_dir = config_dir
        self._close_when_finished = False
        self.task = VideoTask(self)
        self.task.log.connect(self._log)
        self.task.completed.connect(self._completed)
        self.task.failed.connect(self._failed)
        self.task.active_changed.connect(self._set_active)
        self.task.finished.connect(self._finished)
        self._result: Path | None = None
        root = QVBoxLayout(self)
        self.form = QWidget()
        form = QVBoxLayout(self.form)
        form.setContentsMargins(0, 0, 0, 0)
        hint = QLabel(
            "选择已有归档与载体视频，生成 MP4，保留归档内容和密码。"
            if self._fuse else "选择伪装 MP4，提取其中的原归档；之后可在解包页逐层恢复文件。"
        )
        hint.setWordWrap(True)
        form.addWidget(hint)
        self.source_edit = LineEdit()
        self.source_edit.setText(source)
        form.addLayout(path_row("已有归档" if self._fuse else "伪装 MP4", self.source_edit,
                                (("选择文件", self._choose_source),)))
        self.video_row = QWidget()
        self.video_edit = LineEdit()
        self.video_edit.setText(video)
        video_layout = QVBoxLayout(self.video_row)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.addLayout(path_row("载体 MP4", self.video_edit,
                                        (("选择视频", self._choose_video),)))
        form.addWidget(self.video_row)
        self.video_row.setVisible(self._fuse)
        self.output_edit = LineEdit()
        self.output_edit.setText(output)
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
        self.open_button = PushButton("打开输出目录")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_output)
        buttons.addWidget(self.open_button)
        buttons.addStretch(1)
        self.start = PrimaryPushButton("开始伪装" if self._fuse else "提取原归档")
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

    def _choose_source(self) -> None:
        start = selection_directory(self.source_edit.text(), self._config_dir)
        picker = pick_archive if self._fuse else pick_video
        selected = picker(self, str(start))
        if selected:
            self.source_edit.setText(selected)
            if not self.output_edit.text().strip():
                self.output_edit.setText(str(Path(selected).parent / "output"))

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
        if self.task.active:
            return
        source = self.source_edit.text().strip()
        video = self.video_edit.text().strip() if self._fuse else None
        output = self.output_edit.text().strip()
        if not source or not output or video == "":
            message = (
                "请选择归档、载体视频和输出目录。" if self._fuse else "请选择 MP4 和输出目录。"
            )
            show_error(self, "无法开始", message)
            return
        self.log.clear()
        self._result = None
        self.open_button.setEnabled(False)
        try:
            self.task.start(
                normalize_user_path(source, self._config_dir),
                normalize_user_path(video, self._config_dir) if video is not None else None,
                normalize_user_path(output, self._config_dir), self.overwrite.isChecked(),
            )
        except (ValueError, OSError) as error:
            show_error(self, "无法开始", str(error))

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
        self._result = result
        self.open_button.setEnabled(True)
        self._log(f"已完成：{result}")

    def _failed(self, message: str) -> None:
        if not self._close_when_finished:
            show_error(self, "处理失败", message)

    def _open_output(self) -> None:
        if self._result is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._result.parent)))

    def _cancel(self) -> None:
        self.task.cancel()
        self.cancel.setEnabled(False)
        self._log("正在取消…")

    def _finished(self) -> None:
        if self._close_when_finished:
            super().reject()

    def reject(self) -> None:
        if self.task.active:
            self._close_when_finished = True
            self._cancel()
        else:
            super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.task.active:
            event.ignore()
            self.reject()
        else:
            super().closeEvent(event)
