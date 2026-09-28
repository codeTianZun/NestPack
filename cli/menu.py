"""面向人类的数字菜单，任务结束后返回菜单。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from cli.args import create_parser, parse_arguments
from cli.compress_cmd import CompressionOptions, run_compress
from cli.configuration import absolute_config, validate_config, write_task_config
from cli.prompts import ask_menu, ask_output_directory, ask_source_paths, ask_yes_no, read_password
from cli.unpack_cmd import run_unpack
from cli.video_cmd import run_video
from cli.wizard import (
    ask_config_path,
    create_config_interactively,
    edit_config,
    print_task_settings,
)
from core.cancellation import CancelledError
from core.config import load_config
from core.filesystem import normalize_user_path
from core.models import DEFAULT_CONFIG_PATH, AppConfig, ConfigError
from platforms import get_archive_platform
from platforms.tool_installer import install_requested_tools


def _repair_sources(config: AppConfig) -> AppConfig:
    sources = config.effective_source_paths()
    missing = [value for value in sources if not normalize_user_path(value).exists()]
    if sources and not missing:
        return config
    print("\n来源尚未设置或已不存在：")
    for value in missing:
        print(f"  {value}")
    if not ask_yes_no("是否重新选择来源", default=True):
        raise CancelledError("已返回任务设置。")
    paths = ask_source_paths("新的来源路径（多个用分号 ; 分隔）：")
    return replace(config, source_path=str(paths[0]), source_paths=[str(path) for path in paths])


def _task_session(config: AppConfig, config_path: Path | None) -> None:
    """运行和保存各自明确选择，失败时保留正在编辑的任务。"""
    while True:
        print_task_settings(config)
        choice = ask_menu(
            "任务操作",
            {
                1: "直接运行",
                2: "保存配置",
                3: "保存并运行",
                4: "修改设置",
                5: "预览计划",
                6: "安装压缩工具",
                0: "返回主菜单",
            },
            default=0,
        )
        try:
            if choice == 0:
                return
            if choice == 4:
                config = edit_config(config)
                continue
            if choice == 6:
                _install_menu()
                continue
            if choice == 2:
                path = ask_config_path(config_path or DEFAULT_CONFIG_PATH)
                config = validate_config(config)
                if (
                    path.exists()
                    and path != config_path
                    and not ask_yes_no(f"是否替换配置：{path}")
                ):
                    continue
                write_task_config(path, config, config_path)
                config_path = path
                print(f"配置已保存：{path}")
                if config.persist_passwords and any(
                    layer.password for layer in config.all_layers()
                ):
                    print("该配置包含明文密码，请妥善保管。")
                continue
            config = _repair_sources(config)
            save_path = ask_config_path(config_path or DEFAULT_CONFIG_PATH) if choice == 3 else None
            run_compress(
                config,
                config_path,
                CompressionOptions(
                    dry_run=choice == 5,
                    save_path=save_path,
                    confirm=True,
                ),
            )
            if choice != 5:
                return
        except (CancelledError, KeyboardInterrupt):
            print("\n任务已取消，可以继续修改设置。")
        except (ConfigError, OSError, RuntimeError) as error:
            print(f"\n任务未完成：{error}\n可选择“修改设置”后重试，或返回主菜单。")


def _unpack_menu() -> None:
    print("\n解包嵌套归档：分卷请选择第一卷。")
    while True:
        raw = input("压缩包路径：").strip()
        if not raw:
            print("请输入压缩包路径。")
            continue
        archive = normalize_user_path(raw)
        if archive.is_file():
            break
        print(f"找不到压缩包文件：{archive}")
    output = ask_output_directory(archive.parent / f"{archive.stem}_unpacked")
    argv = ["--unpack", str(archive), "--output", str(output)]
    choice = ask_menu(
        "候选密码",
        {
            1: "直接输入候选密码",
            2: "读取密码文件",
            3: "读取配置中的密码和工具路径",
            4: "逐层询问",
        },
        default=4,
    )
    if choice == 1:
        print("逐个输入候选密码，空输入结束。")
        while password := read_password("候选密码："):
            argv.append("--password=" + password)
    elif choice == 2:
        argv.extend(["--password-file", str(ask_config_path(Path.cwd() / "passwords.txt"))])
    elif choice == 3:
        argv.extend(["--config", str(ask_config_path(DEFAULT_CONFIG_PATH))])
    while True:
        raw = input("解包层数（回车自动识别；原始载荷本身为压缩包时可指定）：").strip()
        if not raw:
            break
        if raw.isdecimal() and int(raw) >= 1:
            argv.extend(["--layers", raw])
            break
        print("请输入不小于 1 的整数，或回车自动识别。")
    if ask_yes_no("是否指定归档工具路径"):
        for flag, label in (("--rar-path", "RAR"), ("--sevenzip-path", "7-Zip")):
            value = input(f"{label} 程序路径（回车自动检测）：").strip()
            if value:
                argv.extend([flag, value])
    print(f"\n归档：{archive}\n解包到：{output}")
    if ask_yes_no("开始解包", default=True):
        run_unpack(parse_arguments(argv))


def _install_menu() -> None:
    platform = get_archive_platform()
    for kind, label in (("rar", "RAR"), ("7z", "7-Zip")):
        print(f"{label}：{platform.find_tool(kind) or '未检测到'}")
    choice = ask_menu(
        "获取压缩工具",
        {
            1: "RAR / WinRAR 官网安装指引",
            2: "自动安装 7-Zip",
            3: "显示 RAR 指引并安装 7-Zip",
            0: "返回",
        },
        default=0,
    )
    if choice:
        install_requested_tools({1: "rar", 2: "7z", 3: "all"}[choice])


def _video_menu() -> None:
    choice = ask_menu("视频融合", {1: "融合已有归档与 MP4", 2: "从融合视频提取原归档", 0: "返回"})
    if choice == 0:
        return
    raw = input("已有压缩包路径：" if choice == 1 else "融合视频路径：").strip()
    if not raw:
        raise CancelledError("已返回主菜单。")
    source = normalize_user_path(raw)
    argv = ["--fuse-archive" if choice == 1 else "--extract-video-archive", str(source)]
    if choice == 1:
        video = input("载体 MP4 路径：").strip()
        argv.extend(["--video", video])
    output = ask_output_directory(source.parent / "video_output")
    argv.extend(["--output", str(output)])
    if ask_yes_no("允许覆盖输出目录中的同名成品"):
        argv.append("--overwrite-existing")
    run_video(parse_arguments(argv))


def run_menu(default_config: Path | None = None) -> int:
    """无参数启动先展示菜单，在用户选择后才加载配置或检查来源。"""
    selected_config = default_config or DEFAULT_CONFIG_PATH
    while True:
        try:
            choice = ask_menu(
                "NestPack 主菜单",
                {
                    1: "新建压缩任务",
                    2: "解包文件",
                    3: "运行已有配置",
                    4: "修改已有配置",
                    5: "检测 / 安装压缩工具",
                    6: "参数调用帮助",
                    7: "视频融合 / 提取原归档",
                    0: "退出",
                },
            )
        except (KeyboardInterrupt, EOFError):
            print("\n已退出。")
            return 0
        if choice == 0:
            print("再见。")
            return 0
        try:
            if choice == 1:
                _task_session(create_config_interactively(), None)
            elif choice == 2:
                _unpack_menu()
            elif choice in (3, 4):
                selected_config = ask_config_path(selected_config)
                config = absolute_config(
                    load_config(selected_config, allow_incomplete=True), selected_config
                )
                if choice == 4:
                    config = edit_config(config)
                _task_session(config, selected_config)
            elif choice == 5:
                _install_menu()
            elif choice == 6:
                create_parser().print_help()
            elif choice == 7:
                _video_menu()
        except EOFError:
            print("\n输入已结束，已退出。")
            return 0
        except (KeyboardInterrupt, CancelledError):
            print("\n已取消，返回主菜单。")
        except (ConfigError, OSError, RuntimeError) as error:
            print(f"\n操作未完成：{error}\n可在主菜单中新建任务、修改配置或安装工具。")
