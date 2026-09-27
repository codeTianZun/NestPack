"""文件、目录与压缩包选择器：混合多选、中文导航与最近目录。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QDir,
    QStandardPaths,
    QUrl,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLineEdit,
    QListView,
    QPushButton,
    QTreeView,
    QWidget,
)

from gui.appearance.file_dialog import style_file_dialog
from gui.config.storage import load_recent_output_dirs, remember_output_dir
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


def _system_shortcut_urls() -> list[QUrl]:
    """收集桌面/下载/文档/主目录等系统快捷位置的 URL。"""
    locations = [
        QStandardPaths.StandardLocation.DesktopLocation,
        QStandardPaths.StandardLocation.DocumentsLocation,
        QStandardPaths.StandardLocation.DownloadLocation,
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
    """重设侧栏 URL：默认输出目录 + 最近输出目录 + 系统快捷位置 + 所有盘根。"""
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    urls: list[QUrl] = []
    if default_output and Path(default_output).is_dir():
        url = QUrl.fromLocalFile(default_output)
        if url not in urls:
            urls.append(url)
    for path in load_recent_output_dirs():
        url = QUrl.fromLocalFile(path)
        if url not in urls:
            urls.append(url)
    for url in _system_shortcut_urls():
        if url not in urls:
            urls.append(url)
    for url in _drive_urls():
        if url not in urls:
            urls.append(url)
    dialog.setSidebarUrls(urls)


def _prepare_dialog(
    dialog: QFileDialog, *, tip: str, accept_text: str, start_path: str,
    default_output: str = "",
) -> None:
    """统一设置起始目录、侧栏与外观。"""
    _ensure_directory(dialog, start_path)
    _apply_sidebar(dialog, default_output)
    style_file_dialog(dialog, tip=tip, accept_text=accept_text)


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


def pick_archive(
    parent: QWidget,
    start_path: str,
) -> str | None:
    """弹出单文件选择对话框用于选最外层压缩包，返回选中文件或 None。"""
    dialog = QFileDialog(parent)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    dialog.setNameFilter("所有文件 (*.*)")
    _prepare_dialog(
        dialog,
        tip=_TIP_ARCHIVE,
        accept_text=_ACCEPT_ARCHIVE,
        start_path=start_path,
        default_output="",
    )
    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        result = dialog.selectedFiles()
        if result:
            return result[0]
    return None


__all__ = ["pick_archive", "pick_directory", "pick_sources"]
