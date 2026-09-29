"""文件、目录与压缩包选择器：混合多选、中文导航与最近目录。"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import (
    QDir,
    QStandardPaths,
    Qt,
    QUrl,
)
from PySide6.QtGui import QFocusEvent, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFileSystemModel,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QToolTip,
    QTreeView,
    QWidget,
)

from gui.appearance.file_dialog import style_file_dialog
from gui.config.storage import (
    load_file_dialog_size,
    load_recent_output_dirs,
    remember_file_dialog_size,
    remember_output_dir,
)
from gui.views.dialogs import show_info

# 各模式的项目专属提示文案，拼入 windowTitle 承载。
_TIP_SOURCES = "选择来源 · 文件与文件夹可混选"
_TIP_ARCHIVE = "选择最外层压缩包 · 分卷选第一卷，.bin 会自动识别"

# 确认按钮文案：用 setLabelText 改写 Accept 按钮的默认「Open」。
_ACCEPT_SOURCES = "选择来源"
_ACCEPT_DIRECTORY = "选择目录"
_ACCEPT_ARCHIVE = "选择压缩包"


class _MixedSourceDialog(QFileDialog):
    """文件+文件夹混合多选的确认对话框。

    QFileDialog 的 Directory 模式在仅选中文件时会禁用确认按钮，
    确认时还会把选中的目录当作「打开/进入」处理；子类覆盖这两处行为：
    - 确认按钮始终保持可用，抵消内部对纯文件选中的禁用；
    - accept 直接确认视图中选中的文件和文件夹。
    """

    def __init__(self, parent: QWidget, start_path: str, default_output: str) -> None:
        super().__init__(parent)
        self._accept_button: QPushButton | None = None
        self.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        self.setFileMode(QFileDialog.FileMode.Directory)
        self.setNameFilter("文件与文件夹 (*)")
        views = (self.findChild(QListView, "listView"), self.findChild(QTreeView))
        if any(view is not None for view in views):
            for view in views:
                if view is not None:
                    view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        else:
            self.setFileMode(QFileDialog.FileMode.ExistingFiles)
            show_info(
                parent, "混合多选不可用",
                "当前 Qt 版本不支持文件与文件夹混合多选，本次降级为纯文件多选。\n"
                "要添加文件夹，请把文件夹从资源管理器拖入来源列表。",
            )
        _prepare_dialog(
            self, tip=_TIP_SOURCES, accept_text=_ACCEPT_SOURCES,
            start_path=start_path, default_output=default_output,
        )
        self._force_accept_enabled()

    def accept(self) -> None:
        """确认当前选择：手动输入的路径交给 QFileDialog，视图选中项直接确认。"""
        edit = self.findChild(QLineEdit, "fileNameEdit")
        if edit is not None and edit.isModified() and edit.text().strip():
            super().accept()
            return
        if self.selectedFiles():
            # 绕过 Directory 模式的「打开目录」分支，直接确认选中项。
            QDialog.accept(self)
            return
        super().accept()

    def _force_accept_enabled(self) -> None:
        """锁定确认按钮可用，抵消 Directory 模式对纯文件选中的禁用。"""
        button_box = self.findChild(QDialogButtonBox, "buttonBox")
        if button_box is None:
            return
        button = button_box.button(
            QDialogButtonBox.StandardButton.Open
        )
        if button is None:
            return
        self._accept_button = button
        button.setEnabled(True)
        # 内部逻辑会在每次选中/输入变化后按 Directory 模式重新禁用按钮，
        # 这里在同样的信号上随后恢复可用，保证纯文件/目录/混合都能确认。
        for view in self.findChildren(QAbstractItemView):
            model = view.selectionModel()
            if model is None:
                continue
            model.selectionChanged.connect(self._keep_accept_enabled)
            model.currentChanged.connect(self._keep_accept_enabled)
        file_name_edit = self.findChild(QLineEdit, "fileNameEdit")
        if file_name_edit is not None:
            file_name_edit.textChanged.connect(self._keep_accept_enabled)

    def _keep_accept_enabled(self, *_args) -> None:
        if self._accept_button is not None:
            self._accept_button.setEnabled(True)


class _ConfigSaveDialog(QFileDialog):
    """在 Qt 校验与覆盖确认前确定配置文件的 JSON 后缀。"""

    def accept(self) -> None:
        selected = self.selectedFiles()
        if selected:
            path = Path(selected[0])
            if not path.is_dir() and path.suffix.lower() != ".json":
                edit = self.findChild(QLineEdit, "fileNameEdit")
                if edit is not None:
                    edit.clearFocus()
                self.selectFile(str(path.with_suffix(".json")))
        super().accept()


class _PathEdit(QLineEdit):
    """显示当前目录，点击后输入路径并导航或定位文件。"""

    def __init__(self, dialog: QFileDialog) -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self.setObjectName("pathEdit")
        self.setAccessibleName("当前路径")
        self.setToolTip("点击编辑路径，按回车跳转")
        self.setReadOnly(True)

        model = QFileSystemModel(self)
        model.setRootPath("")
        completer = QCompleter(model, self)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.activated[str].connect(self._complete_path)
        self.setCompleter(completer)

        file_model = dialog.findChild(QFileSystemModel, "qt_filesystem_model")
        if file_model is not None:
            file_model.rootPathChanged.connect(self._sync_path)
        dialog.directoryEntered.connect(self._sync_path)
        self._sync_path()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        was_read_only = self.isReadOnly()
        if was_read_only:
            self.setReadOnly(False)
        super().mousePressEvent(event)
        if was_read_only:
            self.selectAll()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and not self.isReadOnly():
            self._finish_edit()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.isReadOnly():
                self.setReadOnly(False)
                self.selectAll()
            elif self.completer() is not None and self.completer().popup().isVisible():
                completer = self.completer()
                index = completer.popup().currentIndex()
                if index.isValid():
                    self.setText(completer.pathFromIndex(index))
                completer.popup().hide()
                self._navigate()
            else:
                self._navigate()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        if not self.isReadOnly() and event.reason() != Qt.FocusReason.PopupFocusReason:
            self.setReadOnly(True)
            self._sync_path()
        super().focusOutEvent(event)

    def _sync_path(self, *_args: object) -> None:
        if self.isReadOnly():
            self.setText(QDir.toNativeSeparators(self._dialog.directory().absolutePath()))

    def _finish_edit(self) -> None:
        self.setReadOnly(True)
        self._sync_path()
        self.clearFocus()

    def _complete_path(self, path: str) -> None:
        self.setText(path)
        self._navigate()

    def _navigate(self) -> None:
        raw = self.text().strip().strip('"')
        if not raw:
            self._finish_edit()
            return
        expanded = os.path.expandvars(os.path.expanduser(raw))
        path = Path(expanded)
        if not path.is_absolute():
            path = Path(self._dialog.directory().absolutePath()) / path
        path = Path(os.path.normpath(path))

        if path.is_dir():
            self.setReadOnly(True)
            self._dialog.setDirectory(str(path))
        elif path.is_file() and not self._dialog.testOption(QFileDialog.Option.ShowDirsOnly):
            self.setReadOnly(True)
            self._dialog.selectFile(str(path))
        elif (self._dialog.acceptMode() == QFileDialog.AcceptMode.AcceptSave
              and path.parent.is_dir() and path.name):
            self.setReadOnly(True)
            self._dialog.selectFile(str(path))
        else:
            QToolTip.showText(
                self.mapToGlobal(self.rect().bottomLeft()), "路径不存在或不可选择", self,
            )
            return
        self._sync_path()
        self.clearFocus()


def _install_path_edit(dialog: QFileDialog) -> None:
    """用地址栏替换可见的查找范围下拉框，保留 Qt 的内部导航控件。"""
    look_in = dialog.findChild(QComboBox, "lookInCombo")
    grid = dialog.layout()
    if look_in is None or not isinstance(grid, QGridLayout):
        return
    top_item = grid.itemAtPosition(0, 1)
    top_layout = top_item.layout() if top_item is not None else None
    if not isinstance(top_layout, QHBoxLayout):
        return
    edit = _PathEdit(dialog)
    top_layout.insertWidget(0, edit, 1)
    look_in.hide()
    label = dialog.findChild(QLabel, "lookInLabel")
    if label is not None:
        label.setBuddy(edit)


def _system_shortcut_urls() -> list[QUrl]:
    """收集桌面/下载/文档/主目录等系统快捷位置的 URL。"""
    locations = [
        QStandardPaths.StandardLocation.DesktopLocation,
        QStandardPaths.StandardLocation.DownloadLocation,
        QStandardPaths.StandardLocation.DocumentsLocation,
        QStandardPaths.StandardLocation.HomeLocation,
    ]
    urls: list[QUrl] = []
    for loc in locations:
        path = QStandardPaths.writableLocation(loc)
        if path and Path(path).is_dir():
            url = QUrl.fromLocalFile(path)
            if url not in urls:
                urls.append(url)
    return urls


def _drive_urls() -> list[QUrl]:
    """收集系统所有盘根的 URL（C:/ D:/ ...），供查找范围下拉常驻切换。"""
    urls: list[QUrl] = []
    for info in QDir.drives():
        url = QUrl.fromLocalFile(info.absoluteFilePath())
        if url not in urls:
            urls.append(url)
    return urls


def _apply_sidebar(dialog: QFileDialog, default_output: str) -> None:
    """按常用位置、磁盘、当前输出和最近输出的顺序设置侧栏。"""
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    urls = _system_shortcut_urls()
    for url in _drive_urls():
        if url not in urls:
            urls.append(url)
    if default_output and Path(default_output).is_dir():
        url = QUrl.fromLocalFile(default_output)
        if url not in urls:
            urls.append(url)
    for path in load_recent_output_dirs():
        url = QUrl.fromLocalFile(path)
        if url not in urls:
            urls.append(url)
    dialog.setSidebarUrls(urls)


def _prepare_dialog(
    dialog: QFileDialog, *, tip: str, accept_text: str, start_path: str,
    default_output: str = "",
) -> None:
    """统一设置目录与外观，恢复并记录用户调整的窗口尺寸。"""
    _ensure_directory(dialog, start_path)
    _apply_sidebar(dialog, default_output)
    style_file_dialog(
        dialog, tip=tip, accept_text=accept_text,
        size=load_file_dialog_size() or (720, 460),
    )
    _install_path_edit(dialog)
    initial_size = dialog.size()

    def remember_size(_result: int) -> None:
        size = dialog.normalGeometry().size()
        if size != initial_size:
            remember_file_dialog_size(size.width(), size.height())

    dialog.finished.connect(remember_size)


def _ensure_directory(dialog: QFileDialog, start_path: str) -> None:
    """起始目录有效则设入对话框；无效则交给 QFileDialog 默认目录。"""
    if start_path and Path(start_path).is_dir():
        dialog.setDirectory(start_path)


def pick_sources(
    parent: QWidget,
    start_path: str,
    default_output: str = "",
) -> list[str]:
    """弹出文件+文件夹混合多选对话框，返回选中路径列表。

    Qt 内部视图不可用时提示用户并使用文件多选；文件夹可拖入来源列表。
    """
    dialog = _MixedSourceDialog(parent, start_path, default_output)
    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        return dialog.selectedFiles()
    return []


def pick_directory(
    parent: QWidget,
    *,
    title: str,
    start_path: str,
    default_output: str = "",
) -> str | None:
    """弹出单目录选择对话框，返回选中目录或取消为 None。

    选中后写入「最近输出目录」侧栏持久化记录。
    """
    dialog = QFileDialog(parent)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    dialog.setNameFilter("文件夹 (*)")
    _prepare_dialog(
        dialog,
        tip=title,
        accept_text=_ACCEPT_DIRECTORY,
        start_path=start_path,
        default_output=default_output,
    )
    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        result = dialog.selectedFiles()
        if result:
            selected = result[0]
            remember_output_dir(Path(selected))
            return selected
    return None


def pick_file(
    parent: QWidget,
    *,
    title: str,
    start_path: str,
    file_filter: str,
    accept_text: str = "选择文件",
) -> str | None:
    """按指定类型选择单个现有文件，共用导航与外观。"""
    dialog = QFileDialog(parent)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    dialog.setNameFilter(file_filter)
    _prepare_dialog(
        dialog,
        tip=title,
        accept_text=accept_text,
        start_path=start_path,
        default_output="",
    )
    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        result = dialog.selectedFiles()
        if result:
            return result[0]
    return None


def pick_archive(parent: QWidget, start_path: str) -> str | None:
    """选择最外层压缩包，返回选中文件或 None。"""
    return pick_file(
        parent, title=_TIP_ARCHIVE, start_path=start_path,
        file_filter="所有文件 (*.*)", accept_text=_ACCEPT_ARCHIVE,
    )


def pick_video(parent: QWidget, start_path: str) -> str | None:
    """选择 MP4 载体或融合视频，沿用统一文件选择器外观。"""
    return pick_file(
        parent, title="选择 MP4 视频", start_path=start_path,
        file_filter="MP4 视频 (*.mp4);;所有文件 (*.*)", accept_text="选择视频",
    )


def pick_sfx_resource(parent: QWidget, start_path: str, kind: str) -> str | None:
    """选择自解压模板或品牌图片。"""
    title, filters = {
        "template_path": ("自解压模板", "模板或品牌样包 (*.sfx *.SFX *.exe);;所有文件 (*)"),
        "icon_path": ("ICO 图标", "图标 (*.ico);;所有文件 (*)"),
        "logo_path": ("界面 Logo", "图片 (*.png *.bmp);;所有文件 (*)"),
    }[kind]
    return pick_file(
        parent, title=f"选择{title}", start_path=start_path, file_filter=filters,
    )


def pick_config_save(parent: QWidget, current_path: Path) -> str | None:
    """选择配置另存位置，预填当前文件名并由 Qt 确认覆盖。"""
    dialog = _ConfigSaveDialog(parent)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile)
    dialog.setNameFilter("JSON 配置 (*.json)")
    dialog.setDefaultSuffix("json")
    _prepare_dialog(
        dialog, tip="另存配置", accept_text="保存配置", start_path=str(current_path.parent),
    )
    dialog.selectFile(current_path.name)
    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        result = dialog.selectedFiles()
        if result:
            return result[0]
    return None


__all__ = [
    "pick_archive", "pick_config_save", "pick_directory", "pick_file",
    "pick_sfx_resource", "pick_sources", "pick_video",
]
