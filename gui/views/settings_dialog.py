"""运行环境设置：工具路径、检测安装与外部压缩窗口。"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget
from qfluentwidgets import CheckBox, PushButton

from core.models import AppConfig
from gui.views.runtime_panel import RuntimePanel


class SettingsDialog(QDialog):
    """管理随当前配置保存的运行环境。"""

    changed = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("运行环境 · NestPack")
        self.resize(700, 390)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)
        self.runtime = RuntimePanel()
        self.runtime.changed.connect(self.changed)
        root.addWidget(self.runtime)
        self.show_gui_check = CheckBox("显示 WinRAR 压缩窗口")
        self.show_gui_check.setToolTip("关闭后由 WinRAR 在后台运行，NestPack 显示处理进度。")
        self.show_gui_check.toggled.connect(self.changed)
        root.addWidget(self.show_gui_check)
        root.addStretch(1)
        close = PushButton("关闭")
        close.clicked.connect(self.hide)
        root.addWidget(close)

    def collect(self, config: AppConfig, *, strict: bool = True) -> AppConfig:
        return replace(
            self.runtime.collect(config, strict=strict),
            show_winrar_gui=self.show_gui_check.isChecked(),
        )

    def apply(self, config: AppConfig) -> None:
        self.runtime.apply(config)
        self.show_gui_check.setChecked(config.show_winrar_gui)
