"""独立视频融合与归档提取的后台任务。"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject

from core.cancellation import Cancellation
from core.models import ConfigError
from core.video import extract_video_archive, fuse_archive, inspect_video_archive
from gui.tasks.threading import BackgroundTask, TaskWorker


class VideoWorker(TaskWorker):
    """在线程内完成视频文件读写，取消时释放临时产物。"""

    def __init__(
        self, source: Path, video: Path | None, output: Path,
        overwrite: bool, cancel_event: threading.Event,
    ) -> None:
        super().__init__("视频处理失败")
        self._source = source
        self._video = video
        self._output = output
        self._overwrite = overwrite
        self._cancellation = Cancellation(cancel_event)

    def execute(self) -> Path:
        if self._video is not None:
            return fuse_archive(
                self._video, self._source, self._output / f"{self._source.stem}.mp4",
                overwrite_existing=self._overwrite, cancellation=self._cancellation,
                output_cb=self.log.emit,
            )
        record = inspect_video_archive(self._source, self._cancellation)
        if record is None:
            raise ConfigError("所选文件不是 NestPack 生成的视频融合文件。")
        return extract_video_archive(
            self._source, self._output / f"{self._source.stem}.{record.format}",
            overwrite_existing=self._overwrite, cancellation=self._cancellation,
            output_cb=self.log.emit,
        )


class VideoTask(BackgroundTask):
    """持有独立视频任务的输入快照和取消事件。"""

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._cancel_event = threading.Event()

    def start(self, source: Path, video: Path | None, output: Path, overwrite: bool) -> None:
        self._cancel_event = threading.Event()
        self._start(VideoWorker(source, video, output, overwrite, self._cancel_event))

    def cancel(self) -> None:
        self._cancel_event.set()
