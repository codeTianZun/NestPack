"""Windows GUI 应用：连接编辑会话、主窗口与后台任务。"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QFileDialog

from core.compression import CompressionResult, build_compression_plan
from core.logging_utils import setup_logging
from core.models import ConfigError
from gui.appearance.logo import LogoState
from gui.appearance.theme import APP_NAME, create_app_icon, init_fluent_theme
from gui.config.binding import ConfigBinding
from gui.config.session import ConfigSession
from gui.tasks.compression import CompressionTask
from gui.tasks.tools import ToolInstallTask
from gui.views.dialogs import ask_yes_no, show_compression_result, show_error, show_info
from gui.views.main_window import MainWindow
from gui.views.tool_dialogs import (
    confirm_missing_tools,
    confirm_tool_install,
    show_installed_tools,
    show_rar_install_guide,
)
from gui.views.unpack_dialog import UnpackDialog


class TabNavigationBlocker(QObject):
    """禁用 Tab/Shift+Tab 的焦点跳转，避免误触改变当前编辑位置。"""

    def eventFilter(self, watched, event) -> bool:
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            if event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                return True
        return super().eventFilter(watched, event)


class GuiApplication(QObject):
    """组装 GUI 模块，协调用户动作与不同任务之间的互斥。"""

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self.window = MainWindow()
        self.config = ConfigSession(self, ConfigBinding(
            self.window.source, self.window.layers, self.window.settings,
        ))
        self.compression = CompressionTask(self)
        self.tools = ToolInstallTask(self)
        self._close_when_finished = False
        self._connect_actions()
        self.window.set_config_path(self.config.path)
        self.config.load_initial()
        self._detect_tools()
        if getattr(sys, "frozen", False):
            QTimer.singleShot(0, self._offer_missing_tools_install)

    def _connect_actions(self) -> None:
        window = self.window
        window.load_requested.connect(self.load_config_dialog)
        window.save_as_requested.connect(self.save_config_as)
        window.close_requested.connect(self.close_window)
        window.side.save_requested.connect(self.save_current_config)
        window.side.run_requested.connect(self.start_compression)
        window.side.cancel_requested.connect(self.cancel_compression)
        window.side.unpack_requested.connect(self.open_unpack_dialog)
        window.settings.runtime.install_requested.connect(self.install_local_tools)
        window.settings.runtime.rar_guide_requested.connect(
            lambda: show_rar_install_guide(self.window)
        )
        self.config.path_changed.connect(window.set_config_path)
        self.config.status.connect(window.set_status)
        self.config.applied.connect(window.update_summary)
        self.compression.log.connect(window.side.append_log)
        self.compression.progress.connect(self._update_progress)
        self.compression.active_changed.connect(self.config.set_execution_active)
        self.compression.active_changed.connect(window.set_compressing)
        self.compression.completed.connect(self._compression_succeeded)
        self.compression.cancelled.connect(self._compression_cancelled)
        self.compression.failed.connect(self._compression_failed)
        self.compression.finished.connect(self._compression_finished)
        self.tools.log.connect(window.side.append_log)
        self.tools.active_changed.connect(window.set_installing)
        self.tools.completed.connect(self._tool_install_succeeded)
        self.tools.failed.connect(self._tool_install_failed)

    def load_config_dialog(self) -> None:
        selected, _filter = QFileDialog.getOpenFileName(
            self.window, "载入配置", str(self.config.path.parent),
            "JSON 配置 (*.json);;所有文件 (*.*)",
        )
        if selected:
            try:
                self.config.load(Path(selected).resolve())
            except (ConfigError, OSError) as error:
                show_error(self.window, "无法载入配置", str(error))

    def save_current_config(self) -> None:
        try:
            self.config.save()
        except (ValueError, OSError) as error:
            show_error(self.window, "无法保存配置", str(error))

    def save_config_as(self) -> None:
        selected, _filter = QFileDialog.getSaveFileName(
            self.window, "另存配置", str(self.config.path), "JSON 配置 (*.json)",
        )
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        try:
            self.config.save(path.resolve())
        except (ValueError, OSError) as error:
            show_error(self.window, "无法保存配置", str(error))

    def start_compression(self) -> None:
        """确定本次配置和计划后交给压缩任务执行。"""
        if self.tools.active:
            show_info(self.window, "正在安装依赖", "请等待依赖安装完成后再开始压缩。")
            return
        if self.compression.active:
            return
        try:
            config = self.config.collect()
        except (ValueError, ConfigError, OSError) as error:
            show_error(self.window, "无法开始", str(error))
            return
        missing = [
            str(index) for index, layer in enumerate(config.layers, start=1)
            if layer.password_set and not layer.password
        ]
        if missing and not ask_yes_no(
            self.window, "缺少密码",
            "以下层在配置中标记为需要密码，但当前未填写：第 "
            + "、".join(missing)
            + " 层。\n继续将生成【不加密】的压缩包，是否继续？",
            yes_text="继续",
        ):
            return
        try:
            config = self.config.prepare_execution(config)
            plan = build_compression_plan(config, self.config.path)
        except (ValueError, ConfigError, OSError) as error:
            show_error(self.window, "无法开始", str(error))
            return
        for warning in plan.warnings:
            show_info(self.window, "启动前提示", warning)
        self.window.side.set_progress(0, plan.total_layers)
        self.window.side.clear_log()
        self.window.set_status("正在准备打包任务…", LogoState.WORKING)
        self.compression.start(plan)

    def cancel_compression(self) -> None:
        if self.compression.active:
            self.window.side.show_cancelling()
            self.window.set_status("正在取消…", LogoState.WORKING)
            self.compression.cancel()

    @Slot(int, int, str)
    def _update_progress(self, value: int, total: int, message: str) -> None:
        self.window.side.set_progress(value, total)
        self.window.set_status(message, LogoState.WORKING)

    @Slot(object)
    def _compression_succeeded(self, result: CompressionResult) -> None:
        self.window.side.set_progress(result.plan.total_layers, result.plan.total_layers)
        self.window.set_status("全部打包完成！", LogoState.SUCCESS)
        show_compression_result(
            self.window, result,
            lambda: self.window.set_status("密码清单已复制到剪贴板"),
        )

    @Slot(str)
    def _compression_failed(self, message: str) -> None:
        self.window.set_status("打包失败了…请检查设置后重试", LogoState.FAIL)
        show_error(self.window, "压缩失败", message)

    @Slot()
    def _compression_cancelled(self) -> None:
        self.window.set_status("已取消", LogoState.IDLE)

    @Slot()
    def _compression_finished(self) -> None:
        if self._close_when_finished:
            self._close_when_finished = False
            self.window.close()

    def _detect_tools(self) -> tuple[Path | None, Path | None]:
        winrar, sevenzip = self.tools.detect()
        self.window.settings.runtime.show_detection(winrar, sevenzip)
        return winrar, sevenzip

    def _offer_missing_tools_install(self) -> None:
        tool = confirm_missing_tools(self.window, *self._detect_tools())
        if tool is not None:
            self._start_tool_install(tool)

    def install_local_tools(self) -> None:
        if confirm_tool_install(self.window):
            self._start_tool_install("7z")

    def _start_tool_install(self, tool: str) -> None:
        if self.compression.active:
            show_info(self.window, "正在压缩", "请等待当前压缩任务完成后再安装依赖。")
            return
        if self.tools.active:
            return
        self.window.side.clear_log()
        self.window.set_status("正在下载安装压缩依赖…", LogoState.WORKING)
        self.tools.start(tool)

    @Slot(object)
    def _tool_install_succeeded(self, _result: object) -> None:
        detected = self._detect_tools()
        self.window.set_status("压缩依赖安装完成", LogoState.SUCCESS)
        show_installed_tools(self.window, *detected)

    @Slot(str)
    def _tool_install_failed(self, message: str) -> None:
        self.window.set_status("依赖安装失败，请查看日志", LogoState.FAIL)
        show_error(self.window, "依赖安装失败", message)

    def open_unpack_dialog(self) -> None:
        if self.tools.active:
            show_info(self.window, "正在安装依赖", "请等待依赖安装完成后再解包。")
            return
        if self.compression.active:
            show_info(self.window, "正在压缩", "请等待当前压缩任务完成后再解包。")
            return
        winrar, sevenzip = self.window.settings.runtime.tool_paths()
        dialog = UnpackDialog(
            self.window, winrar_configured=winrar, sevenzip_configured=sevenzip,
            config_dir=self.config.path.parent,
            preset_candidates=self.window.layers.passwords(),
        )
        dialog.exec()

    def close_window(self, event: QCloseEvent) -> None:
        """安装结束后允许关闭，压缩中先确认取消并等待资源回收。"""
        if self.tools.active:
            show_info(self.window, "正在安装依赖", "请等待依赖安装完成后再关闭程序。")
            event.ignore()
            return
        if self.compression.active:
            confirmed = ask_yes_no(
                self.window, "任务正在运行",
                "压缩任务尚未完成。\n是否取消当前任务并退出？",
                yes_text="取消并退出", cancel_text="继续压缩",
            )
            if not confirmed:
                event.ignore()
                return
            if self.compression.active:
                self._close_when_finished = True
                self.compression.cancel()
                self.window.set_status("正在取消并退出…", LogoState.WORKING)
                event.ignore()
                return
        self.config.flush()
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
        app.installEventFilter(TabNavigationBlocker(app))
        app.setQuitOnLastWindowClosed(True)
        controller = GuiApplication(app)
        controller.window.show()
        return app.exec()
    except Exception:
        logger.exception("GUI 异常退出")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
