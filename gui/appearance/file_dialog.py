"""文件选择器的中文文案、导航展示与主题装饰。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QAbstractItemModel, QObject, QSize, QStandardPaths, Qt, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialogButtonBox,
    QFileDialog,
    QListView,
    QSplitter,
    QToolBar,
    QToolButton,
    QTreeView,
)
from qfluentwidgets import FluentIcon

from gui.appearance.file_dialog_style import FILE_DIALOG_STYLE
from gui.appearance.theme import ACCENT, create_app_icon

_SYSTEM_LOCATIONS = (
    (QStandardPaths.StandardLocation.DesktopLocation, "桌面", FluentIcon.APPLICATION),
    (QStandardPaths.StandardLocation.DownloadLocation, "下载", FluentIcon.DOWNLOAD),
    (QStandardPaths.StandardLocation.DocumentsLocation, "文档", FluentIcon.DOCUMENT),
    (QStandardPaths.StandardLocation.HomeLocation, "主目录", FluentIcon.HOME),
)

# QFileDialog 的侧栏和查找范围使用 QUrlModel.UrlRole。
_URL_ROLE = Qt.ItemDataRole.UserRole + 1

# 工具栏按钮 objectName → 中文 tooltip（DontUseNativeDialog 下不加载翻译）。
_TOOLBAR_ACTIONS = {
    "backButton": ("后退", FluentIcon.LEFT_ARROW),
    "forwardButton": ("前进", FluentIcon.RIGHT_ARROW),
    "toParentButton": ("上一级", FluentIcon.UP),
    "newFolderButton": ("新建文件夹", FluentIcon.FOLDER_ADD),
    "listModeButton": ("列表视图", FluentIcon.TILES),
    "detailModeButton": ("详细视图", FluentIcon.MENU),
}


def _relabel_dialog(dialog: QFileDialog, accept_text: str) -> None:
    """改 QFileDialog 各内置 label 为中文，并给确认按钮打主样式标记。"""
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setLabelText(QFileDialog.DialogLabel.LookIn, "地址")
    dialog.setLabelText(QFileDialog.DialogLabel.FileName, "文件名")
    dialog.setLabelText(QFileDialog.DialogLabel.FileType, "文件类型")
    dialog.setLabelText(QFileDialog.DialogLabel.Accept, accept_text)
    dialog.setLabelText(QFileDialog.DialogLabel.Reject, "取消")
    # 通过 objectName 为确认按钮应用主样式。
    button_box = dialog.findChild(QDialogButtonBox, "buttonBox")
    if button_box is not None:
        accept_button = button_box.button(
            QDialogButtonBox.StandardButton.Save
            if dialog.acceptMode() == QFileDialog.AcceptMode.AcceptSave
            else QDialogButtonBox.StandardButton.Open
        )
        if accept_button is not None:
            accept_button.setObjectName("primaryButton")


class _NavigationAppearance(QObject):
    """在 Qt 更新导航位置后保持中文名称与 Fluent 图标。"""

    def __init__(self, model: QAbstractItemModel) -> None:
        super().__init__(model)
        self._model = model
        self._updating = False
        self._locations = {
            Path(path): (label, icon)
            for location, label, icon in _SYSTEM_LOCATIONS
            if (path := QStandardPaths.writableLocation(location))
        }
        self._icons = {
            icon: icon.icon(color=ACCENT)
            for icon in (*[entry[2] for entry in _SYSTEM_LOCATIONS], FluentIcon.FOLDER)
        }
        model.dataChanged.connect(self._refresh)
        model.rowsInserted.connect(self._refresh)
        model.modelReset.connect(self._refresh)
        self._refresh()

    def _refresh(self, *_args) -> None:
        if self._updating:
            return
        self._updating = True
        try:
            for row in range(self._model.rowCount()):
                index = self._model.index(row, 0)
                url = index.data(_URL_ROLE)
                if not isinstance(url, QUrl) or not url.isLocalFile():
                    continue
                path = Path(url.toLocalFile())
                label, symbol = self._locations.get(path, (None, FluentIcon.FOLDER))
                if label is not None and index.data(Qt.ItemDataRole.DisplayRole) != label:
                    self._model.setData(index, label, Qt.ItemDataRole.DisplayRole)
                icon = self._icons[symbol]
                current = index.data(Qt.ItemDataRole.DecorationRole)
                if not isinstance(current, QIcon) or current.cacheKey() != icon.cacheKey():
                    self._model.setData(index, icon, Qt.ItemDataRole.DecorationRole)
                tooltip = str(path)
                if index.data(Qt.ItemDataRole.ToolTipRole) != tooltip:
                    self._model.setData(index, tooltip, Qt.ItemDataRole.ToolTipRole)
        finally:
            self._updating = False


def _localize_sidebar(dialog: QFileDialog) -> None:
    """统一侧栏与导航模型里的位置名称、图标和完整路径提示。"""
    sidebar = dialog.findChild(QListView, "sidebar")
    if sidebar is not None:
        _NavigationAppearance(sidebar.model())
        sidebar.setIconSize(QSize(18, 18))
        sidebar.setSpacing(2)
        sidebar.setWordWrap(False)
        sidebar.setTextElideMode(Qt.TextElideMode.ElideRight)
        sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sidebar.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    look_in = dialog.findChild(QComboBox, "lookInCombo")
    if look_in is not None:
        _NavigationAppearance(look_in.model())
        look_in.setIconSize(QSize(18, 18))


def _localize_toolbar(dialog: QFileDialog) -> None:
    """使用 Fluent 导航图标和中文提示。"""
    for toolbar in dialog.findChildren(QToolBar):
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    for obj_name, (tip, icon) in _TOOLBAR_ACTIONS.items():
        button = dialog.findChild(QToolButton, obj_name)
        if button is not None:
            button.setToolTip(tip)
            button.setText(tip)
            button.setAccessibleName(tip)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setIcon(icon.icon(color=ACCENT))
            button.setIconSize(QSize(18, 18))


def _enable_scrollbars(dialog: QFileDialog) -> None:
    """让列表视图与详细视图的滚动条按需出现。

    QFileDialog 内部的 listView/treeView 默认把水平滚动条策略设为
    ScrollBarAlwaysOff，长文件名超长时只能被省略号截断、无法左右
    滚动查看；改成 ScrollBarAsNeeded 后，水平/垂直滚动条在内容超出
    视口时自动出现。
    """
    policy = Qt.ScrollBarPolicy.ScrollBarAsNeeded
    list_view = dialog.findChild(QListView, "listView")
    if list_view is not None:
        list_view.setHorizontalScrollBarPolicy(policy)
        list_view.setVerticalScrollBarPolicy(policy)
    tree_view = dialog.findChild(QTreeView)
    if tree_view is not None:
        tree_view.setHorizontalScrollBarPolicy(policy)
        tree_view.setVerticalScrollBarPolicy(policy)


def _size_dialog(dialog: QFileDialog, size: tuple[int, int]) -> None:
    """在屏幕可用空间内恢复指定尺寸，并设置紧凑的侧栏宽度。"""
    available = dialog.screen().availableGeometry().adjusted(24, 24, -24, -24)
    dialog.setMinimumSize(min(560, available.width()), min(360, available.height()))
    dialog.resize(min(size[0], available.width()), min(size[1], available.height()))
    sidebar = dialog.findChild(QListView, "sidebar")
    if sidebar is not None:
        sidebar.setMinimumWidth(144)
    splitter = dialog.findChild(QSplitter, "splitter")
    if splitter is not None:
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([184, max(1, dialog.width() - 220)])


def style_file_dialog(
    dialog: QFileDialog, *, tip: str, accept_text: str, size: tuple[int, int],
) -> None:
    """装饰已设定侧栏位置的 Qt 文件选择器。"""
    _relabel_dialog(dialog, accept_text)
    dialog.setStyleSheet(FILE_DIALOG_STYLE)
    dialog.setWindowIcon(create_app_icon())
    _localize_sidebar(dialog)
    _localize_toolbar(dialog)
    _enable_scrollbars(dialog)
    dialog.setWindowTitle(f"NestPack · {tip}")
    _size_dialog(dialog, size)
