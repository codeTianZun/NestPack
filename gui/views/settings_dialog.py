"""设定对话框：运行环境、任务选项与隐私归档参数的读写和联动。"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import CheckBox, LineEdit

from core.config import validate_disguise_extension
from core.models import AppConfig
from gui.appearance.theme import SPACE_LG, SPACE_MD, SPACE_SM
from gui.views.runtime_panel import RuntimePanel
from gui.views.widgets import SectionCard


class SettingsDialog(QDialog):
    """右上角齿轮按钮弹出的「设定」窗口。

    配置通过 collect/apply 读写，用户改动统一汇聚成 changed 信号。
    """

    #: 任一设置项被用户改动时发出（含互锁勾选引发的连锁变化）。
    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("设定")
        self.setModal(False)
        self.setMinimumWidth(760)
        self.setMinimumHeight(460)
        self.resize(760, 460)

        root = QHBoxLayout(self)
        root.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        root.setSpacing(SPACE_LG)

        left_column = QVBoxLayout()
        left_column.setSpacing(SPACE_MD)
        self.runtime = RuntimePanel()
        self.runtime.changed.connect(self.changed)
        left_column.addWidget(self.runtime)
        left_column.addWidget(self._build_option_card())
        left_column.addStretch(1)
        root.addLayout(left_column, 1)

        root.addWidget(self._build_security_card(), 2)

        self._interlock_verify_and_delete()
        self._connect_changed_signals()

    def _build_option_card(self) -> SectionCard:
        """任务选项卡片：同名压缩包覆盖方式与 WinRAR 界面显示。"""
        card = SectionCard("任务选项", "控制同名压缩包的处理方式。")
        self.overwrite_check = CheckBox("自动覆盖同名压缩包")
        card.body_layout.addWidget(self.overwrite_check)
        self.show_gui_check = CheckBox("显示 WinRAR 压缩界面")
        self.show_gui_check.setChecked(True)
        self.show_gui_check.setToolTip(
            "取消勾选后，压缩时 WinRAR 将在后台运行，不弹出压缩界面。"
        )
        card.body_layout.addWidget(self.show_gui_check)
        return card

    def _build_security_card(self) -> SectionCard:
        """隐私与归档卡片：密码保存、元数据选项、扩展名与自检删除。"""
        card = SectionCard("隐私与归档", "减少归档过程中不必要的元数据暴露。")
        self.persist_passwords_check = CheckBox("在 JSON 中保存密码")
        self.persist_passwords_check.setChecked(True)
        self.persist_passwords_check.setToolTip(
            "取消勾选后，保存配置时密码字段写空，压缩时仍使用界面上当前输入的密码。"
        )
        self.add_padding_check = CheckBox("每层加入随机填充文件")
        self.add_padding_check.setToolTip(
            "每层加入随机生成的填充文件，为独立归档任务生成不同的内容与体积特征。"
        )
        self.randomize_names_check = CheckBox("各层随机文件名")
        self.randomize_names_check.setToolTip(
            "开始压缩时为本层生成随机的 8 位文件名并写入配置。"
        )
        self.hide_source_check = CheckBox("隐藏源文件名（脱敏）")
        self.hide_source_check.setToolTip(
            "第 1 层用随机别名打包原始输入；文件夹会整体复制一份再压缩，"
            "大文件夹需要额外的时间和磁盘空间。"
        )
        self.disguise_check = CheckBox("最外层伪装扩展名")
        self.disguise_check.setToolTip(
            "最外层压缩包使用下方填写的扩展名；解包时会按内容自动识别格式。"
        )
        self.randomize_timestamps_check = CheckBox("随机化最外层时间戳")
        self.randomize_timestamps_check.setToolTip(
            "完成后把最外层文件的修改时间改为最近两年内的随机时刻，"
            "避免时间戳成为关联多次上传的特征。"
        )
        self.verify_check = CheckBox("压缩后自检每个压缩包")
        self.verify_check.setChecked(True)
        self.verify_check.setToolTip(
            "每层完成后调用对应归档工具自检，损坏则失败并保留旧包，代价是耗时增加。"
        )
        self.delete_inner_check = CheckBox("自检通过后删除上一层（省磁盘）")
        self.delete_inner_check.setChecked(True)
        self.delete_inner_check.setToolTip(
            "每层压缩并自检通过后，删除已被它包裹的上一层，只保留最外层；"
            "必须与压缩后自检一起启用，防止删除损坏的中间层。"
        )
        self.cleanup_check = CheckBox("失败时清理已生成压缩包")
        self.cleanup_check.setToolTip("任务中途失败时删除本次已经生成的中间层压缩包。")

        # 双列网格：左列为基础混淆开关，右列为完成与自检开关；
        # disguise_check 与「伪装为」输入行同行成组，两列等宽避免右半留白。
        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACE_LG)
        grid.setVerticalSpacing(SPACE_SM)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.addWidget(self.persist_passwords_check, 0, 0)
        grid.addWidget(self.randomize_timestamps_check, 0, 1)
        grid.addWidget(self.add_padding_check, 1, 0)
        grid.addWidget(self.verify_check, 1, 1)
        grid.addWidget(self.randomize_names_check, 2, 0)
        grid.addWidget(self.delete_inner_check, 2, 1)
        grid.addWidget(self.hide_source_check, 3, 0)
        grid.addWidget(self.cleanup_check, 3, 1)
        grid.addWidget(self.disguise_check, 4, 0)

        extension_row = QHBoxLayout()
        extension_row.setContentsMargins(0, 0, 0, 0)
        extension_row.setSpacing(SPACE_SM)
        extension_label = QLabel("伪装为")
        extension_label.setObjectName("fieldLabel")
        self.disguise_extension_edit = LineEdit()
        self.disguise_extension_edit.setText(".bin")
        self.disguise_extension_edit.setToolTip(
            "以点开头的 1-8 位字母数字，如 .bin、.dat、.pdf。"
        )
        extension_row.addWidget(extension_label)
        extension_row.addWidget(self.disguise_extension_edit, 1)
        grid.addLayout(extension_row, 4, 1)

        card.body_layout.addLayout(grid)
        return card

    def _interlock_verify_and_delete(self) -> None:
        """删除上一层必须依赖自检：勾选删除时强制启用自检，取消自检时同步取消删除。"""
        self.delete_inner_check.toggled.connect(
            lambda checked: (self.verify_check.setChecked(True) if checked else None)
        )
        self.verify_check.toggled.connect(
            lambda checked: (
                self.delete_inner_check.setChecked(False) if not checked else None
            )
        )

    def set_video_fusion(self, enabled: bool) -> None:
        """视频融合产物固定使用 MP4 扩展名。"""
        self.disguise_check.setEnabled(not enabled)
        self.disguise_extension_edit.setEnabled(not enabled)
        self.disguise_check.setToolTip(
            "视频融合成品使用 .mp4 扩展名。" if enabled
            else "最外层压缩包使用指定的扩展名，解包时按内容识别。"
        )

    def _connect_changed_signals(self) -> None:
        """所有设置控件的变化统一汇聚成 changed 信号，供主窗口接自动保存。"""
        self.disguise_extension_edit.textChanged.connect(self.changed.emit)
        for checkbox in (
            self.overwrite_check,
            self.show_gui_check,
            self.persist_passwords_check,
            self.add_padding_check,
            self.randomize_names_check,
            self.hide_source_check,
            self.disguise_check,
            self.randomize_timestamps_check,
            self.verify_check,
            self.cleanup_check,
            self.delete_inner_check,
        ):
            checkbox.toggled.connect(self.changed.emit)

    def collect(self, config: AppConfig, *, strict: bool = True) -> AppConfig:
        """把运行环境与选项写入配置快照。"""
        config = self.runtime.collect(config, strict=strict)
        extension = self.disguise_extension_edit.text().strip() or ".bin"
        if strict:
            validate_disguise_extension(extension)
        return replace(
            config,
            overwrite_existing=self.overwrite_check.isChecked(),
            show_winrar_gui=self.show_gui_check.isChecked(),
            add_padding=self.add_padding_check.isChecked(),
            randomize_layer_names=self.randomize_names_check.isChecked(),
            hide_source_name=self.hide_source_check.isChecked(),
            disguise_outer_extension=self.disguise_check.isChecked(),
            disguise_extension=extension,
            randomize_timestamps=self.randomize_timestamps_check.isChecked(),
            verify_after_compress=self.verify_check.isChecked(),
            cleanup_on_failure=self.cleanup_check.isChecked(),
            persist_passwords=self.persist_passwords_check.isChecked(),
            delete_inner_after_verify=self.delete_inner_check.isChecked(),
        )

    def apply(self, config: AppConfig) -> None:
        """回填设置字段并应用控件间的联动。"""
        self.runtime.apply(config)
        self.overwrite_check.setChecked(config.overwrite_existing)
        self.show_gui_check.setChecked(config.show_winrar_gui)
        self.add_padding_check.setChecked(config.add_padding)
        self.randomize_names_check.setChecked(config.randomize_layer_names)
        self.hide_source_check.setChecked(config.hide_source_name)
        self.disguise_check.setChecked(config.disguise_outer_extension)
        self.disguise_extension_edit.setText(config.disguise_extension)
        self.randomize_timestamps_check.setChecked(config.randomize_timestamps)
        self.verify_check.setChecked(config.verify_after_compress)
        self.cleanup_check.setChecked(config.cleanup_on_failure)
        self.persist_passwords_check.setChecked(config.persist_passwords)
        self.delete_inner_check.setChecked(config.delete_inner_after_verify)
