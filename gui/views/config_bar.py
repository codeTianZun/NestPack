"""当前配置、保存状态与配置文件操作。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QSizePolicy
from qfluentwidgets import PushButton

from core.models import AppConfig


class ConfigBar(QFrame):
    """在同一位置管理配置文件与密码落盘选项。"""

    changed = Signal()
    load_requested = Signal()
    save_requested = Signal()
    save_as_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("configBar")
        row = QHBoxLayout(self)
        row.setContentsMargins(24, 6, 24, 6)
        self.name_label = QLabel()
        self.name_label.setMaximumWidth(280)
        row.addWidget(self.name_label)
        self.state_label = QLabel()
        self.state_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.state_label.setObjectName("muted")
        row.addWidget(self.state_label, 1)
        self.button = PushButton("配置操作")
        self.menu = QMenu(self)
        self.menu.setToolTipsVisible(True)
        for title, signal in (
            ("载入配置…", self.load_requested),
            ("保存配置", self.save_requested),
            ("另存配置…", self.save_as_requested),
        ):
            action = self.menu.addAction(title)
            action.triggered.connect(signal.emit)
        self.menu.addSeparator()
        self.persist_action = QAction("在配置中保存密码", self)
        self.persist_action.setCheckable(True)
        self.persist_action.setChecked(True)
        self.persist_action.setToolTip("关闭后，密码只保留在本次界面中；请复制保存完成时的密码清单。")
        self.persist_action.toggled.connect(self.changed)
        self.menu.addAction(self.persist_action)
        self.button.clicked.connect(
            lambda: self.menu.exec(self.button.mapToGlobal(self.button.rect().bottomLeft()))
        )
        row.addWidget(self.button)

    def set_path(self, path: Path) -> None:
        self.name_label.setText(path.name)
        self.name_label.setToolTip(str(path))

    def set_status(self, message: str) -> None:
        self.state_label.setText(message)
        self.state_label.setToolTip(message)

    def collect(self, config: AppConfig) -> AppConfig:
        return replace(config, persist_passwords=self.persist_action.isChecked())

    def apply(self, config: AppConfig) -> None:
        self.persist_action.setChecked(config.persist_passwords)
