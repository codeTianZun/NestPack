"""压缩工具后台安装。"""

from gui.tasks.threading import BackgroundTask, TaskWorker
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

    def start(self, tool: str) -> None:
        """安装指定工具，结束后通知界面重新检测。"""
        self._start(ToolInstallWorker(tool))
