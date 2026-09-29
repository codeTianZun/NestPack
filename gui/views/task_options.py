"""压缩任务选项：隐私处理、自检与产物清理。"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout
from qfluentwidgets import CheckBox

from core.models import AppConfig
from gui.views.widgets import CollapsibleSection


class TaskOptionsPanel(CollapsibleSection):
    """收集作用于整次压缩的选项，并展示已启用项。"""

    changed = Signal()

    def __init__(self) -> None:
        super().__init__("任务选项")
        self._checks: dict[str, CheckBox] = {}
        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        for index, (key, title, hint) in enumerate(
            (
                ("verify_after_compress", "压缩后自检每一层", "调用归档工具检查本层产物。"),
                (
                    "delete_inner_after_verify",
                    "自检通过后删除上一层",
                    "删除已包裹的内层，节省磁盘。",
                ),
                ("add_padding", "每层加入随机填充文件", "加入随机内容，使体积和内容特征发生变化。"),
                ("randomize_layer_names", "各层随机文件名", "开始压缩前生成层名并保存到当前配置。"),
                ("hide_source_name", "隐藏来源名称", "第一层以随机别名打包；文件夹会先整体复制。"),
                ("cleanup_on_failure", "失败或取消时清理本次产物", "清理本任务已发布的层产物。"),
            )
        ):
            check = CheckBox(title)
            check.setToolTip(hint)
            self._checks[key] = check
            grid.addWidget(check, index // 2, index % 2)
        self.body_layout.addLayout(grid)
        verify = self._checks["verify_after_compress"]
        delete = self._checks["delete_inner_after_verify"]
        delete.toggled.connect(lambda value: verify.setChecked(True) if value else None)
        verify.toggled.connect(lambda value: delete.setChecked(False) if not value else None)
        for check in self._checks.values():
            check.toggled.connect(self._updated)

    def _updated(self) -> None:
        labels = [check.text() for check in self._checks.values() if check.isChecked()]
        self.set_summary(f"已启用 {len(labels)} 项" if labels else "")
        self.toggle.setToolTip("\n".join(labels))
        self.changed.emit()

    def random_names_enabled(self) -> bool:
        return self._checks["randomize_layer_names"].isChecked()

    def collect(self, config: AppConfig) -> AppConfig:
        return replace(config, **{key: check.isChecked() for key, check in self._checks.items()})

    def apply(self, config: AppConfig) -> None:
        for key, check in self._checks.items():
            check.setChecked(getattr(config, key))
