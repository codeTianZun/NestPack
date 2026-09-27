"""CLI 入口：菜单、参数任务和统一的文本 / JSON 结果。"""

from __future__ import annotations

import argparse
import sys
from contextlib import redirect_stdout

from cli.args import UsageError, create_parser, parse_arguments
from cli.compress_cmd import CompressionOptions, run_compress
from cli.configuration import configuration_from_arguments
from cli.display import classify_error, print_banner, print_json
from cli.prompts import require_interactive_tty, stdin_is_interactive
from cli.unpack_cmd import run_unpack
from cli.wizard import initialize_config
from core.cancellation import CancelledError
from core.filesystem import normalize_user_path
from core.logging_utils import setup_logging
from core.models import DEFAULT_CONFIG_PATH
from core.result_summary import MANIFEST_SCHEMA_VERSION
from platforms import get_archive_platform
from platforms.tool_installer import install_requested_tools


def _print_error(message: str, kind: str, machine_mode: bool) -> None:
    if machine_mode:
        print_json(
            {
                "tool": "nestpack",
                "schema_version": MANIFEST_SCHEMA_VERSION,
                "status": "error",
                "error_kind": kind,
                "error": message,
            }
        )
    else:
        print(f"错误：{message}", file=sys.stderr)


def _run(arguments: argparse.Namespace) -> int:
    get_archive_platform()
    if arguments.menu:
        if not stdin_is_interactive():
            create_parser().print_help()
            return 0
        from cli.menu import run_menu

        print_banner()
        path = normalize_user_path(str(arguments.config)) if arguments.config is not None else None
        return run_menu(path)
    if not arguments.json and not arguments.dry_run:
        print_banner()
    if arguments.install_tools is not None:
        with redirect_stdout(sys.stderr if arguments.json else sys.stdout):
            install_requested_tools(arguments.install_tools)
        if arguments.json:
            print_json(
                {
                    "tool": "nestpack",
                    "schema_version": MANIFEST_SCHEMA_VERSION,
                    "status": "ok",
                    "mode": "install",
                    "tools": arguments.install_tools,
                    "manual_install": ["rar"]
                    if arguments.install_tools in ("rar", "all") else [],
                }
            )
        return 0
    if arguments.unpack is not None:
        return run_unpack(arguments)
    if arguments.init:
        if arguments.non_interactive:
            raise UsageError(
                "--init 需要交互；无交互任务请用 --source / --layer，并用 --save-config 保存"
            )
        require_interactive_tty("--init 需要交互式终端")
        path = (
            normalize_user_path(str(arguments.config))
            if arguments.config is not None
            else DEFAULT_CONFIG_PATH
        )
        with redirect_stdout(sys.stderr if arguments.json else sys.stdout):
            config = initialize_config(path, force_request=True, assume_yes=arguments.yes)
        if config is None:
            raise CancelledError("已保留原配置。")
        if arguments.json:
            print_json(
                {
                    "tool": "nestpack",
                    "schema_version": MANIFEST_SCHEMA_VERSION,
                    "status": "ok",
                    "mode": "init",
                    "config_path": str(path),
                }
            )
        return 0
    config, config_path = configuration_from_arguments(arguments)
    return run_compress(
        config,
        config_path,
        CompressionOptions(
            json_mode=arguments.json,
            dry_run=arguments.dry_run,
            assume_yes=arguments.yes,
            non_interactive=arguments.non_interactive,
            save_path=normalize_user_path(str(arguments.save_config))
            if arguments.save_config is not None
            else None,
        ),
    )


def main(argv: list[str] | None = None) -> int:
    """统一处理解析、编码、执行和取消错误，参数任务结束后直接退出。"""
    raw = list(sys.argv[1:] if argv is None else argv)
    machine_mode = any(flag in raw for flag in ("--json", "--dry-run"))
    logger = setup_logging("cli")
    try:
        if machine_mode and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        return _run(parse_arguments(raw))
    except UsageError as error:
        _print_error(str(error), "usage_error", machine_mode)
        if not machine_mode:
            print("使用 --help 查看参数示例，或无参数启动数字菜单。", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, CancelledError) as error:
        _print_error(str(error) or "操作已由用户中止。", "cancelled", machine_mode)
        return 130
    except EOFError:
        _print_error(
            "输入流已结束；自动调用请提供完整参数并使用 --non-interactive。",
            "config_error",
            machine_mode,
        )
        return 1
    except Exception as error:
        logger.exception("命令行异常退出")
        _print_error(str(error), classify_error(error), machine_mode)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
