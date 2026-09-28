"""解包对话框：选择嵌套压缩包，逐层解开并释放原始文件。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Slot
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    IndeterminateProgressBar,
    LineEdit,
    PlainTextEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SpinBox,
)

from core.filesystem import normalize_user_path
from gui.appearance.theme import apply_danger_style
from gui.config.paths import selection_directory
from gui.tasks.unpack import UnpackTask
from gui.views.dialogs import ask_yes_no, show_error, show_info
from gui.views.file_dialog import pick_archive, pick_directory
from gui.views.widgets import path_row


class UnpackDialog(QDialog):
    """选择最外层压缩包与候选密码，逐层解开到指定目录。"""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        winrar_configured: str = "auto",
        sevenzip_configured: str = "auto",
        config_dir: Path | None = None,
        preset_candidates: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("解包 · NestPack")
        self.setModal(True)
        self.setMinimumSize(560, 480)
        self._winrar_configured = winrar_configured
        self._sevenzip_configured = sevenzip_configured
        self._config_dir = config_dir or Path.cwd()
        # 主窗口传入的预置候选（当前配置各层密码），与手输密码合并尝试。
        self._preset_candidates = list(preset_candidates or [])
        self._output_dir: Path | None = None
        self._task = UnpackTask(self)
        self._task.log.connect(self._append_log)
        self._task.completed.connect(self._unpack_succeeded)
        self._task.cancelled.connect(self._restore_progress_bar)
        self._task.failed.connect(self._unpack_failed)
        self._task.active_changed.connect(self._set_active)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        hint = QLabel(
            "选择最外层压缩包或融合 MP4（支持 .bin 等伪装扩展名与分卷，分卷请选第一卷；"
            "伪装扩展名的分卷套会自动识别）。候选密码每行一个，顺序不限；"
            "当前配置中已保存的各层密码会自动加入候选。"
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.archive_edit = LineEdit()
        layout.addLayout(
            path_row(
                "压缩包", self.archive_edit,
                (("选择文件", self._choose_archive),),
            )
        )
        self.output_edit = LineEdit()
        layout.addLayout(
            path_row(
                "解压到", self.output_edit,
                (("选择目录", self._choose_output),),
            )
        )

        password_label = QLabel("候选密码（每行一个，顺序不限，可留空）")
        password_label.setObjectName("fieldLabel")
        layout.addWidget(password_label)
        self.password_edit = PlainTextEdit()
        self.password_edit.setPlaceholderText(
            "第 1 行密码\n第 2 行密码（未加密的层无需填写）"
        )
        self.password_edit.setMaximumHeight(96)
        layout.addWidget(self.password_edit)

        layers_row = QHBoxLayout()
        layers_label = QLabel("强制层数")
        layers_label.setObjectName("fieldLabel")
        self.layers_spin = SpinBox()
        self.layers_spin.setRange(0, 99)
        self.layers_spin.setSpecialValueText("自动识别")
        self.layers_spin.setToolTip(
            "留 0 自动按内容识别层数；原始文件本身恰好是一个 RAR 压缩包时，"
            "手动指定层数可以避免多解一层。"
        )
        layers_row.addWidget(layers_label)
        layers_row.addWidget(self.layers_spin)
        layers_row.addStretch(1)
        layout.addLayout(layers_row)

        # 双进度条：确定进度条显示已知进度，不定长动画条用于忙碌态。
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.busy_bar = IndeterminateProgressBar(start=False)
        self.busy_bar.hide()
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.busy_bar)

        self.log_edit = PlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumBlockCount(500)
        self.log_edit.setPlaceholderText("开始解包后，这里会显示每层的处理过程。")
        layout.addWidget(self.log_edit, 1)

        buttons = QHBoxLayout()
        self.start_button = PrimaryPushButton("开始解包")
        self.start_button.clicked.connect(self._start)
        self.cancel_button = PushButton("取消解包")
        apply_danger_style(self.cancel_button)
        self.cancel_button.clicked.connect(self._cancel)
        self.cancel_button.hide()
        close_button = PushButton("关闭")
        close_button.clicked.connect(self._request_close)
        buttons.addStretch(1)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def _choose_archive(self) -> None:
        """弹出 Fluent 风格文件选择对话框，选完写入压缩包输入框并预填输出目录。"""
        start = selection_directory(self.archive_edit.text(), self._config_dir)
        selected = pick_archive(self, str(start))
        if not selected:
            return
        self.archive_edit.setText(selected)
        if not self.output_edit.text().strip():
            path = Path(selected)
            self.output_edit.setText(str(path.parent / f"{path.stem}_unpacked"))

    def _choose_output(self) -> None:
        """弹出 Fluent 风格目录选择对话框，选完写入解包输出目录输入框。"""
        raw = self.output_edit.text().strip()
        selected = pick_directory(
            self,
            title="选择解包输出目录",
            start_path=str(selection_directory(raw, self._config_dir)),
            default_output=str(normalize_user_path(raw, self._config_dir)) if raw else "",
        )
        if selected:
            self.output_edit.setText(selected)

    def _start(self) -> None:
        if self._task.active:
            return
        archive_text = self.archive_edit.text().strip()
        output_text = self.output_edit.text().strip()
        if not archive_text:
            show_error(self, "无法开始", "请选择最外层压缩包。")
            return
        archive = normalize_user_path(archive_text, self._config_dir)
        if output_text:
            output_dir = normalize_user_path(output_text, self._config_dir)
        else:
            output_dir = archive.parent / f"{archive.stem}_unpacked"
        candidates = [
            line.strip()
            for line in self.password_edit.toPlainText().splitlines()
            if line.strip()
        ]
        # 手输密码优先，其后自动尝试主窗口预置的配置密码。
        for password in self._preset_candidates:
            if password not in candidates:
                candidates.append(password)
        layer_limit = self.layers_spin.value() or None

        try:
            self._output_dir = output_dir
            self._task.start(
                archive, output_dir, candidates, layer_limit,
                winrar_configured=self._winrar_configured,
                sevenzip_configured=self._sevenzip_configured,
                config_dir=self._config_dir,
            )
        except (ValueError, OSError) as error:
            show_error(self, "无法开始", str(error))

    @Slot(bool)
    def _set_active(self, active: bool) -> None:
        self.start_button.setEnabled(not active)
        self.cancel_button.setVisible(active)
        self.cancel_button.setEnabled(True)
        if active:
            self.progress_bar.setValue(0)
            self.progress_bar.hide()
            self.busy_bar.show()
            self.busy_bar.start()
            self.log_edit.clear()
        else:
            self._restore_progress_bar()

    def _cancel(self) -> None:
        if self._task.active:
            self.cancel_button.setEnabled(False)
            self._append_log("正在取消…")
            self._task.cancel()

    @Slot(str)
    def _append_log(self, line: str) -> None:
        text = line.strip()
        if text:
            self.log_edit.appendPlainText(text)

    @Slot(object)
    def _unpack_succeeded(self, entries: list[Path]) -> None:
        self._restore_progress_bar()
        self.progress_bar.setValue(1)
        names = "\n".join(f"  {entry}" for entry in entries) or "  （空）"
        confirmed = ask_yes_no(
            self,
            "解包完成",
            f"解包完成，共恢复 {len(entries)} 个条目：\n{names}",
            yes_text="打开输出目录",
        )
        if confirmed and self._output_dir is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_dir)))

    @Slot(str)
    def _unpack_failed(self, message: str) -> None:
        self._restore_progress_bar()
        show_error(self, "解包失败", message)

    def _restore_progress_bar(self) -> None:
        """解包结束后停止忙碌动画条，恢复确定进度条的显示。"""
        self.busy_bar.stop()
        self.busy_bar.hide()
        self.progress_bar.show()

    def _request_close(self) -> None:
        if self._task.active:
            show_info(self, "正在解包", "请先等待解包完成或取消后再关闭。")
            return
        super().reject()

    def reject(self) -> None:
        """Esc 与关闭按钮共用任务结束检查。"""
        self._request_close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._task.active:
            event.ignore()
            self._cancel()
            return
        super().closeEvent(event)


__all__ = ["UnpackDialog"]
