"""任务来源面板：文件和目录选择、拖放与打包方式。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QWidget,
)
from qfluentwidgets import FluentIcon, ListWidget, PushButton, ToolButton

from core.filesystem import normalize_user_path
from core.models import COMPRESS_MODE_COMBINED, COMPRESS_MODE_SEPARATE, AppConfig
from gui.appearance.theme import SPACE_SM
from gui.config.paths import selection_directory
from gui.views.file_dialog import pick_sources
from gui.views.widgets import (
    FIELD_LABEL_WIDTH,
    ComboBox,
    SectionCard,
)


class SourceDropList(ListWidget):
    """接受文件/文件夹拖放的来源列表（拖入即添加，去重由面板处理）。"""

    #: 拖入的本地路径交给来源面板去重追加。
    paths_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(ListWidget.DragDropMode.DropOnly)

    def _has_local_urls(self, event) -> bool:
        mime = event.mimeData()
        return mime.hasUrls() and any(url.isLocalFile() for url in mime.urls())

    def dragEnterEvent(self, event) -> None:
        if self._has_local_urls(event):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if self._has_local_urls(event):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if self._has_local_urls(event):
            paths = [
                url.toLocalFile()
                for url in event.mimeData().urls()
                if url.isLocalFile()
            ]
            if paths:
                self.paths_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class SourcePanel(SectionCard):
    """管理来源列表及合并、分别打包方式。"""

    #: 来源集合更新完成，供层名联动、概览和配置保存使用。
    paths_changed = Signal()
    #: 打包方式下拉切换。
    mode_changed = Signal()
    selection_changed = Signal()

    def __init__(self) -> None:
        super().__init__("来源文件", "添加文件或文件夹，也可以拖入下方列表。")
        self._config_dir = Path.cwd()
        self._default_output = ""
        self._build_list()
        self._build_buttons()
        self._build_mode_row()
        self.paths_changed.connect(self._fit_list_height)

    def _build_list(self) -> None:
        """来源列表：单选切换编辑来源，拖放添加，行尾删除。"""
        self.source_list = SourceDropList()
        self.source_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.source_list.setFixedHeight(64)
        self.source_list.setToolTip(
            "可拖入文件或文件夹；分别打包时，点击来源编辑它的压缩层。"
        )
        self.body_layout.addWidget(self.source_list)
        self.source_list.paths_dropped.connect(self.append_selection)
        self.source_list.currentItemChanged.connect(
            lambda _current, _previous: self._selection_changed()
        )

    def _fit_list_height(self) -> None:
        """按来源数量分配空间，较多来源在列表内滚动。"""
        height = sum(
            self.source_list.item(index).sizeHint().height() + 2 * self.source_list.spacing()
            for index in range(min(3, self.source_list.count()))
        )
        self.source_list.setFixedHeight(max(64, min(144, height + 12)))

    def _build_buttons(self) -> None:
        """添加与清空按钮由本面板处理，完成后发布来源变化。"""
        buttons = QHBoxLayout()
        buttons.setSpacing(SPACE_SM)
        add_button = PushButton("添加来源", None, FluentIcon.ADD)
        add_button.setToolTip("在同一个对话框里同时选择文件或文件夹")
        add_button.clicked.connect(self._choose_sources)
        clear_button = PushButton("清空", None, FluentIcon.BROOM)
        clear_button.setToolTip("清空全部来源")
        clear_button.clicked.connect(self.clear_all)
        buttons.addWidget(add_button)
        buttons.addWidget(clear_button)
        buttons.addStretch(1)
        self.actions.addLayout(buttons)

    def _build_mode_row(self) -> None:
        """打包方式下拉：合并打包 / 分别打包。"""
        row = QHBoxLayout()
        row.setSpacing(SPACE_SM)
        label = QLabel("打包方式")
        label.setObjectName("fieldLabel")
        label.setFixedWidth(FIELD_LABEL_WIDTH)
        row.addWidget(label)
        self.source_mode_combo = ComboBox()
        self.source_mode_combo.addItem("合并打包", userData=COMPRESS_MODE_COMBINED)
        self.source_mode_combo.addItem("分别打包", userData=COMPRESS_MODE_SEPARATE)
        self.source_mode_combo.setToolTip(
            "一起打包：所有来源合并后生成一套压缩包；\n"
            "分别打包：每个来源在输出目录下各自的子文件夹里生成一套压缩包。"
        )
        self.source_mode_combo.currentIndexChanged.connect(self._mode_index_changed)
        row.addWidget(self.source_mode_combo, 1)
        self.body_layout.addLayout(row)

    def _selection_changed(self) -> None:
        if self.mode() == COMPRESS_MODE_SEPARATE:
            self.selection_changed.emit()

    def _mode_index_changed(self, _index: int) -> None:
        """切换来源选择方式，并通知主窗口刷新打包预览。"""
        with QSignalBlocker(self.source_list):
            if self.mode() == COMPRESS_MODE_SEPARATE:
                self.source_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
                if self.source_list.count():
                    self.source_list.setCurrentRow(self.source_list.count() - 1)
            else:
                self.source_list.setCurrentRow(-1)
                self.source_list.clearSelection()
                self.source_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.mode_changed.emit()

    def set_default_output_directory(self, value: str) -> None:
        """为文件选择器提供当前输出目录的快捷入口。"""
        self._default_output = value

    def collect(self, config: AppConfig, *, strict: bool = True) -> AppConfig:
        """把来源与打包方式写入配置快照。"""
        paths = self.paths()
        if strict:
            if not paths:
                raise ValueError("请选择原始文件或文件夹")
        return replace(
            config, source_path=paths[0] if paths else "", source_paths=paths,
            compress_mode=self.mode(),
        )

    def apply(self, config: AppConfig) -> None:
        """回填本面板的配置字段。"""
        self.set_paths(config.effective_source_paths())
        self.set_mode(config.compress_mode)

    def set_config_directory(self, directory: Path) -> None:
        """选择路径时以当前配置目录为基准。"""
        self._config_dir = directory

    def _choose_sources(self) -> None:
        """从最后一个来源所在目录选择并追加来源。"""
        sources = self.paths()
        start = selection_directory(sources[-1] if sources else "", self._config_dir)
        paths = pick_sources(
            self.window(), str(start), default_output=(
                str(normalize_user_path(self._default_output, self._config_dir))
                if self._default_output else ""
            ),
        )
        self.append_selection(paths)

    def append_selection(self, paths: list[str]) -> list[str]:
        """追加用户选择的来源，集合更新后通知主窗口。"""
        return self.add_paths(paths)

    def paths(self) -> list[str]:
        """按列表顺序返回全部来源路径。"""
        return [
            self.source_list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.source_list.count())
        ]

    def set_paths(self, paths: list[str]) -> None:
        """替换来源列表，分别打包时保留已有选择或选中最下方来源。"""
        if paths == self.paths():
            return
        selected = self.selected_path()
        with QSignalBlocker(self.source_list):
            self.source_list.clear()
            for path in paths:
                self._create_item(path)
            if self.mode() == COMPRESS_MODE_SEPARATE and paths:
                selected_path = (
                    normalize_user_path(selected, self._config_dir) if selected else None
                )
                index = next((index for index, path in enumerate(paths)
                              if normalize_user_path(path, self._config_dir) == selected_path),
                             len(paths) - 1)
                self.source_list.setCurrentRow(index)
        self.paths_changed.emit()

    def selected_path(self) -> str | None:
        """当前编辑的来源；未选中时编辑默认层设置。"""
        if self.mode() != COMPRESS_MODE_SEPARATE:
            return None
        item = self.source_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def select_defaults(self) -> None:
        """退出来源选择，显示共用的默认层设置。"""
        self.source_list.setCurrentRow(-1)
        self.source_list.clearSelection()

    def add_paths(self, paths: list[str]) -> list[str]:
        """去重追加来源，返回真正新增的路径；无新增时不改动列表。"""
        existing = {path.casefold() for path in self.paths()}
        added = []
        for path in paths:
            key = path.casefold()
            if key not in existing:
                existing.add(key)
                added.append(path)
        if added:
            with QSignalBlocker(self.source_list):
                was_empty = self.source_list.count() == 0
                for path in added:
                    self._create_item(path)
                if was_empty and self.mode() == COMPRESS_MODE_SEPARATE:
                    self.source_list.setCurrentRow(self.source_list.count() - 1)
            self.paths_changed.emit()
        return added

    def clear_all(self) -> bool:
        """清空来源列表，返回清空前是否非空。"""
        if self.source_list.count() == 0:
            return False
        self.set_paths([])
        return True

    def mode(self) -> str:
        """返回当前打包方式；数据异常时回退为合并打包。"""
        mode = self.source_mode_combo.currentData()
        if mode in (COMPRESS_MODE_COMBINED, COMPRESS_MODE_SEPARATE):
            return mode
        return COMPRESS_MODE_COMBINED

    def set_mode(self, mode: str) -> None:
        """按配置值切换打包方式与来源列表的选择状态。"""
        index = self.source_mode_combo.findData(mode)
        if index >= 0:
            self.source_mode_combo.setCurrentIndex(index)

    def set_editable(self, editable: bool) -> None:
        """按任务状态锁定来源及打包方式。"""
        self.setEnabled(editable)

    def _create_item(self, path: str) -> None:
        """为单个来源创建一行：路径文字 + 行尾删除按钮。"""
        item = QListWidgetItem()
        # 路径存在 UserRole 里，不写入显示文本，避免与行内标签重复渲染出重影。
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(6, 2, 4, 2)
        row_layout.setSpacing(6)
        label = QLabel(Path(path).name or path)
        label.setToolTip(path)
        row_layout.addWidget(label, 1)
        remove_button = ToolButton(FluentIcon.DELETE)
        remove_button.setToolTip("移除该来源")
        remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_button.clicked.connect(
            lambda _checked=False, row=item: self._remove_item(row)
        )
        row_layout.addWidget(remove_button)
        item.setSizeHint(row_widget.sizeHint())
        self.source_list.addItem(item)
        self.source_list.setItemWidget(item, row_widget)

    def _remove_item(self, item: QListWidgetItem) -> None:
        """移除指定的来源行并通知主窗口做联动刷新。"""
        row = self.source_list.row(item)
        if row < 0:
            return
        selected = self.source_list.currentItem() is item
        with QSignalBlocker(self.source_list):
            self.source_list.takeItem(row)
            if selected and self.mode() == COMPRESS_MODE_SEPARATE and self.source_list.count():
                self.source_list.setCurrentRow(self.source_list.count() - 1)
        self.paths_changed.emit()


__all__ = ["SourcePanel"]
