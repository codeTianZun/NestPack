"""单层压缩参数编辑：控件联动、配置收集与默认层名更新。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CheckBox,
    PushButton,
    SpinBox,
)

from core.backends import get_backend
from core.config.validation import parse_layer_config
from core.filesystem import normalize_user_path
from core.models import FORMAT_7Z, FORMAT_RAR, FORMAT_ZIP, LayerConfig
from gui.appearance.theme import SPACE_SM, SPACE_XS
from gui.config.passwords import generate_password
from gui.views.disguise_panel import DisguisePanel
from gui.views.layer_names import LayerNames
from gui.views.sfx_dialog import SfxSettingsDialog
from gui.views.widgets import CollapsibleSection, ComboBox, LineEdit, text_field

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


class LayerEditor(QWidget):
    """右侧单层编辑表单，切换选择时保留字段草稿。"""

    changed = Signal()

    def __init__(self, layer: LayerConfig) -> None:
        super().__init__()
        self.names = LayerNames(layer)
        self._separate = False
        self.sfx_settings = layer.sfx
        self.config_dir = Path.cwd()
        self.password_set_hint = layer.password_set or bool(layer.password)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        body_layout = QVBoxLayout(self)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(12)
        self.scope_label = QLabel()
        self.scope_label.setTextFormat(Qt.TextFormat.PlainText)
        self.scope_label.setWordWrap(True)
        self.scope_label.setObjectName("muted")
        body_layout.addWidget(self.scope_label)
        self.number_label = QLabel()
        self.number_label.setObjectName("sectionTitle")
        self.role_label = QLabel()
        self.role_label.setObjectName("muted")
        heading = QHBoxLayout()
        heading.addWidget(self.number_label)
        heading.addWidget(self.role_label, 1)
        body_layout.addLayout(heading)

        fields = QHBoxLayout()
        fields.setSpacing(SPACE_SM)
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
        self.format_combo.setCurrentIndex(self.format_combo.findData(layer.format))
        self.format_combo.setMinimumWidth(76)
        format_layout.addWidget(self.format_combo)
        fields.addWidget(format_box)
        password_box, self.password_edit, password_line = text_field("密码", layer.password)
        self.password_edit.setEchoMode(LineEdit.EchoMode.Password)
        toggle = PushButton("显示")
        toggle.setCheckable(True)
        toggle.setFixedWidth(52)
        toggle.toggled.connect(lambda checked: self._toggle_password(toggle, checked))
        password_line.addWidget(toggle)
        generate = PushButton("随机")
        generate.setFixedWidth(52)
        generate.setToolTip("生成 16 位随机强密码")
        generate.clicked.connect(self._generate_password)
        password_line.addWidget(generate)
        fields.addWidget(password_box, 3)
        body_layout.addLayout(fields)
        body_layout.addWidget(self.names)
        self.disguise = DisguisePanel(layer.disguise)
        body_layout.addWidget(self.disguise)
        self.disguise.changed.connect(self.changed)

        self.details = CollapsibleSection("高级选项")
        advanced = QHBoxLayout()
        advanced.setSpacing(SPACE_SM)
        level_box = QWidget()
        level_layout = QVBoxLayout(level_box)
        level_layout.setContentsMargins(0, 0, 0, 0)
        level_layout.addWidget(QLabel("压缩级别"))
        self.level_combo = ComboBox()
        for text, value in COMPRESSION_LEVEL_OPTIONS:
            self.level_combo.addItem(text, userData=value)
        self.level_combo.setCurrentIndex(self.level_combo.findData(layer.compression_level))
        self.level_combo.setToolTip("智能自动：第一层采样选择级别，之后的层只存储。")
        level_layout.addWidget(self.level_combo)
        advanced.addWidget(level_box, 1)
        volume_box, self.volume_edit, _ = text_field("分卷大小", layer.volume_size or "")
        self.volume_edit.setPlaceholderText("如 500m，留空不分卷")
        advanced.addWidget(volume_box, 1)
        recovery_box = QWidget()
        recovery_layout = QHBoxLayout(recovery_box)
        recovery_layout.setContentsMargins(0, 0, 0, 0)
        self.recovery_check = CheckBox("恢复记录")
        self.recovery_check.setToolTip("恢复记录只适用于 RAR 格式。")
        self.recovery_check.setChecked(layer.recovery_percent is not None)
        self.recovery_spin = SpinBox()
        self.recovery_spin.setRange(1, 100)
        self.recovery_spin.setSuffix(" %")
        self.recovery_spin.setValue(layer.recovery_percent or 5)
        recovery_layout.addWidget(self.recovery_check)
        recovery_layout.addWidget(self.recovery_spin)
        self.details.body_layout.addLayout(advanced)
        self.details.body_layout.addWidget(recovery_box)
        sfx_row = QHBoxLayout()
        self.sfx_check = CheckBox("RAR 自解压")
        self.sfx_check.setChecked(layer.sfx.enabled)
        self.sfx_button = PushButton("自解压设置…")
        self.sfx_button.clicked.connect(self._edit_sfx)
        self.sfx_label = QLabel()
        self.sfx_label.setWordWrap(True)
        sfx_row.addWidget(self.sfx_check)
        sfx_row.addWidget(self.sfx_button)
        self.details.body_layout.addLayout(sfx_row)
        self.details.body_layout.addWidget(self.sfx_label)
        body_layout.addWidget(self.details)
        body_layout.addStretch(1)
        self.sfx_check.toggled.connect(self._toggle_sfx)
        self.recovery_check.toggled.connect(self.recovery_spin.setEnabled)
        self.recovery_check.toggled.connect(self.changed)
        self.recovery_spin.valueChanged.connect(self.changed)
        self.names.changed.connect(self.changed)
        self.password_edit.textEdited.connect(self._password_edited)
        self.password_edit.textChanged.connect(self.changed)
        self.volume_edit.textChanged.connect(self.changed)
        self.level_combo.currentIndexChanged.connect(self.changed)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        self.changed.connect(self._refresh_details)
        self._sync_recovery()
        self._sync_sfx()
        self._refresh_details()

    def _refresh_details(self) -> None:
        parts = [self.level_combo.currentText()]
        if self.volume_edit.text().strip():
            parts.append("分卷 " + self.volume_edit.text().strip())
        if self.recovery_check.isChecked():
            parts.append(f"恢复记录 {self.recovery_spin.value()}%")
        if self.sfx_settings.enabled:
            parts.append(f"{self.sfx_settings.target.title()} 自解压")
        self.details.set_summary("，".join(parts))
        self.disguise.set_archive_options(self.volume_edit.text().strip(), self.sfx_settings)

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
        self._sync_recovery()
        self._sync_sfx()
        self._update_extension()
        self.changed.emit()

    def _extension(self) -> str:
        return (
            self.sfx_settings.extension if self.sfx_settings.enabled
            else get_backend(self.current_format()).archive_extension
        )

    def _update_extension(self) -> None:
        self.names.set_extension(self._extension())

    def _sync_sfx(self) -> None:
        self.sfx_button.setEnabled(self.sfx_settings.enabled)
        self.sfx_label.setText(
            "自解压需要 RAR 格式，请调整格式或关闭自解压"
            if self.sfx_settings.enabled and self.current_format() != FORMAT_RAR
            else f"交付给 {self.sfx_settings.target.title()} 用户"
            if self.sfx_settings.enabled else ""
        )

    def _toggle_sfx(self, enabled: bool) -> None:
        self.sfx_settings = replace(self.sfx_settings, enabled=enabled)
        self._sync_sfx()
        self._update_extension()
        self.changed.emit()

    def _edit_sfx(self) -> None:
        dialog = SfxSettingsDialog(self, self.sfx_settings, self.config_dir)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.sfx_settings = dialog.values()
            self._sync_sfx()
            self._update_extension()
            self.changed.emit()

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

    def set_number(self, number: int, total: int) -> None:
        self.names.set_number(number)
        self.number_label.setText(f"第 {number} 层")
        self.role_label.setText(
            "打包来源（最外层）" if total == 1 else
            "打包来源" if number == 1 else "最外层" if number == total else "包裹上一层"
        )

    def set_scope(self, text: str) -> None:
        self.scope_label.setText(text)

    def set_config_directory(self, directory: Path) -> None:
        """同步本层素材选择的路径基准。"""
        self.config_dir = directory
        self.disguise.set_config_directory(directory)

    def set_sources(self, sources: list[str], separate: bool, *, template: bool = False) -> None:
        """显示当前来源的层名；默认层编辑提供逐来源载体设置。"""
        self._separate = template
        source = normalize_user_path(sources[0], self.config_dir) if sources else None
        self.names.set_source(source, template=template)
        self.disguise.set_sources(sources, separate and template)

    def collect(self, index: int, *, strict: bool = True) -> LayerConfig:
        """收集字段快照；执行时校验，草稿保留尚未完成的输入。"""
        archive_format = self.current_format()
        password = self.password_edit.text()
        layer = LayerConfig(
            archive_name=self.names.name_edit.text().strip(),
            password=password,
            recovery_percent=(
                self.recovery_spin.value()
                if archive_format == FORMAT_RAR and self.recovery_check.isChecked()
                else None
            ),
            format=archive_format,
            compression_level=self.level_combo.currentData(),
            auto_name=self.names.auto_name,
            volume_size=self.volume_edit.text().strip() or None,
            password_set=self.password_set_hint or bool(password),
            sfx=self.sfx_settings,
            disguise=self.disguise.collect(),
        )
        return parse_layer_config(
            layer.to_json_dict(), index - 1, strict=strict, separate=self._separate,
        )


__all__ = ["COMPRESSION_LEVEL_OPTIONS", "FORMAT_OPTIONS", "LayerEditor"]
