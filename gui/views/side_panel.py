"""公共任务区域：Logo、状态、进度、执行操作与日志。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QVBoxLayout
from qfluentwidgets import (
    IndeterminateProgressBar,
    PlainTextEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
)

from gui.appearance.logo import LogoState, render_logo
from gui.appearance.theme import apply_danger_style

LOGO_SIZE = 80


class SidePanel(QFrame):
    """执行按钮位置固定，日志在可独立查看的窗口中保留。"""

    run_requested = Signal()
    cancel_requested = Signal()
    result_requested = Signal()
    open_output_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("taskStatus")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        status_row = QHBoxLayout()
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(LOGO_SIZE, LOGO_SIZE)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setToolTip("NestPack Logo")
        status_row.addWidget(self.logo_label)
        text = QVBoxLayout()
        self.status_label = QLabel("准备就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        self.status_label.setMaximumHeight(64)
        text.addWidget(self.status_label)
        self.summary_label = QLabel()
        self.summary_label.setObjectName("muted")
        self.summary_label.setWordWrap(True)
        self.summary_label.setMaximumHeight(40)
        text.addWidget(self.summary_label)
        status_row.addLayout(text, 1)
        layout.addLayout(status_row)
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        self.busy_bar = IndeterminateProgressBar(start=False)
        self.busy_bar.hide()
        layout.addWidget(self.busy_bar)
        self.run_button = PrimaryPushButton("开始压缩")
        self.run_button.setMinimumHeight(40)
        self.run_button.clicked.connect(self.run_requested.emit)
        layout.addWidget(self.run_button)
        self.cancel_button = PushButton("取消任务")
        self.cancel_button.setMinimumHeight(40)
        apply_danger_style(self.cancel_button)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        self.cancel_button.hide()
        layout.addWidget(self.cancel_button)
        actions = QHBoxLayout()
        log_button = PushButton("查看日志")
        log_button.clicked.connect(self.show_log)
        actions.addWidget(log_button)
        self.result_button = PushButton("查看结果")
        self.result_button.setEnabled(False)
        self.result_button.clicked.connect(self.result_requested.emit)
        actions.addWidget(self.result_button)
        open_button = PushButton("打开输出目录")
        open_button.clicked.connect(self.open_output_requested.emit)
        actions.addWidget(open_button)
        layout.addLayout(actions)

        self.log_dialog = QDialog(self)
        self.log_dialog.setWindowTitle("任务日志 · NestPack")
        self.log_dialog.resize(760, 500)
        log_layout = QVBoxLayout(self.log_dialog)
        self.progress_log = PlainTextEdit()
        self.progress_log.setReadOnly(True)
        self.progress_log.setMaximumBlockCount(500)
        self.progress_log.setPlaceholderText("开始任务后，这里显示处理过程。")
        log_layout.addWidget(self.progress_log)
        self.set_status("准备就绪", LogoState.IDLE)

    def show_log(self) -> None:
        self.log_dialog.show()
        self.log_dialog.raise_()
        self.log_dialog.activateWindow()

    def set_workspace(self, workspace: str) -> None:
        self.run_button.setText("开始压缩" if workspace == "compress" else "开始解包")

    def set_summary(self, message: str) -> None:
        self.summary_label.setText(message)
        self.summary_label.setToolTip(message)

    def set_active(self, active: bool, *, cancellable: bool = True) -> None:
        self.run_button.setVisible(not active or not cancellable)
        self.run_button.setEnabled(not active)
        self.cancel_button.setVisible(active and cancellable)
        self.cancel_button.setEnabled(True)
        if not active:
            self.set_busy(False)

    def show_cancelling(self) -> None:
        self.cancel_button.setEnabled(False)

    def set_busy(self, busy: bool) -> None:
        self.progress_bar.setVisible(not busy)
        self.busy_bar.setVisible(busy)
        if busy:
            self.busy_bar.start()
        else:
            self.busy_bar.stop()

    def set_progress(self, value: int, total: int) -> None:
        self.set_busy(False)
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(value)

    def set_status(self, message: str, state: LogoState | None = None) -> None:
        self.status_label.setText(message)
        self.status_label.setToolTip(message)
        if state is not None:
            self.logo_label.setPixmap(render_logo(
                state, LOGO_SIZE, device_pixel_ratio=self.devicePixelRatioF()
            ))

    def clear_log(self) -> None:
        self.progress_log.clear()

    def append_log(self, line: str) -> None:
        if line.strip():
            self.progress_log.appendPlainText(line.strip())
