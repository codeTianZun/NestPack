"""Fluent 风格的消息弹窗助手，统一全应用的弹窗观感。

提供信息提示、错误提示、是否确认三类常用弹窗，以及打包完成后的
摘要弹窗（含复制密码清单与打开输出目录两个动作）。所有弹窗基于
qfluentwidgets 的 MessageBoxBase，带遮罩与淡入淡出动画；正文统一
放在限高的滚动区里，内容再长也只是滚动而不是超出屏幕。
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPlainTextEdit, QWidget
from qfluentwidgets import (
    BodyLabel,
    MessageBoxBase,
    PrimaryPushButton,
    PushButton,
    SmoothScrollArea,
)

from core.compression import CompressionResult
from core.legal import license_text
from core.moji import KAOMOJI
from core.result_summary import build_password_clipboard, build_success_report


def show_licenses(parent: QWidget) -> None:
    """在可滚动、可复制的窗口中展示版权与全部随附许可。"""
    box = MessageBoxBase(parent)
    box.viewLayout.addWidget(QLabel("NestPack · 版权与许可证"))
    text = QPlainTextEdit()
    text.setReadOnly(True)
    text.setPlainText(license_text())
    text.setMinimumHeight(320)
    box.viewLayout.addWidget(text)
    box.widget.setMinimumWidth(640)
    box.cancelButton.hide()
    box.yesButton.setText("关闭")
    box.exec()


def _scrollable_text(container: QWidget, text: str) -> SmoothScrollArea:
    """把多行正文包进限高的透明滚动区，内容过长时纵向滚动查看。"""
    label = BodyLabel(text)
    label.setWordWrap(True)
    scroll = SmoothScrollArea(container)
    scroll.setWidget(label)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea{background: transparent; border: none;}")
    label.setStyleSheet("QLabel{background: transparent;}")
    parent = container.window()
    if parent is not None:
        scroll.setMaximumHeight(max(240, parent.height() - 320))
    else:
        scroll.setMaximumHeight(420)
    return scroll


class _InfoBox(MessageBoxBase):
    """单按钮信息弹窗：只显示内容与一个确定按钮。"""

    def __init__(self, parent: QWidget, title: str, content: str) -> None:
        super().__init__(parent)
        self._build(title, content)
        self.cancelButton.hide()
        self.buttonLayout.insertStretch(0, 1)
        self.yesButton.setText("确定")

    def _build(self, title: str, content: str) -> None:
        title_label = QLabel(title)
        title_label.setObjectName("dialogTitle")
        self.viewLayout.addWidget(title_label)
        self.viewLayout.addWidget(_scrollable_text(self.widget, content))
        self.widget.setMinimumWidth(360)


class _AskBox(MessageBoxBase):
    """双按钮确认弹窗：确定执行 yes 动作，取消则拒绝。"""

    def __init__(
        self,
        parent: QWidget,
        title: str,
        content: str,
        yes_text: str = "确定",
        cancel_text: str = "取消",
    ) -> None:
        super().__init__(parent)
        title_label = QLabel(title)
        title_label.setObjectName("dialogTitle")
        self.viewLayout.addWidget(title_label)
        self.viewLayout.addWidget(_scrollable_text(self.widget, content))
        self.yesButton.setText(yes_text)
        self.cancelButton.setText(cancel_text)
        self.widget.setMinimumWidth(360)


class SuccessBox(MessageBoxBase):
    """打包完成摘要弹窗：展示各层文件名与密码清单，提供复制与打开动作。"""

    #: 用户点击「复制密码清单」。
    copy_requested = Signal()
    #: 用户点击「打开输出目录」。
    open_requested = Signal()

    def __init__(
        self,
        parent: QWidget,
        headline: str,
        detail_lines: list[str],
        final_archive_text: str,
        warning: str,
        kaomoji: str,
    ) -> None:
        super().__init__(parent)
        sections = [headline, "各层文件名与密码：", *detail_lines]
        sections.append(f"最外层文件：\n{final_archive_text}")
        if warning:
            sections.append(warning)
        sections.append(kaomoji)
        self.viewLayout.addWidget(_scrollable_text(self.widget, "\n".join(sections)))

        self.copy_button = PrimaryPushButton("复制密码清单")
        self.open_button = PushButton("打开输出目录")
        self._copy_feedback_timer = QTimer(self)
        self._copy_feedback_timer.setSingleShot(True)
        self._copy_feedback_timer.setInterval(2000)
        self._copy_feedback_timer.timeout.connect(self._reset_copy_button)
        self.copy_button.clicked.connect(self._request_copy)
        self.open_button.clicked.connect(self.open_requested.emit)
        self.buttonLayout.insertWidget(0, self.open_button, 1)
        self.buttonLayout.insertWidget(0, self.copy_button, 1)
        # 摘要弹窗只有「关闭」一个确认动作，隐藏默认 Cancel 按钮。
        self.cancelButton.hide()
        self.yesButton.setText("关闭")
        self.widget.setMinimumWidth(480)

    def _request_copy(self) -> None:
        """请求复制，并在当前弹窗内短暂显示成功反馈。"""
        self.copy_requested.emit()
        self.copy_button.setText("✓ 已复制")
        self._copy_feedback_timer.start()

    def _reset_copy_button(self) -> None:
        """恢复复制按钮的默认文字。"""
        self.copy_button.setText("复制密码清单")


def show_info(parent: QWidget, title: str, content: str) -> None:
    """弹出信息提示。"""
    _InfoBox(parent, title, content).exec()


def show_error(parent: QWidget, title: str, content: str) -> None:
    """弹出错误提示。"""
    _InfoBox(parent, title, content).exec()


def ask_yes_no(
    parent: QWidget,
    title: str,
    content: str,
    yes_text: str = "确定",
    cancel_text: str = "取消",
) -> bool:
    """弹出确认对话框，返回用户是否确认。"""
    return _AskBox(parent, title, content, yes_text, cancel_text).exec() == 1


__all__ = ["SuccessBox", "ask_yes_no", "show_error", "show_info"]


def show_compression_result(
    parent: QWidget, result: CompressionResult, on_copied: Callable[[], None]
) -> None:
    """展示本次执行结果，并从结果生成密码清单与输出目录动作。"""
    report = build_success_report(result)
    box = SuccessBox(
        parent, report.headline, report.detail_lines, report.final_archive_text,
        report.warning, KAOMOJI["success"],
    )

    def copy_passwords() -> None:
        QApplication.clipboard().setText(build_password_clipboard(result))
        on_copied()

    box.copy_requested.connect(copy_passwords)
    box.open_requested.connect(lambda: QDesktopServices.openUrl(
        QUrl.fromLocalFile(str(result.plan.output_directory))
    ))
    box.exec()
