"""文件日志：为 GUI（pythonw）等无控制台场景留下崩溃与错误痕迹。

日志写入用户数据目录并滚动保留，Windows 使用 %LOCALAPPDATA%，
Linux 使用 XDG_DATA_HOME 或 ~/.local/share。
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
MAX_LOG_BYTES = 1024 * 1024
BACKUP_COUNT = 3


def log_directory() -> Path:
    """返回日志目录（按平台约定），不存在时由调用方创建。"""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
        return Path(base) / "NestPack" / "logs"
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "nestpack" / "logs"


def setup_logging(name: str = "nestpack") -> logging.Logger:
    """配置并返回文件日志器；日志目录不可用时静默降级。"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        directory = log_directory()
        directory.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            directory / "nestpack.log",
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())
    return logger
