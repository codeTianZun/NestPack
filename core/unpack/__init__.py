"""解包入口：按内容识别并逐层释放 RAR / 7z / ZIP 归档。"""

from .workflow import unpack_archive

__all__ = ["unpack_archive"]
