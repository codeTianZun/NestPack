"""MP4 视频融合、原归档识别与提取入口。"""

from .fusion import (
    VideoArchive,
    extract_video_archive,
    fuse_archive,
    inspect_video_archive,
    validate_video,
    write_fused_video,
)

__all__ = [
    "VideoArchive", "extract_video_archive", "fuse_archive", "inspect_video_archive",
    "validate_video", "write_fused_video",
]
