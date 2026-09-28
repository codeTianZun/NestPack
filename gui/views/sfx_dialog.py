"""逐层自解压设置：交付目标、品牌素材与解压后的命令。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    ComboBox,
    LineEdit,
    PlainTextEdit,
    PrimaryPushButton,
    PushButton,
    ScrollArea,
)

from core.models import SfxConfig
from gui.config.paths import selection_directory
from gui.views.file_dialog import pick_sfx_resource
from gui.views.widgets import path_row


class SfxSettingsDialog(QDialog):
    """编辑时保留所有字段，执行时由共享计划校验目标能力和冲突。"""

    def __init__(self, parent: QWidget, settings: SfxConfig, config_dir: Path) -> None:
        super().__init__(parent)
        self.setWindowTitle("RAR 自解压设置")
        self.resize(760, 680)
        self._settings = settings
        self._config_dir = config_dir
        self._editors: dict[str, LineEdit] = {}
        root = QVBoxLayout(self)
        hint = QLabel(
            "交付目标由接收者的系统决定。Windows 可显示品牌界面；Linux 使用终端自解压。\n"
            "服务器生成 Windows 包时，可复用在 Windows 制作的品牌样包。"
        )
        hint.setWordWrap(True)
        root.addWidget(hint)
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        rows = QVBoxLayout(content)
        self.target = ComboBox()
        for label, value in (("Windows", "windows"), ("Linux", "linux")):
            self.target.addItem(label, userData=value)
        self.target.setCurrentIndex(self.target.findData(settings.target))
        rows.addWidget(QLabel("接收者系统"))
        rows.addWidget(self.target)
        for key, label, placeholder in (
            ("template_path", "模板", "auto，或官方模块 / 品牌样包路径"),
            ("icon_path", "图标", "ICO；留空沿用模板，修改需 Windows WinRAR.exe"),
            ("logo_path", "Logo", "PNG / BMP；留空沿用模板"),
            ("title", "标题", "留空使用模块默认标题"),
            ("extract_path", "解压路径", "接收者电脑上的默认路径，留空由接收者选择"),
            ("setup", "启动命令", '如 cmd.exe /c start "" "https://example.com"'),
        ):
            editor = LineEdit()
            editor.setText(getattr(settings, key))
            editor.setPlaceholderText(placeholder)
            self._editors[key] = editor
            buttons = (
                (("浏览", lambda checked=False, field=key: self._choose(field)),)
                if key in ("template_path", "icon_path", "logo_path") else ()
            )
            rows.addLayout(path_row(label, editor, buttons))
        command_hint = QLabel(
            "启动命令留空表示仅解压；成功解压本层后执行，工作目录是解压目录。"
            "命令原样写入，文件名和参数由你填写。每个自解压文件只解开自己这一层。"
        )
        command_hint.setWordWrap(True)
        rows.addWidget(command_hint)
        rows.addWidget(QLabel("界面说明（可多行）"))
        self.text = PlainTextEdit()
        self.text.setPlainText(settings.text)
        self.text.setMinimumHeight(120)
        rows.addWidget(self.text)
        self.overwrite = ComboBox()
        for label, value in (("询问", "ask"), ("覆盖", "overwrite"), ("跳过", "skip")):
            self.overwrite.addItem(label, userData=value)
        self.overwrite.setCurrentIndex(self.overwrite.findData(settings.overwrite))
        rows.addWidget(QLabel("接收者解压时遇到同名文件"))
        rows.addWidget(self.overwrite)
        self.silent = ComboBox()
        for label, value in (
            ("正常显示", "show"), ("隐藏开始窗口", "hide_start"), ("隐藏全部窗口", "hide_all"),
        ):
            self.silent.addItem(label, userData=value)
        self.silent.setCurrentIndex(self.silent.findData(settings.silent))
        rows.addWidget(QLabel("Windows 自解压窗口"))
        rows.addWidget(self.silent)
        linux_hint = QLabel(
            "Linux 目标使用模板默认的终端行为，以上 Windows 品牌和行为字段应留空，"
            "覆盖和窗口选项保持默认。切换目标会保留输入，执行前提示冲突。"
        )
        linux_hint.setWordWrap(True)
        rows.addWidget(linux_hint)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)
        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)
        apply = PrimaryPushButton("应用")
        apply.clicked.connect(self.accept)
        cancel = PushButton("取消")
        cancel.clicked.connect(self.reject)
        buttons_row.addWidget(apply)
        buttons_row.addWidget(cancel)
        root.addLayout(buttons_row)

    def _choose(self, key: str) -> None:
        editor = self._editors[key]
        start = selection_directory(editor.text(), self._config_dir)
        selected = pick_sfx_resource(self, str(start), key)
        if selected:
            editor.setText(selected)

    def values(self) -> SfxConfig:
        """返回对话框中的草稿；命令保留用户输入的空格和引号。"""
        return replace(
            self._settings,
            target=self.target.currentData(),
            text=self.text.toPlainText(),
            overwrite=self.overwrite.currentData(),
            silent=self.silent.currentData(),
            **{key: editor.text() for key, editor in self._editors.items()},
        )
