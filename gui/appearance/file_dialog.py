"""文件选择器的中文文案、导航展示与主题装饰。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QAbstractItemModel, Qt, QUrl
from PySide6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QFileDialog,
    QListView,
    QToolBar,
    QToolButton,
    QTreeView,
)

from gui.appearance.file_dialog_style import FILE_DIALOG_STYLE
from gui.appearance.theme import create_app_icon

# 系统目录名 → 中文显示名（仅本地化侧栏与查找范围里的系统位置）。
_SIDEBAR_CN = {
    "Desktop": "桌面",
    "Documents": "文档",
    "Downloads": "下载",
}

# 工具栏按钮 objectName → 中文 tooltip（DontUseNativeDialog 下不加载翻译）。
_TOOLBAR_TIPS = {
    "backButton": "后退",
    "forwardButton": "前进",
    "parentButton": "上一级",
    "newFolderButton": "新建文件夹",
    "listModeButton": "列表视图",
    "detailModeButton": "详细视图",
}


def _relabel_dialog(dialog: QFileDialog, accept_text: str) -> None:
    """改 QFileDialog 各内置 label 为中文，并给确认按钮打主样式标记。"""
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setLabelText(QFileDialog.DialogLabel.LookIn, "查找范围")
    dialog.setLabelText(QFileDialog.DialogLabel.FileName, "文件名")
    dialog.setLabelText(QFileDialog.DialogLabel.FileType, "文件类型")
    dialog.setLabelText(QFileDialog.DialogLabel.Accept, accept_text)
    dialog.setLabelText(QFileDialog.DialogLabel.Reject, "取消")
    # [text=...] 属性选择器对 QPushButton 不生效，改用 objectName 触发主样式
    button_box = dialog.findChild(QDialogButtonBox, "buttonBox")
    if button_box is not None:
        accept_button = button_box.button(
            QDialogButtonBox.StandardButton.Open
        )
        if accept_button is not None:
            accept_button.setObjectName("primaryButton")


def _localize_url_model(model: QAbstractItemModel | None) -> None:
    """遍历 URL 模型，把系统目录名替换为中文显示名。"""
    if model is None:
        return
    for row in range(model.rowCount()):
        index = model.index(row, 0)
        url = model.data(index, Qt.ItemDataRole.UserRole)
        if not isinstance(url, QUrl):
            continue
        name = Path(url.toLocalFile()).name
        cn = _SIDEBAR_CN.get(name)
        if cn:
            model.setData(index, cn, Qt.ItemDataRole.DisplayRole)


def _localize_sidebar(dialog: QFileDialog) -> None:
    """把侧栏与查找范围下拉里的系统目录名本地化为中文显示。"""
    sidebar = dialog.findChild(QListView, "sidebar")
    if sidebar is not None:
        _localize_url_model(sidebar.model())
    look_in = dialog.findChild(QComboBox, "lookInCombo")
    if look_in is not None:
        _localize_url_model(look_in.model())


def _localize_toolbar(dialog: QFileDialog) -> None:
    """把工具栏按钮的英文 tooltip 改为中文，并强制只显示图标。

    QFileDialog 在 DontUseNativeDialog 下，工具栏按钮的 ToolButtonStyle
    会跟随系统设置：若系统为「图标+文字」或「仅文字」，后退/前进/新建
    文件夹等按钮就会显示英文文本（Back / Forward / New Folder 等）。
    把 toolbar 强制设为 IconOnly，只保留图标与中文 tooltip。
    """
    for toolbar in dialog.findChildren(QToolBar):
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    for obj_name, tip in _TOOLBAR_TIPS.items():
        button = dialog.findChild(QToolButton, obj_name)
        if button is not None:
            button.setToolTip(tip)
            # 同步设置文字，保证工具栏切换展示模式时仍显示中文。
            button.setText(tip)


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


def style_file_dialog(dialog: QFileDialog, *, tip: str, accept_text: str) -> None:
    """装饰已设定侧栏位置的 Qt 文件选择器。"""
    dialog.setStyleSheet(FILE_DIALOG_STYLE)
    dialog.setWindowIcon(create_app_icon())
    _localize_sidebar(dialog)
    _localize_toolbar(dialog)
    _enable_scrollbars(dialog)
    _relabel_dialog(dialog, accept_text)
    dialog.setWindowTitle(f"NestPack · {tip}")
