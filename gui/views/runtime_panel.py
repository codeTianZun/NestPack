"""压缩工具路径面板：字段读写、浏览、检测展示与安装动作。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import LineEdit, PushButton

from core.models import AppConfig
from gui.appearance.theme import SPACE_SM
from gui.config.paths import selection_directory
from gui.views.file_dialog import pick_file
from gui.views.widgets import SectionCard
from platforms import resolve_optional_tool


class _ToolPathRow(QWidget):
    """一个工具的路径编辑、文件选择和检测提示。"""

    changed = Signal()

    def __init__(self, title: str, kind: str, file_filter: str, missing_hint: str) -> None:
        super().__init__()
        self._title = title
        self._kind = kind
        self._file_filter = file_filter
        self._missing_hint = missing_hint
        self.config_dir = Path.cwd()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_SM)
        row = QHBoxLayout()
        row.setSpacing(SPACE_SM)
        label = QLabel(title)
        label.setObjectName("fieldLabel")
        label.setMinimumWidth(56)
        row.addWidget(label)
        self.edit = LineEdit()
        self.edit.setText("auto")
        row.addWidget(self.edit, 1)
        browse = PushButton("浏览")
        browse.clicked.connect(self._choose)
        row.addWidget(browse)
        layout.addLayout(row)
        self._state = QLabel("正在检测…")
        self._state.setObjectName("muted")
        self._state.setWordWrap(True)
        layout.addWidget(self._state)
        self.edit.textChanged.connect(self._path_edited)
        self.edit.editingFinished.connect(self.detect)

    def _path_edited(self) -> None:
        self._show_state("路径已修改，可点击“重新检测”检查。", "muted")
        self.changed.emit()

    def value(self) -> str:
        return self.edit.text().strip() or "auto"

    def show_detection(self, path: Path | None) -> None:
        """展示工具检测结果与实际支持的格式。"""
        if path is None:
            self._show_state(self._missing_hint, "warning")
        else:
            formats = "（仅支持 7z）" if path.name.lower() == "7zr.exe" else ""
            self._show_state(f"已检测到：{path}{formats}", "success")

    def detect(self) -> Path | None:
        try:
            path = resolve_optional_tool(self.value(), self.config_dir, self._kind)
        except (ValueError, OSError) as error:
            self._show_state(str(error), "warning")
            return None
        self.show_detection(path)
        return path

    def _show_state(self, text: str, level: str) -> None:
        self._state.setObjectName(level)
        self._state.setText(text)
        self._state.style().unpolish(self._state)
        self._state.style().polish(self._state)

    def _choose(self) -> None:
        start = selection_directory(self.value(), self.config_dir)
        selected = pick_file(
            self, title=f"选择 {self._title} 命令行程序", start_path=str(start),
            file_filter=self._file_filter,
        )
        if selected:
            self.edit.setText(selected)
            self.detect()


class RuntimePanel(SectionCard):
    """管理两种压缩工具，安装执行通过信号交给应用协调。"""

    changed = Signal()
    install_requested = Signal()
    detect_requested = Signal()
    rar_guide_requested = Signal()

    def __init__(self) -> None:
        super().__init__("运行环境", "自动检测 WinRAR 与 7-Zip，也可以手动指定程序。")
        self._winrar = _ToolPathRow(
            "WinRAR", "rar", "WinRAR 程序 (WinRAR.exe Rar.exe);;可执行文件 (*.exe)",
            "未检测到；请查看 WinRAR 安装指引，或手动选择 WinRAR.exe / Rar.exe。",
        )
        self._sevenzip = _ToolPathRow(
            "7-Zip", "7z", "7-Zip 程序 (7z.exe 7za.exe 7zz.exe 7zr.exe);;可执行文件 (*.exe)",
            "未检测到；使用 7z / zip 层前请安装 7-Zip，或点击依赖安装按钮。",
        )
        self._sevenzip.edit.setToolTip(
            "只在层级使用 7z / zip 格式时才会用到（共用同一程序）；auto 为自动检测。"
            "ZIP 需要 7z.exe / 7za.exe / 7zz.exe；7zr.exe 仅支持 7z。"
        )
        for row in (self._winrar, self._sevenzip):
            self.body_layout.addWidget(row)
            row.changed.connect(self.changed)
        install_line = QHBoxLayout()
        detect_button = PushButton("重新检测")
        detect_button.clicked.connect(self.detect_requested)
        install_line.addWidget(detect_button)
        install_line.addStretch(1)
        rar_button = PushButton("WinRAR 安装指引")
        rar_button.clicked.connect(self.rar_guide_requested)
        install_line.addWidget(rar_button)
        self._install_button = PushButton("安装/修复 7-Zip")
        self._install_button.setToolTip(
            "从官方下载并校验 7-Zip，保留许可材料，安装到程序同目录的 dependencies。"
        )
        self._install_button.clicked.connect(self.install_requested)
        install_line.addWidget(self._install_button)
        self.body_layout.addLayout(install_line)

    def set_config_directory(self, directory: Path) -> None:
        """文件选择以当前配置目录为相对路径基准。"""
        for row in (self._winrar, self._sevenzip):
            row.config_dir = directory

    def collect(self, config: AppConfig, *, strict: bool = True) -> AppConfig:
        """收集工具配置；草稿中留空的路径保存为自动检测。"""
        if strict and not self._winrar.edit.text().strip():
            raise ValueError("请填写 WinRAR 路径，或使用 auto")
        winrar, sevenzip = self.tool_paths()
        return replace(config, winrar_path=winrar, sevenzip_path=sevenzip)

    def apply(self, config: AppConfig) -> None:
        self._winrar.edit.setText(config.winrar_path)
        self._sevenzip.edit.setText(config.sevenzip_path)

    def tool_paths(self) -> tuple[str, str]:
        return self._winrar.value(), self._sevenzip.value()

    def detect(self) -> tuple[Path | None, Path | None]:
        return self._winrar.detect(), self._sevenzip.detect()
