"""Windows GUI 应用：连接编辑会话、主窗口与后台任务。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QObject, QTimer, QUrl, Slot
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import QApplication

from core.compression import CompressionResult, build_compression_plan
from core.logging_utils import setup_logging
from core.models import ConfigError
from core.source_layers import source_layer_groups
from gui.appearance.logo import LogoState
from gui.appearance.theme import APP_NAME, create_app_icon, init_fluent_theme
from gui.config.binding import ConfigBinding
from gui.config.session import ConfigSession
from gui.tasks.compression import CompressionTask
from gui.tasks.tools import ToolInstallTask
from gui.tasks.unpack import UnpackTask
from gui.views.dialogs import ask_yes_no, show_compression_result, show_error, show_info
from gui.views.file_dialog import pick_config_save, pick_file
from gui.views.main_window import MainWindow
from gui.views.tool_dialogs import (
    confirm_missing_tools,
    confirm_tool_install,
    show_installed_tools,
    show_rar_install_guide,
)
from gui.views.video_dialog import VideoDialog


class GuiApplication(QObject):
    """组装 GUI 模块，协调用户动作与不同任务之间的互斥。"""

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self.window = MainWindow()
        self.config = ConfigSession(self, ConfigBinding(
            self.window.source, self.window.layers, self.window.output,
            self.window.options, self.window.settings, self.window.config_bar,
        ))
        self.compression = CompressionTask(self)
        self.unpack = UnpackTask(self)
        self.tools = ToolInstallTask(self)
        self._video_dialog: VideoDialog | None = None
        self._compression_result: CompressionResult | None = None
        self._unpack_result: tuple[list[Path], Path] | None = None
        self._video_results: dict[str, Path] = {}
        self._unpack_output = Path.cwd()
        self._close_when_finished = False
        self._connect_actions()
        self.window.set_config_path(self.config.path)
        self.config.load_initial()
        self._detect_tools()
        if getattr(sys, "frozen", False):
            QTimer.singleShot(0, self._offer_missing_tools_install)

    def _connect_actions(self) -> None:
        window = self.window
        window.config_bar.load_requested.connect(self.load_config_dialog)
        window.config_bar.save_requested.connect(self.save_current_config)
        window.config_bar.save_as_requested.connect(self.save_config_as)
        window.close_requested.connect(self.close_window)
        window.workspace_changed.connect(self._update_result_button)
        window.side.run_requested.connect(self.start_current_task)
        window.side.cancel_requested.connect(self.cancel_current_task)
        window.side.result_requested.connect(self.show_current_result)
        window.output.disguise_existing_requested.connect(lambda: self.open_video_dialog("fuse"))
        window.unpack.extract_requested.connect(lambda: self.open_video_dialog("extract"))
        window.settings.runtime.install_requested.connect(self.install_local_tools)
        window.settings.runtime.detect_requested.connect(self._detect_tools)
        window.settings.runtime.rar_guide_requested.connect(
            lambda: show_rar_install_guide(window.settings)
        )
        self.config.path_changed.connect(window.set_config_path)
        self.config.status.connect(window.config_bar.set_status)
        self.config.applied.connect(window.update_summary)
        for kind, task in (
            ("compress", self.compression), ("unpack", self.unpack), ("tools", self.tools),
        ):
            task.log.connect(window.side.append_log)
            task.active_changed.connect(
                lambda active, name=kind: self._set_task_active(name, active)
            )
            task.finished.connect(self._task_finished)
        self.compression.progress.connect(self._update_progress)
        self.compression.completed.connect(self._compression_succeeded)
        self.compression.cancelled.connect(lambda: self._task_cancelled("压缩"))
        self.compression.failed.connect(lambda message: self._task_failed("压缩", message))
        self.unpack.completed.connect(self._unpack_succeeded)
        self.unpack.cancelled.connect(lambda: self._task_cancelled("解包"))
        self.unpack.failed.connect(lambda message: self._task_failed("解包", message))
        self.tools.completed.connect(self._tool_install_succeeded)
        self.tools.failed.connect(lambda message: self._task_failed("依赖安装", message))

    def _busy(self) -> bool:
        return any(task.active for task in (self.compression, self.unpack, self.tools)) or (
            self._video_dialog is not None and self._video_dialog.task.active
        )

    def _can_start(self) -> bool:
        if self._busy():
            show_info(self.window, "任务正在运行", "请先结束当前任务，再开始新的操作。")
            return False
        return True

    def _set_task_active(self, kind: str, active: bool) -> None:
        self.config.set_execution_active(active)
        self.window.set_task_active(kind, active)
        self._update_result_button()

    def _update_result_button(self) -> None:
        available = (
            self._compression_result is not None if self.window.workspace() == "compress"
            else self._unpack_result is not None
        )
        available = available or self.window.workspace() in self._video_results
        self.window.side.result_button.setEnabled(available and not self._busy())

    def _clear_result(self, workspace: str) -> None:
        self._video_results.pop(workspace, None)
        if workspace == "compress":
            self._compression_result = None
        else:
            self._unpack_result = None
            self.window.unpack.result_label.clear()
        self._update_result_button()

    def load_config_dialog(self) -> None:
        selected = pick_file(
            self.window, title="载入配置", start_path=str(self.config.path.parent),
            file_filter="JSON 配置 (*.json);;所有文件 (*.*)", accept_text="载入配置",
        )
        if selected:
            try:
                self.config.flush()
                self.config.load(Path(selected).resolve())
                self._detect_tools()
            except (ConfigError, OSError) as error:
                show_error(self.window, "无法载入配置", str(error))

    def save_current_config(self) -> None:
        try:
            self.config.save()
        except (ValueError, OSError) as error:
            show_error(self.window, "无法保存配置", str(error))

    def save_config_as(self) -> None:
        selected = pick_config_save(self.window, self.config.path)
        if not selected:
            return
        path = Path(selected)
        try:
            self.config.save(path.resolve())
        except (ValueError, OSError) as error:
            show_error(self.window, "无法保存配置", str(error))

    def start_current_task(self) -> None:
        if not self._can_start():
            return
        if self.window.workspace() == "compress":
            self.start_compression()
        else:
            self.start_unpack()

    def start_compression(self) -> None:
        """确定本次配置和计划后交给压缩任务执行。"""
        try:
            config = self.config.collect()
        except (ValueError, OSError) as error:
            show_error(self.window, "无法开始", str(error))
            return
        missing = [
            f"{sources[0].name} 第 {index} 层"
            for sources, layers in source_layer_groups(config, self.config.path.parent)
            for index, layer in enumerate(layers, start=1)
            if layer.password_set and not layer.password
        ]
        if missing and not ask_yes_no(
            self.window, "缺少密码",
            "以下层在配置中标记为需要密码，但当前未填写："
            + "、".join(missing)
            + "。\n继续将生成【不加密】的压缩包，是否继续？",
            yes_text="继续",
        ):
            return
        try:
            config = self.config.prepare_execution(config)
            plan = build_compression_plan(config, self.config.path)
        except (ValueError, OSError) as error:
            show_error(self.window, "无法开始", str(error))
            return
        for warning in plan.warnings:
            show_info(self.window, "启动前提示", warning)
        self._clear_result("compress")
        self.window.side.set_summary("压缩 · " + str(len(plan.tasks)) + " 个任务")
        self.window.side.set_progress(0, plan.total_layers)
        self.window.side.clear_log()
        self.window.set_status("正在准备压缩…", LogoState.WORKING)
        self.compression.start(plan)

    def start_unpack(self) -> None:
        try:
            archive, output, candidates, limit = self.window.unpack.collect(
                self.window.layers.passwords()
            )
            winrar, sevenzip = self.window.settings.runtime.tool_paths()
            self._unpack_output = output
            self.window.side.clear_log()
            self.unpack.start(
                archive, output, candidates, limit,
                winrar_configured=winrar, sevenzip_configured=sevenzip,
                config_dir=self.config.path.parent,
            )
        except (ValueError, OSError) as error:
            show_error(self.window, "无法开始解包", str(error))
            return
        self._clear_result("unpack")
        self.window.side.set_summary("解包 · " + archive.name)
        self.window.side.set_progress(0, 1)
        self.window.side.set_busy(True)
        self.window.set_status("正在逐层解包…", LogoState.WORKING)

    def cancel_current_task(self) -> None:
        task = self.compression if self.compression.active else self.unpack
        if task.active:
            self.window.side.show_cancelling()
            self.window.set_status("正在取消…", LogoState.WORKING)
            task.cancel()

    @Slot(int, int, str)
    def _update_progress(self, value: int, total: int, message: str) -> None:
        self.window.side.set_progress(value, total)
        self.window.set_status(message, LogoState.WORKING)

    @Slot(object)
    def _compression_succeeded(self, result: CompressionResult) -> None:
        self._compression_result = result
        self.window.side.set_progress(result.plan.total_layers, result.plan.total_layers)
        self.window.set_status("压缩完成", LogoState.SUCCESS)
        if not self._close_when_finished:
            self._show_compression_result()

    @Slot(object)
    def _unpack_succeeded(self, entries: list[Path]) -> None:
        self._unpack_result = (entries, self._unpack_output)
        self.window.unpack.show_result(entries, self._unpack_output)
        self.window.side.set_progress(1, 1)
        self.window.set_status("解包完成", LogoState.SUCCESS)
        if not self._close_when_finished:
            self._show_unpack_result()

    def _task_failed(self, label: str, message: str) -> None:
        self.window.set_status(f"{label}失败，请查看日志", LogoState.FAIL)
        if not self._close_when_finished:
            show_error(self.window, f"{label}失败", message)

    def _task_cancelled(self, label: str) -> None:
        self.window.set_status(f"{label}已取消", LogoState.IDLE)

    def show_current_result(self) -> None:
        video_result = self._video_results.get(self.window.workspace())
        if video_result is not None:
            if ask_yes_no(
                self.window, "归档处理完成", str(video_result),
                yes_text="打开输出目录", cancel_text="关闭",
            ):
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(video_result.parent)))
        elif self.window.workspace() == "compress":
            self._show_compression_result()
        else:
            self._show_unpack_result()

    def _show_compression_result(self) -> None:
        if self._compression_result is not None:
            show_compression_result(
                self.window, self._compression_result,
                lambda: self.window.set_status("密码清单已复制到剪贴板"),
            )

    def _show_unpack_result(self) -> None:
        if self._unpack_result is None:
            return
        entries, output = self._unpack_result
        names = "\n".join(str(entry) for entry in entries) or "（空）"
        if ask_yes_no(
            self.window, "解包完成",
            f"已恢复 {len(entries)} 个条目：\n{names}\n输出目录：{output}",
            yes_text="打开输出目录", cancel_text="关闭",
        ):
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output)))

    @Slot()
    def _task_finished(self) -> None:
        if self._close_when_finished and not self._busy():
            self._close_when_finished = False
            self.window.close()

    def _detect_tools(self) -> tuple[Path | None, Path | None]:
        return self.window.settings.runtime.detect()

    def _offer_missing_tools_install(self) -> None:
        tool = confirm_missing_tools(self.window, *self._detect_tools())
        if tool is not None:
            self._start_tool_install(tool)

    def install_local_tools(self) -> None:
        if self._can_start() and confirm_tool_install(self.window.settings):
            self._start_tool_install("7z")

    def _start_tool_install(self, tool: str) -> None:
        if not self._can_start():
            return
        self.window.side.clear_log()
        self.window.side.set_summary("安装 7-Zip")
        self.window.side.set_progress(0, 1)
        self.window.side.set_busy(True)
        self.window.set_status("正在下载安装…", LogoState.WORKING)
        self.tools.start(tool)

    @Slot(object)
    def _tool_install_succeeded(self, _result: object) -> None:
        detected = self._detect_tools()
        self.window.side.set_progress(1, 1)
        self.window.set_status("依赖安装完成", LogoState.SUCCESS)
        show_installed_tools(self.window, *detected)

    def open_video_dialog(self, operation: Literal["fuse", "extract"]) -> None:
        if not self._can_start():
            return
        dialog = VideoDialog(
            self.window, self.config.path.parent, operation,
            source=self.window.unpack.archive_edit.text() if operation == "extract" else "",
            video=self.window.output.video_edit.text(),
            output=(
                self.window.output.output_directory() if operation == "fuse"
                else self.window.unpack.output_directory()
            ),
        )
        self._video_dialog = dialog
        workspace = self.window.workspace()
        label = "归档伪装" if operation == "fuse" else "原归档提取"
        dialog.task.log.connect(self.window.side.append_log)
        dialog.task.active_changed.connect(lambda active: self._video_active(label, active))
        dialog.task.completed.connect(
            lambda result: self._video_completed(workspace, label, result)
        )
        dialog.task.failed.connect(
            lambda _message: self.window.set_status(f"{label}失败", LogoState.FAIL)
        )
        dialog.task.cancelled.connect(lambda: self._task_cancelled(label))
        dialog.task.finished.connect(self._task_finished)
        dialog.exec()
        self._video_dialog = None
        dialog.deleteLater()

    def _video_completed(self, workspace: str, label: str, result: Path) -> None:
        self._video_results[workspace] = result
        self.window.side.set_progress(1, 1)
        self.window.set_status(f"{label}完成", LogoState.SUCCESS)
        self._update_result_button()

    def _video_active(self, label: str, active: bool) -> None:
        self._set_task_active("video", active)
        if active:
            self._clear_result(self.window.workspace())
            self.window.side.clear_log()
            self.window.side.set_summary(label)
            self.window.side.set_progress(0, 1)
            self.window.side.set_busy(True)
            self.window.set_status(f"正在{label}…", LogoState.WORKING)

    def close_window(self, event: QCloseEvent) -> None:
        """运行中先确认取消，等线程释放资源后再退出。"""
        if self.tools.active:
            show_info(self.window, "正在安装依赖", "请等待依赖安装完成后再关闭程序。")
            event.ignore()
            return
        if self._busy():
            if not self._close_when_finished and not ask_yes_no(
                self.window, "任务正在运行", "是否取消当前任务并退出？",
                yes_text="取消并退出", cancel_text="继续任务",
            ):
                event.ignore()
                return
            if self._busy():
                self._close_when_finished = True
                if self._video_dialog is not None:
                    self._video_dialog.reject()
                else:
                    self.cancel_current_task()
                self.window.set_status("正在取消并退出…", LogoState.WORKING)
                event.ignore()
                return
        self.config.flush()
        self.window.settings.close()
        self.window.side.log_dialog.close()
        event.accept()


def main() -> int:
    """创建 Windows 应用并进入事件循环。"""
    if sys.platform != "win32":
        raise RuntimeError("NestPack 图形界面仅支持 Windows。")
    logger = setup_logging("gui")
    try:
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setOrganizationName("Local Tools")
        init_fluent_theme()
        app.setWindowIcon(create_app_icon())
        app.setQuitOnLastWindowClosed(True)
        controller = GuiApplication(app)
        controller.window.show()
        return app.exec()
    except Exception:
        logger.exception("GUI 异常退出")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
