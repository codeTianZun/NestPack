"""单层压缩参数编辑：控件联动、配置收集与默认层名更新。"""

from __future__ import annotations

import re
from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CheckBox,
    FluentIcon,
    PushButton,
    SpinBox,
    ToolButton,
)

from core.backends import SUPPORTED_FORMATS, get_backend
from core.config import validate_archive_name, validate_password, validate_volume_size
from core.models import FORMAT_7Z, FORMAT_RAR, FORMAT_ZIP, LayerConfig
from gui.appearance.theme import SPACE_MD, SPACE_SM, SPACE_XS, apply_danger_style
from gui.config.passwords import generate_password
from gui.views.widgets import ComboBox, LineEdit, text_field

# 压缩级别下拉选项：(显示名, 配置值)。
COMPRESSION_LEVEL_OPTIONS = (
    ("智能自动", "auto"),
    ("仅存储", 0),
    ("最快", 1),
    ("较快", 2),
    ("标准", 3),
    ("较好", 4),
    ("最佳", 5),
)

# 压缩格式下拉选项：(显示名, 配置值)。
FORMAT_OPTIONS = (
    ("RAR", FORMAT_RAR),
    ("7z", FORMAT_7Z),
    ("ZIP", FORMAT_ZIP),
)


class LayerCard(QFrame):
    """单层压缩参数编辑卡片。"""

    changed = Signal()
    remove_requested = Signal(object)
    move_requested = Signal(object, int)

    def __init__(self, layer: LayerConfig) -> None:
        super().__init__()
        self.setObjectName("layerCard")
        self.name_template = layer.name_template
        # 记录“该层本应设密码”的标记：persist_passwords=false 的配置
        # 载入时密码为空但标记为真，用户手动改空密码输入框时清除。
        self.password_set_hint = layer.password_set or bool(layer.password)
        # Preferred 允许卡片在字体/缩放变化时纵向扩展，避免内容被裁切。
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM)
        outer.setSpacing(SPACE_SM)

        header = QHBoxLayout()
        header.setSpacing(SPACE_SM)
        self.number_label = QLabel("01")
        self.number_label.setObjectName("layerNumber")
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.number_label)
        header.addStretch(1)
        level_hint = QLabel("级别")
        level_hint.setObjectName("muted")
        header.addWidget(level_hint)
        self.level_combo = ComboBox()
        for text, value in COMPRESSION_LEVEL_OPTIONS:
            self.level_combo.addItem(text, userData=value)
        index = self.level_combo.findData(layer.compression_level)
        self.level_combo.setCurrentIndex(index if index >= 0 else 0)
        self.level_combo.setToolTip(
            "智能自动：第 1 层按内容探测，之后的层只存储不压缩。"
        )
        header.addWidget(self.level_combo)
        for icon, offset, tooltip in (
            (FluentIcon.UP, -1, "向内移动一层"),
            (FluentIcon.DOWN, 1, "向外移动一层"),
        ):
            button = ToolButton(icon)
            button.setToolTip(tooltip)
            button.clicked.connect(
                lambda _checked=False, value=offset: self.move_requested.emit(
                    self, value
                )
            )
            header.addWidget(button)
        remove_button = PushButton("删除")
        apply_danger_style(remove_button)
        remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        header.addWidget(remove_button)
        outer.addLayout(header)

        # 字段分两行排布，避免窄窗口下各控件被挤压裁切。
        # 两行总 stretch 均为 10，且 6/10 处为分界：name 右边界对齐 recovery
        # 右边界、password 左边界对齐 volume 左边界，形成纵向网格对齐。
        fields = QHBoxLayout()
        fields.setSpacing(SPACE_SM)
        name_box, self.name_edit, _name_line = text_field(
            "压缩包名称", layer.archive_name
        )
        self.name_edit.setMinimumWidth(150)
        fields.addWidget(name_box, 6)

        password_box, self.password_edit, password_line = text_field(
            "密码", layer.password
        )
        self.password_edit.setEchoMode(LineEdit.EchoMode.Password)
        toggle = PushButton("显示")
        toggle.setCheckable(True)
        toggle.setToolTip("显示或隐藏密码")
        toggle.toggled.connect(
            lambda checked: self._toggle_password(toggle, checked)
        )
        password_line.addWidget(toggle)
        generate_button = PushButton("随机")
        generate_button.setToolTip("生成 16 位随机强密码并填入")
        generate_button.clicked.connect(self._generate_password)
        password_line.addWidget(generate_button)
        fields.addWidget(password_box, 4)
        outer.addLayout(fields)

        fields_row2 = QHBoxLayout()
        fields_row2.setSpacing(SPACE_SM)
        format_box = QWidget()
        format_layout = QVBoxLayout(format_box)
        format_layout.setContentsMargins(0, 0, 0, 0)
        format_layout.setSpacing(SPACE_XS)
        format_label = QLabel("格式")
        format_label.setObjectName("fieldLabel")
        format_layout.addWidget(format_label)
        self.format_combo = ComboBox()
        for text, value in FORMAT_OPTIONS:
            self.format_combo.addItem(text, userData=value)
        format_index = self.format_combo.findData(layer.format)
        self.format_combo.setCurrentIndex(format_index if format_index >= 0 else 0)
        self.format_combo.setToolTip(
            "该层的压缩格式；rar 以外的格式没有恢复记录，"
            "zip 层的密码仅支持 ASCII 字符（7-Zip 限制）。"
        )
        format_layout.addWidget(self.format_combo)
        fields_row2.addWidget(format_box, 3)

        recovery_box = QWidget()
        recovery_layout = QVBoxLayout(recovery_box)
        recovery_layout.setContentsMargins(0, 0, 0, 0)
        recovery_layout.setSpacing(SPACE_XS)
        recovery_label = QLabel("恢复记录")
        recovery_label.setObjectName("fieldLabel")
        recovery_layout.addWidget(recovery_label)
        recovery_line = QHBoxLayout()
        recovery_line.setContentsMargins(0, 0, 0, 0)
        recovery_line.setSpacing(SPACE_SM)
        self.recovery_check = CheckBox("启用")
        self.recovery_check.setChecked(layer.recovery_percent is not None)
        self.recovery_spin = SpinBox()
        self.recovery_spin.setRange(1, 100)
        self.recovery_spin.setSuffix(" %")
        self.recovery_spin.setValue(layer.recovery_percent or 5)
        recovery_line.addWidget(self.recovery_check)
        recovery_line.addWidget(self.recovery_spin)
        recovery_layout.addLayout(recovery_line)
        fields_row2.addWidget(recovery_box, 3)

        volume_box, self.volume_edit, _volume_line = text_field(
            "分卷大小", layer.volume_size or ""
        )
        self.volume_edit.setPlaceholderText("如 500m，留空不分卷")
        self.volume_edit.setToolTip(
            "把本层压缩包切分成固定大小的分卷（同 WinRAR -v 参数），"
            "适配网盘单文件大小限制；如 500k、100m、1g。"
        )
        fields_row2.addWidget(volume_box, 4)
        outer.addLayout(fields_row2)

        self.recovery_check.toggled.connect(self.recovery_spin.setEnabled)
        self.recovery_check.toggled.connect(self.changed)
        self.recovery_spin.valueChanged.connect(self.changed)
        self.name_edit.textEdited.connect(self._name_edited)
        self.name_edit.textChanged.connect(self.changed)
        self.password_edit.textEdited.connect(self._password_edited)
        self.password_edit.textChanged.connect(self.changed)
        self.volume_edit.textChanged.connect(self.changed)
        self.level_combo.currentIndexChanged.connect(self.changed)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        self._sync_recovery()

    def current_format(self) -> str:
        """当前选择的压缩格式（"rar" / "7z" / "zip"）。"""
        value = self.format_combo.currentData()
        return value if isinstance(value, str) else FORMAT_RAR

    def _sync_recovery(self) -> None:
        """按当前格式同步恢复记录控件。"""
        is_rar = self.current_format() == FORMAT_RAR
        self.recovery_check.setEnabled(is_rar)
        if not is_rar:
            self.recovery_check.setChecked(False)
        self.recovery_spin.setEnabled(is_rar and self.recovery_check.isChecked())

    def _on_format_changed(self) -> None:
        """切换格式：非 rar 禁用恢复记录，名称后缀跟随格式互换。"""
        archive_format = self.current_format()
        self._sync_recovery()
        current_name = self.name_edit.text().strip()
        new_extension = get_backend(archive_format).archive_extension
        for other_format in SUPPORTED_FORMATS:
            if other_format == archive_format:
                continue
            other_extension = get_backend(other_format).archive_extension
            if current_name.lower().endswith(other_extension):
                # setText 不触发 textEdited，来源模板标记得以保留。
                self.name_edit.setText(
                    current_name[: -len(other_extension)] + new_extension
                )
                break
        self.changed.emit()

    def _name_edited(self, _text: str) -> None:
        """用户手动改过文件名后视为自定义名称，不再按来源模板替换。"""
        self.name_template = None

    def _password_edited(self, _text: str) -> None:
        """用户手动改过密码输入框后，按输入框内容刷新密码标记。"""
        self.password_set_hint = bool(self.password_edit.text())

    def _generate_password(self) -> None:
        """填入随机强密码并标记该层需要密码（setText 不触发 textEdited）。"""
        self.password_edit.setText(generate_password())
        self.password_set_hint = True

    def _toggle_password(self, button: PushButton, visible: bool) -> None:
        self.password_edit.setEchoMode(
            LineEdit.EchoMode.Normal if visible else LineEdit.EchoMode.Password
        )
        button.setText("隐藏" if visible else "显示")

    def set_number(self, number: int) -> None:
        self.number_label.setText(f"{number:02d}")

    def set_name(self, name: str) -> None:
        """程序化设置文件名；不触发 textEdited，保留来源模板。"""
        self.name_edit.setText(name)

    def set_name_editable(self, editable: bool) -> None:
        """separate 模式下文件名自动按来源生成，禁止手动修改。"""
        self.name_edit.setEnabled(editable)
        self.name_edit.setToolTip(
            "分别打包时每个来源以自己去掉后缀的名字生成压缩包，名称不可修改。"
            if not editable
            else "压缩包的文件名。"
        )

    def collect(self, index: int, *, strict: bool = True) -> LayerConfig:
        """收集字段快照；执行时校验，草稿保留尚未完成的输入。"""
        archive_format = self.current_format()
        password = self.password_edit.text()
        layer = LayerConfig(
            archive_name=self.name_edit.text().strip(),
            password=password,
            recovery_percent=(
                self.recovery_spin.value()
                if archive_format == FORMAT_RAR and self.recovery_check.isChecked()
                else None
            ),
            format=archive_format,
            compression_level=self.level_combo.currentData(),
            name_template=self.name_template,
            volume_size=self.volume_edit.text().strip() or None,
            password_set=self.password_set_hint or bool(password),
        )
        try:
            if layer.volume_size is not None:
                validate_volume_size(layer.volume_size)
            validate_password(layer.password, layer.format)
            name = validate_archive_name(layer.archive_name, layer.format)
        except ValueError:
            if strict:
                raise
            name = layer.archive_name or (
                f"layer_{index}{get_backend(layer.format).archive_extension}"
            )
        return replace(layer, archive_name=name)

    def retemplate_default(self, stem: str, index: int) -> None:
        """按来源更新使用默认模板的名称。"""
        current = self.name_edit.text().strip()
        if self.name_template or re.fullmatch(
            r"layer_\d+\.(?:rar|7z|zip)", current, re.IGNORECASE
        ):
            self.name_template = f"{{stem}}_{index}"
            extension = get_backend(self.current_format()).archive_extension
            self.set_name(f"{stem}_{index}{extension}")


__all__ = ["COMPRESSION_LEVEL_OPTIONS", "FORMAT_OPTIONS", "LayerCard"]
