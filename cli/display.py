"""CLI 的启动横幅、任务摘要、进度与 JSON 输出。

print_json 统一 --json 与 --dry-run 的 stdout 输出格式；classify_error
将异常映射为错误 JSON 使用的 error_kind。
"""

from __future__ import annotations

import json
import sys

from core.cancellation import CancelledError
from core.compression import CompressionPlan
from core.legal import LICENSE_SUMMARY
from core.models import COMPRESS_MODE_SEPARATE, ConfigError
from core.moji import KAOMOJI


def print_json(payload: dict) -> None:
    """统一 --json 与 --dry-run 的 stdout 输出（indent=2、ensure_ascii=False）。"""
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def classify_error(error: BaseException) -> str:
    """把异常映射为 --json 错误输出的稳定 error_kind 字符串。

    智能体据此判断错误类别而无需解析中文 error 文本：cancelled=用户主动
    取消，not_found=文件或路径缺失，config_error=配置/参数/环境问题，
    io_error=操作系统 I/O 错误，runtime_error=运行错误。
    """
    if isinstance(error, CancelledError):
        return "cancelled"
    if isinstance(error, FileNotFoundError):
        return "not_found"
    if isinstance(error, ConfigError):
        return "config_error"
    if isinstance(error, OSError):
        return "io_error"
    if isinstance(error, RuntimeError):
        return "runtime_error"
    return "unknown"


def print_config_summary(plan: CompressionPlan) -> None:
    """打印不包含密码的任务摘要，便于用户确认加载的是哪份配置。"""
    config = plan.config
    sources = plan.sources
    if plan.config_path is not None:
        print(f"配置文件：{plan.config_path}")
    else:
        print("配置来源：本次任务设置")
    if plan.winrar is not None:
        print(f"RAR 工具：{plan.winrar}")
    if plan.sevenzip is not None:
        print(f"7-Zip：{plan.sevenzip}")
    if len(sources) == 1:
        print(f"原始输入：{sources[0]}")
    else:
        print("原始输入（多个）：")
        for source in sources:
            print(f"  {source}")
    mode_text = (
        "分别打包（每个来源一套压缩包）"
        if config.compress_mode == COMPRESS_MODE_SEPARATE
        else "一起打包（全部来源压成一个压缩包）"
    )
    print(f"打包方式：{mode_text}")
    print(f"输出目录：{plan.output_directory}")
    counts = sorted({len(task.layers) for task in plan.tasks})
    print("嵌套层数：" + " / ".join(str(count) for count in counts))
    print(f"自动覆盖：{'是' if config.overwrite_existing else '否'}")
    if sys.platform == "win32":
        print(f"显示 WinRAR 界面：{'是' if config.show_winrar_gui else '否'}")
    print(
        "删除中间层："
        f"{'是（自检通过后删除上一层）' if config.delete_inner_after_verify else '否'}"
    )
    for task in plan.tasks:
        if len(plan.tasks) > 1:
            print(f"来源：{task.sources[0].name}")
        for layer_number, planned in enumerate(task.layers, start=1):
            if planned.video is not None:
                print(f"  载体视频：{planned.video}")
            layer = planned.config
            if planned.sfx is not None:
                print(f"  自解压目标：{layer.sfx.target}，模板：{planned.sfx.template}")
            recovery = (
                f"{layer.recovery_percent}%" if layer.recovery_percent is not None else "关闭"
            )
            password_state = "已设置" if layer.password else "未设置"
            print(
                f"  第 {layer_number} 层：{planned.output_paths()[0].name}（{layer.format}），"
                f"密码{password_state}，恢复记录{recovery}"
            )


def print_banner() -> None:
    """启动时打印产品信息。"""
    print()
    print("NestPack 多层嵌套压缩工具")
    print(LICENSE_SUMMARY)
    print("完整许可与源码说明：--license")
    print()


def print_compression_progress(number: int, total: int, _message: str) -> None:
    """按已完成层数显示命令行压缩进度。"""
    if number < total:
        print(f"\n--- 第 {number + 1}/{total} 步：开始打包 ---")
    else:
        print(f"第 {number}/{total} 步打包完成 {KAOMOJI['success']}")
