"""命令行参数、逐层参数分组与用法错误。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, NoReturn

from core.legal import license_text
from core.models import APP_VERSION, DEFAULT_CONFIG_PATH


class UsageError(ValueError):
    """参数用法错误，由 CLI 入口按文本或 JSON 展示。"""


class ArgumentParser(argparse.ArgumentParser):
    """把参数错误交给统一出口，保留 argparse 的帮助与版本行为。"""

    def error(self, message: str) -> NoReturn:
        raise UsageError(message)


class ShowLicense(argparse.Action):
    """显示许可全文后退出，与帮助和版本查询保持一致。"""

    def __call__(
        self, parser: argparse.ArgumentParser, namespace: argparse.Namespace,
        values: Any, option_string: str | None = None,
    ) -> None:
        print(license_text())
        parser.exit()


class LayerOption(argparse.Action):
    """将层参数归入最近一次 --layer 指定的压缩层。"""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        layers = namespace.layer_specs
        if not layers:
            parser.error(f"{option_string} 前需要先指定 --layer rar、7z 或 zip")
        layers[-1][self.dest.removeprefix("layer_")] = values


class StartLayer(argparse.Action):
    """按命令行顺序添加从内到外的压缩层。"""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        if namespace.layer_specs is None:
            namespace.layer_specs = []
        namespace.layer_specs.append({"format": values})


def _positive_int(raw_value: str) -> int:
    try:
        value = int(raw_value)
    except ValueError:
        raise argparse.ArgumentTypeError("必须是不小于 1 的整数") from None
    if value < 1:
        raise argparse.ArgumentTypeError("必须是不小于 1 的整数")
    return value


BOOLEAN_OPTIONS = {
    "overwrite_existing": "允许覆盖已有归档，默认关闭",
    "confirm_before_start": "运行前确认，直接参数任务默认关闭",
    "show_winrar_gui": "显示 Windows WinRAR 界面，直接参数任务默认关闭",
    "add_padding": "每层加入随机填充文件",
    "randomize_layer_names": "运行时随机生成层名",
    "hide_source_name": "使用随机来源根名称",
    "disguise_outer_extension": "调整最外层扩展名",
    "randomize_timestamps": "随机化最外层修改时间",
    "verify_after_compress": "每层压缩后自检，默认开启",
    "cleanup_on_failure": "任务失败时清理本次产物",
    "persist_passwords": "保存配置时保留密码，默认开启",
    "delete_inner_after_verify": "自检通过后删除中间层，默认开启",
    "video_fusion": "将最外层单文件归档融合为 MP4 视频",
}


def create_parser() -> ArgumentParser:
    command = (
        Path(sys.executable).name if getattr(sys, "frozen", False)
        else "python3 -m cli" if sys.platform == "linux" else "python -m cli"
    )
    parser = ArgumentParser(
        prog=command,
        description="NestPack：数字菜单与参数调用共用的多层压缩 / 解包工具。",
        epilog=(
            "无参数启动数字菜单。\n"
            f"直接压缩：{command} --source data --output out --layer rar --yes\n"
            f"混合嵌套：{command} --source data --output out --layer rar "
            "--layer-password inner --layer 7z --layer-password outer --yes\n"
            "AI 调用：加 --non-interactive --json；预览加 --dry-run。\n"
            f"配置任务：{command} --config task.json --yes --non-interactive --json\n"
            f"解包：{command} --unpack outer.rar --password-file passwords.txt"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument("--menu", action="store_true", help="打开数字交互菜单")
    parser.add_argument(
        "--config", type=Path, metavar="文件", help=f"读取配置；默认：{DEFAULT_CONFIG_PATH}"
    )
    parser.add_argument("--init", action="store_true", help="交互创建配置并保存后退出")
    parser.add_argument(
        "--save-config", type=Path, metavar="文件", help="将本次压缩设置保存到指定配置"
    )
    parser.add_argument(
        "--install-tools",
        nargs="?",
        const="all",
        choices=("rar", "7z", "all"),
        metavar="工具",
        help="rar 显示官网安装指引，7z 自动安装，all 执行两项（默认）",
    )
    parser.add_argument("--unpack", type=Path, metavar="文件", help="逐层解包最外层归档")
    parser.add_argument("--fuse-archive", type=Path, metavar="压缩包", help="将已有归档与视频融合")
    parser.add_argument(
        "--extract-video-archive", type=Path, metavar="视频", help="从融合视频提取原始归档"
    )
    parser.add_argument("--video", dest="video_path", metavar="MP4", help="载体视频，并启用融合")
    parser.add_argument(
        "--source-video", dest="source_video_paths", action="append", nargs=2,
        metavar=("来源", "MP4"), help="分别打包时为指定来源覆盖默认视频，可重复",
    )
    parser.add_argument(
        "--output", type=Path, metavar="目录", help="本次输出目录，相对当前工作目录解析"
    )
    parser.add_argument(
        "--yes", action="store_true", help="跳过确认；覆盖产物仍需 --overwrite-existing"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="不读取交互输入，缺少必要信息立即报错",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="stdout 输出单个结果 JSON；日志和进度走 stderr；成功压缩清单含密码",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只读预览压缩计划，输出 JSON，不创建目录或保存配置",
    )
    parser.add_argument(
        "--version", action="version", version=f"NestPack {APP_VERSION}", help="显示版本"
    )
    parser.add_argument("--license", nargs=0, action=ShowLicense, help="显示版权与许可证全文")

    compression = parser.add_argument_group("压缩任务：来源可重复，层按从内到外顺序添加")
    compression.add_argument(
        "--source", action="append", metavar="路径", help="来源文件或目录，可重复"
    )
    compression.add_argument(
        "--compress-mode", choices=("combined", "separate"), help="合并 / 分别打包"
    )
    compression.add_argument(
        "--rar-path", dest="winrar_path", metavar="程序", help="RAR 工具路径或 auto"
    )
    compression.add_argument("--sevenzip-path", metavar="程序", help="7-Zip 工具路径或 auto")
    compression.add_argument(
        "--disguise-extension", metavar="扩展名", help="最外层扩展名，如 .bin，并启用扩展名调整"
    )
    for field, description in BOOLEAN_OPTIONS.items():
        compression.add_argument(
            "--" + field.replace("_", "-"),
            action=argparse.BooleanOptionalAction,
            default=None,
            help=description,
        )
    compression.add_argument(
        "--layer",
        choices=("rar", "7z", "zip"),
        action=StartLayer,
        help="添加一层；后续 --layer-* 参数属于这一层",
    )
    parser.set_defaults(layer_specs=None)
    for flag, field, description in (
        ("--layer-name", "archive_name", "本层文件名，省略时按来源生成"),
        ("--layer-password", "password", "本层密码，空字符串表示不加密"),
        ("--layer-password-file", "password_file", "从 UTF-8 文件读取本层密码（单行）"),
        ("--layer-level", "compression_level", "本层压缩级别：auto 或 0–5"),
        ("--layer-volume-size", "volume_size", "本层分卷大小，如 100m"),
        ("--layer-recovery", "recovery_percent", "本层恢复记录百分比 1–100，仅 RAR"),
        ("--layer-name-template", "name_template", "分别打包的层名模板，如 {stem}_1"),
    ):
        compression.add_argument(
            flag,
            dest="layer_" + field,
            action=LayerOption,
            default=None,
            metavar="值",
            help=description,
        )

    unpack = parser.add_argument_group("解包参数")
    unpack.add_argument(
        "--password", action="append", default=[], metavar="密码", help="解包候选密码，可重复"
    )
    unpack.add_argument(
        "--password-file", type=Path, metavar="文件", help="UTF-8 解包候选密码文件，每行一个"
    )
    unpack.add_argument(
        "--layers", type=_positive_int, metavar="层数", help="最多解包的层数，默认自动识别"
    )
    return parser


def compression_arguments_present(
    arguments: argparse.Namespace, *, include_tools: bool = True
) -> bool:
    return any(
        getattr(arguments, key) is not None
        for key in (
            "source",
            "layer_specs",
            "compress_mode",
            "disguise_extension",
            "save_config",
            "video_path",
            "source_video_paths",
            *BOOLEAN_OPTIONS,
        )
    ) or (include_tools and any((arguments.winrar_path, arguments.sevenzip_path)))


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    raw = list(sys.argv[1:] if argv is None else argv)
    parser = create_parser()
    arguments = parser.parse_args(raw)
    arguments.menu = arguments.menu or not raw
    compression = compression_arguments_present(arguments)
    unpack_options = (
        bool(arguments.password)
        or arguments.password_file is not None
        or arguments.layers is not None
    )
    if arguments.menu:
        if any(
            (
                arguments.init,
                arguments.install_tools,
                arguments.unpack,
                arguments.fuse_archive,
                arguments.extract_video_archive,
                arguments.output,
                arguments.json,
                arguments.dry_run,
                arguments.non_interactive,
                arguments.yes,
                compression,
                unpack_options,
            )
        ):
            parser.error("--menu 仅可搭配 --config 指定菜单中的配置文件")
    if sum((arguments.init, arguments.unpack is not None, arguments.install_tools is not None,
            arguments.fuse_archive is not None, arguments.extract_video_archive is not None)) > 1:
        parser.error("初始化、解包、工具安装、独立视频融合与归档提取只能选择一种模式")
    if arguments.fuse_archive is not None or arguments.extract_video_archive is not None:
        if any(getattr(arguments, key) is not None for key in (
            "source", "layer_specs", "compress_mode", "disguise_extension", "save_config",
            "source_video_paths", "winrar_path", "sevenzip_path",
            *(key for key in BOOLEAN_OPTIONS if key != "overwrite_existing"),
        )) or arguments.config is not None or arguments.dry_run or unpack_options:
            parser.error("独立视频融合与归档提取不接收压缩层、配置或解包参数")
        if arguments.fuse_archive is not None and not arguments.video_path:
            parser.error("--fuse-archive 需要通过 --video 指定载体 MP4")
        if arguments.extract_video_archive is not None and arguments.video_path is not None:
            parser.error("--extract-video-archive 已指定融合文件，无需 --video")
    if arguments.install_tools is not None and any(
        (
            arguments.output,
            arguments.dry_run,
            compression,
            unpack_options,
            arguments.config,
        )
    ):
        parser.error("--install-tools 是独立模式，不接收任务配置、输出或压缩/解包参数")
    if arguments.init and any((arguments.output, arguments.dry_run, compression, unpack_options)):
        parser.error("--init 使用交互向导；直接参数压缩请使用 --source 和 --layer")
    if arguments.unpack is not None and (
        arguments.dry_run or compression_arguments_present(arguments, include_tools=False)
    ):
        parser.error("--unpack 不能与压缩设置或 --dry-run 同时使用")
    if arguments.unpack is None and unpack_options:
        parser.error("--password、--password-file 和 --layers 仅用于 --unpack")
    return arguments
