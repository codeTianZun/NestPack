"""主窗口：压缩和解包工作区、层编辑与右侧输出及任务区域。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import PushButton

from core.config import validate_archive_name
from core.filesystem import normalize_user_path
from core.models import COMPRESS_MODE_SEPARATE
from gui.appearance.logo import LogoState
from gui.appearance.theme import APP_NAME, STYLE_SHEET, create_app_icon, load_application_fonts
from gui.views.config_bar import ConfigBar
from gui.views.dialogs import show_error, show_info, show_licenses
from gui.views.layers_panel import LayersPanel
from gui.views.output_panel import OutputPanel
from gui.views.settings_dialog import SettingsDialog
from gui.views.side_panel import SidePanel
from gui.views.source_panel import SourcePanel
from gui.views.task_options import TaskOptionsPanel
from gui.views.unpack_panel import UnpackPanel


class MainWindow(QMainWindow):
    """管理界面归属与展示，任务执行由应用协调。"""

    close_requested = Signal(object)
    workspace_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._config_dir = Path.cwd()
        self._active_kind: str | None = None
        self.setWindowTitle(f"{APP_NAME} · 多层嵌套压缩")
        self.setWindowIcon(create_app_icon())
        self.resize(1240, 820)
        self.setMinimumSize(940, 600)
        load_application_fonts()
        self.setStyleSheet(STYLE_SHEET)
        self.source = SourcePanel()
        self.layers = LayersPanel()
        self.output = OutputPanel()
        self.options = TaskOptionsPanel()
        self.settings = SettingsDialog(self)
        self.config_bar = ConfigBar()
        self.unpack = UnpackPanel()
        self.side = SidePanel()
        self._build_ui()
        self.source.paths_changed.connect(self._sources_changed)
        self.source.mode_changed.connect(self._mode_changed)
        self.layers.add_requested.connect(self.add_layer)
        self.layers.card_changed.connect(self.update_summary)
        self.layers.cards_changed.connect(self._mode_changed)
        self.layers.selection_changed.connect(lambda: self._show_compress_details(0))
        self.output.directory_changed.connect(self.source.set_default_output_directory)
        self.output.changed.connect(self.update_summary)
        self.options.changed.connect(self.update_summary)
        self.side.open_output_requested.connect(self.open_output_directory)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QFrame()
        header.setObjectName("appHeader")
        row = QHBoxLayout(header)
        row.setContentsMargins(24, 4, 24, 0)
        row.setSpacing(20)
        title = QLabel(APP_NAME)
        title.setObjectName("appName")
        row.addWidget(title)
        self.navigation = QButtonGroup(self)
        for index, title in enumerate(("压缩", "解包")):
            button = QPushButton(title)
            button.setObjectName("workspaceTab")
            button.setCheckable(True)
            button.setChecked(index == 0)
            self.navigation.addButton(button, index)
            button.clicked.connect(
                lambda _checked=False, value=index: self._switch_workspace(value)
            )
            row.addWidget(button)
        row.addStretch(1)
        self.settings_button = PushButton("设置")
        self.settings_button.clicked.connect(self._show_settings)
        row.addWidget(self.settings_button)
        about = PushButton("关于/许可")
        about.clicked.connect(lambda: show_licenses(self))
        row.addWidget(about)
        layout.addWidget(header)
        layout.addWidget(self.config_bar)
        content = QSplitter(Qt.Orientation.Horizontal)
        content.setChildrenCollapsible(False)
        self.workspaces = QStackedWidget()
        compress = QWidget()
        editor = QVBoxLayout(compress)
        editor.setContentsMargins(24, 20, 24, 20)
        editor.setSpacing(24)
        editor.addWidget(self.source)
        editor.addWidget(self.layers)
        editor.addWidget(self.options)
        editor.addStretch(1)
        self.workspaces.addWidget(self._scroll(compress))
        unpack = QWidget()
        unpack_layout = QVBoxLayout(unpack)
        unpack_layout.setContentsMargins(24, 20, 24, 20)
        unpack_layout.addWidget(self.unpack)
        self.workspaces.addWidget(self._scroll(unpack))
        self.workspaces.setMinimumWidth(420)
        content.addWidget(self.workspaces)

        delivery = QFrame()
        delivery.setObjectName("deliveryPanel")
        delivery.setMinimumWidth(420)
        delivery_layout = QVBoxLayout(delivery)
        delivery_layout.setContentsMargins(20, 20, 20, 16)
        delivery_layout.setSpacing(16)
        self.outputs = QStackedWidget()
        compress_details = QWidget()
        details_layout = QVBoxLayout(compress_details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(16)
        detail_tabs = QHBoxLayout()
        self.detail_navigation = QButtonGroup(self)
        for index, title in enumerate(("层设置", "任务输出")):
            button = QPushButton(title)
            button.setObjectName("detailTab")
            button.setCheckable(True)
            button.setChecked(index == 0)
            self.detail_navigation.addButton(button, index)
            button.clicked.connect(
                lambda _checked=False, value=index: self._show_compress_details(value)
            )
            detail_tabs.addWidget(button)
        details_layout.addLayout(detail_tabs)
        self.compress_details = QStackedWidget()
        self.compress_details.addWidget(self.layers.editors)
        self.compress_details.addWidget(self._scroll(self.output))
        details_layout.addWidget(self.compress_details, 1)
        self.outputs.addWidget(compress_details)
        self.outputs.addWidget(self._scroll(self.unpack.output_panel))
        delivery_layout.addWidget(self.outputs, 1)
        delivery_layout.addWidget(self.side)
        content.addWidget(delivery)
        content.setSizes([660, 580])
        content.setStretchFactor(0, 1)
        content.setStretchFactor(1, 1)
        layout.addWidget(content, 1)

    def _show_compress_details(self, index: int) -> None:
        self.compress_details.setCurrentIndex(index)
        self.detail_navigation.button(index).setChecked(True)

    @staticmethod
    def _scroll(content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    def _show_settings(self) -> None:
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def workspace(self) -> str:
        return "compress" if self.workspaces.currentIndex() == 0 else "unpack"

    def _switch_workspace(self, index: int) -> None:
        self.workspaces.setCurrentIndex(index)
        self.outputs.setCurrentIndex(index)
        self.side.set_workspace(self.workspace())
        self.update_summary()
        self.workspace_changed.emit(self.workspace())

    def set_config_path(self, path: Path) -> None:
        self._config_dir = path.parent
        self.config_bar.set_path(path)
        self.source.set_config_directory(path.parent)
        self.layers.set_config_directory(path.parent)
        self.output.set_config_directory(path.parent)
        self.unpack.set_config_directory(path.parent)
        self.settings.runtime.set_config_directory(path.parent)

    def _sources_changed(self) -> None:
        sources = self.source.paths()
        if sources:
            first = normalize_user_path(sources[0], self._config_dir)
            self.layers.retemplate_defaults(first.stem)
            if not self.output.output_directory():
                self.output.set_output_directory(str(first.parent))
        self._mode_changed()

    def _mode_changed(self) -> None:
        separate = self.source.mode() == COMPRESS_MODE_SEPARATE
        self.layers.set_names_editable(not separate)
        self.layers.set_sources(self.source.paths(), separate)
        self.update_summary()

    def add_layer(self) -> None:
        sources = self.source.paths()
        self.layers.add_card(default_stem=Path(sources[0]).stem if sources else "layer")

    def update_summary(self) -> None:
        layers = self.layers.collect(strict=False)
        if self._active_kind is None:
            self.side.set_summary(
                f"{len(self.source.paths())} 个来源，{len(layers)} 层压缩"
                if self.workspace() == "compress" else "逐层恢复原始文件"
            )
        if not layers:
            self.output.set_preview("添加压缩层后显示最外层名称", "")
            return
        outer = layers[-1]
        name = outer.archive_name
        if self.source.mode() == COMPRESS_MODE_SEPARATE and outer.name_template:
            extension = outer.sfx.extension if outer.sfx.enabled else f".{outer.format}"
            try:
                name = outer.name_template.format(stem="{来源名}") + extension
            except (KeyError, IndexError, AttributeError, ValueError):
                self.output.set_preview("名称模板待完善", "请检查配置中的层名模板。")
                return
        if self.options.random_names_enabled():
            name = "{随机名称}" + (outer.sfx.extension if outer.sfx.enabled else f".{outer.format}")
        if not name:
            self.output.set_preview("请填写最外层名称", "")
            return
        try:
            name = validate_archive_name(
                name, outer.format,
                sfx_extension=outer.sfx.extension if outer.sfx.enabled else None,
            )
        except ValueError as error:
            self.output.set_preview("文件名待完善", str(error))
            return
        if outer.disguise.mode == "video":
            name = Path(name).stem + ".mp4"
        elif outer.disguise.mode == "extension":
            name = Path(name).stem + outer.disguise.extension
        hints = ["最外层名称"]
        if outer.volume_size:
            hints.append(f"分卷大小 {outer.volume_size}")
        if self.options.random_names_enabled():
            hints.append("执行前生成随机名称")
        if self.source.mode() == COMPRESS_MODE_SEPARATE:
            hints.append("每个来源输出一套")
        self.output.set_preview(name or "请填写最外层名称", "，".join(hints))

    def set_task_active(self, kind: str, active: bool) -> None:
        self._active_kind = kind if active else None
        self.config_bar.setEnabled(not active)
        self.settings_button.setEnabled(not active)
        self.settings.setEnabled(not active)
        if active:
            self.settings.hide()
        compression_editable = not active or kind == "unpack"
        self.source.set_editable(compression_editable)
        self.layers.set_editable(compression_editable)
        self.output.setEnabled(compression_editable)
        self.options.setEnabled(compression_editable)
        self.unpack.set_editable(not active or kind == "compress")
        self.side.set_active(active, cancellable=kind in ("compress", "unpack"))
        if not active:
            self.update_summary()

    def set_status(self, message: str, state: LogoState | None = None) -> None:
        self.side.set_status(message, state)

    def open_output_directory(self) -> None:
        raw = (
            self.output.output_directory() if self.workspace() == "compress"
            else self.unpack.output_directory()
        )
        if not raw:
            show_info(self, "尚未设置", "请先选择输出目录。")
            return
        path = normalize_user_path(raw, self._config_dir)
        if not path.is_dir():
            show_error(self, "目录不存在", str(path))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.close_requested.emit(event)
