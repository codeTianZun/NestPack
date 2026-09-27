"""NestPack 项目 Logo 资源与任务状态图片。"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

ASSET_DIRECTORY = Path(__file__).resolve().parent / "assets"
APP_ICON_PATH = ASSET_DIRECTORY / "icon.png"


class LogoState(Enum):
    """Logo 图片对应的任务状态。"""

    IDLE = "idle"
    WORKING = "working"
    SUCCESS = "success"
    FAIL = "fail"


@lru_cache(maxsize=32)
def render_logo(
    state: LogoState, size: int = 256, *, device_pixel_ratio: float = 1.0
) -> QPixmap:
    """按显示尺寸与屏幕缩放比例加载并缓存透明状态图。"""
    pixel_size = round(size * device_pixel_ratio)
    pixmap = QPixmap(str(ASSET_DIRECTORY / f"{state.value}.png")).scaled(
        pixel_size,
        pixel_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    pixmap.setDevicePixelRatio(device_pixel_ratio)
    return pixmap
