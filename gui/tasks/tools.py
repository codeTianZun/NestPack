"""压缩工具检测与后台安装。"""

from pathlib import Path

from gui.tasks.threading import BackgroundTask, TaskWorker
from platforms import get_archive_platform
from platforms.tool_installer import install_requested_tools


class ToolInstallWorker(TaskWorker):
    """调用平台安装入口并转发日志。"""

    def __init__(self, tool: str) -> None:
        super().__init__("依赖安装失败")
        self._tool = tool

    def execute(self) -> None:
        install_requested_tools(self._tool, output_cb=self.log.emit)


class ToolInstallTask(BackgroundTask):
    """持有一次依赖安装的运行状态和线程。"""

    @staticmethod
    def detect() -> tuple[Path | None, Path | None]:
        """按平台规则检测 WinRAR 与 7-Zip。"""
        platform = get_archive_platform()
        return platform.find_tool(), platform.find_tool("7z")

    def start(self, tool: str) -> None:
        """安装指定工具，结束后通知界面重新检测。"""
        self._start(ToolInstallWorker(tool))
