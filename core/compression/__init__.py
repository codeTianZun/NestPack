"""压缩入口：构建任务计划、执行计划并返回结构化结果。"""

from .models import CompressionPlan, CompressionResult
from .planning import build_compression_plan
from .scheduler import run_compression

__all__ = [
    "CompressionPlan",
    "CompressionResult",
    "build_compression_plan",
    "run_compression",
]
