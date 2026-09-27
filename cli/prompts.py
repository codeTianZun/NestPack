"""终端交互问答与无头环境保护。

两类职责：

1. ask_* 原子问答：路径、整数、是否、密码等，全部带输入校验循环，
   输入不合法时反复询问直到得到可用值；向导（wizard.py）把它们
   组装成完整配置。
2. 无头环境检测：需要交互且 stdin 未连接真实终端时抛出 ConfigError。
"""

from __future__ import annotations

import getpass
import sys
from dataclasses import replace
from pathlib import Path
from typing import TextIO

from core.backends import SUPPORTED_FORMATS, get_backend
from core.config import validate_archive_name, validate_password
from core.filesystem import normalize_user_path
from core.models import FORMAT_RAR, AppConfig, ConfigError, LayerConfig

# ---------- 路径与基础值问答 ----------


def ask_menu(prompt: str, options: dict[int, str], default: int | None = None) -> int:
    """显示数字选项，错误输入留在当前问题。"""
    print(f"\n{prompt}")
    for number, label in options.items():
        print(f"  {number}. {label}")
    suffix = f"（回车选择 {default}）" if default is not None else ""
    while True:
        raw = input(f"请输入选项{suffix}：").strip()
        if not raw and default is not None:
            return default
        try:
            number = int(raw)
        except ValueError:
            print("请输入菜单中的数字。")
            continue
        if number in options:
            return number
        print("没有这个选项，请重新选择。")


def ask_source_paths(prompt: str) -> list[Path]:
    """循环询问，直到至少输入一个存在的文件或目录；多个路径用分号分隔。"""
    while True:
        raw_values = input(prompt).strip()
        if not raw_values:
            print("路径不能为空。")
            continue
        paths: list[Path] = []
        failed = False
        for raw_value in raw_values.split(";"):
            raw_value = raw_value.strip()
            if not raw_value:
                continue
            try:
                path = normalize_user_path(raw_value)
            except (OSError, RuntimeError, ValueError) as error:
                print(f"路径无效：{error}")
                failed = True
                break
            if not path.exists():
                print(f"找不到该文件或文件夹：{path}")
                failed = True
                break
            paths.append(path)
        if failed:
            continue
        if paths:
            return paths
        print("至少需要输入一个路径。")


def ask_output_directory(default: Path) -> Path:
    """询问输出目录，目录在执行任务时创建。"""
    while True:
        raw_value = input(f"输出目录（直接回车使用 {default}）：").strip()
        try:
            path = default if not raw_value else normalize_user_path(raw_value)
        except (OSError, RuntimeError, ValueError) as error:
            print(f"无法使用输出目录：{error}")
            continue
        if path.exists() and not path.is_dir():
            print("输出路径不是文件夹。")
            continue
        return path.resolve()


def ask_positive_integer(
    prompt: str,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    """读取带上下限的整数，统一处理层数和恢复记录比例。"""
    while True:
        raw_value = input(prompt).strip()
        try:
            value = int(raw_value)
        except ValueError:
            print("请输入整数。")
            continue
        if value < minimum or (maximum is not None and value > maximum):
            if maximum is None:
                print(f"请输入不小于 {minimum} 的整数。")
            else:
                print(f"请输入 {minimum} 到 {maximum} 之间的整数。")
            continue
        return value


def ask_yes_no(prompt: str, default: bool = False, *, output_stream: TextIO | None = None) -> bool:
    """读取数字或中文、英文的是/否输入。"""
    suffix = f"[1 是 / 2 否，回车{'是' if default else '否'}]"
    stream = output_stream or sys.stdout
    while True:
        print(f"{prompt} {suffix}：", end="", file=stream, flush=True)
        raw_value = input().strip().lower()
        if not raw_value:
            return default
        if raw_value in {"1", "y", "yes", "是", "好"}:
            return True
        if raw_value in {"2", "n", "no", "否", "不"}:
            return False
        print("请输入 1（是）或 2（否），也可使用 y/n。", file=stream)


# ---------- 密码读取 ----------


def read_password(prompt: str, *, output_stream: TextIO | None = None) -> str:
    """读取密码；stdin 非终端（管道/无人值守调用）时直接读一行。

    getpass 在 POSIX 上打开 /dev/tty、Windows 上读控制台输入缓冲，
    都无视 stdin 重定向：有终端但无人输入时会永久阻塞。因此仅在
    stdin 是真实终端时才用 getpass 隐藏回显，否则从 stdin 读一行，
    输入流结束抛 EOFError，由调用方处理。
    """
    stream = output_stream or sys.stdout
    if stdin_is_interactive():
        return getpass.getpass(prompt, stream=stream)
    print(prompt, end="", file=stream, flush=True)
    line = sys.stdin.readline()
    if line == "":
        raise EOFError("输入流已结束")
    return line.rstrip("\r\n")


def ask_password(
    layer_number: int, archive_format: str = FORMAT_RAR, *, output_stream: TextIO | None = None
) -> str:
    """读取一层的密码并确认两次；空密码表示该层不加密。"""
    while True:
        password = read_password(
            f"第 {layer_number} 层密码（直接回车表示不设密码，终端输入时不会显示）：",
            output_stream=output_stream,
        )
        if not password:
            return ""
        try:
            validate_password(password, archive_format)
        except ValueError as error:
            print(f"密码无效：{error}", file=output_stream or sys.stdout)
            continue
        confirmation = read_password("再次输入密码：", output_stream=output_stream)
        if password == confirmation:
            return password
        print("两次密码不一致，请重新输入。", file=output_stream or sys.stdout)


# ---------- 逐层配置问答 ----------


def ask_archive_format(layer_number: int) -> str:
    """通过数字选择压缩格式。"""
    formats = list(SUPPORTED_FORMATS)
    choice = ask_menu(
        f"第 {layer_number} 层压缩格式",
        {index: name.upper() for index, name in enumerate(formats, start=1)},
        default=1,
    )
    return formats[choice - 1]


def ask_archive_name(
    layer_number: int,
    default_name: str,
    forbidden_names: set[str],
    archive_format: str = FORMAT_RAR,
) -> str:
    """读取并校验一层的文件名，检查与已收集的层名是否重复。"""
    while True:
        raw_name = input(f"第 {layer_number} 层压缩文件名（直接回车使用 {default_name}）：").strip()
        try:
            archive_name = validate_archive_name(raw_name or default_name, archive_format)
        except ValueError as error:
            print(f"文件名无效：{error}")
            continue
        if archive_name.casefold() in forbidden_names:
            print("该文件名与其他压缩层重复，请换一个名称。")
            continue
        return archive_name


def ask_layer_config(
    layer_number: int,
    source_stem: str,
    forbidden_names: set[str],
) -> LayerConfig:
    """通过交互收集一层配置。"""
    archive_format = ask_archive_format(layer_number)
    default_name = f"{source_stem}_{layer_number}{get_backend(archive_format).archive_extension}"
    archive_name = ask_archive_name(layer_number, default_name, forbidden_names, archive_format)
    password = ask_password(layer_number, archive_format)

    recovery_percent: int | None = None
    if archive_format == FORMAT_RAR and ask_yes_no(
        f"第 {layer_number} 层是否添加恢复记录", default=False
    ):
        recovery_percent = ask_positive_integer(
            "恢复记录百分比（1-100）：",
            minimum=1,
            maximum=100,
        )

    return LayerConfig(
        archive_name=archive_name,
        password=password,
        recovery_percent=recovery_percent,
        format=archive_format,
        name_template=f"{{stem}}_{layer_number}" if archive_name == default_name else None,
        password_set=bool(password),
    )


# ---------- 运行期密码补问 ----------


def prompt_missing_passwords(
    config: AppConfig, *, output_stream: TextIO | None = None
) -> AppConfig:
    """为 password_set=true 但密码为空的层交互补问密码。

    persist_passwords=false 的配置不落盘密码，只保存 password_set 标记；
    不补问会静默压出无加密的压缩包。补问结果只用于本次运行。
    """
    layers: list[LayerConfig] = []
    changed = False
    for layer_number, layer in enumerate(config.layers, start=1):
        if layer.password_set and not layer.password:
            print(
                f"第 {layer_number} 层标记为需要密码，但配置中未保存密码。",
                file=output_stream or sys.stdout,
            )
            password = ask_password(layer_number, layer.format, output_stream=output_stream)
            layer = replace(layer, password=password, password_set=bool(password))
            changed = True
        layers.append(layer)
    return replace(config, layers=layers) if changed else config


# ---------- 无头环境检测 ----------


def stdin_is_interactive() -> bool:
    """判断 stdin 是否真的连接到可交互的控制台。

    Windows 的 CRT 对 NUL 等字符设备一律误报 isatty=True（计划任务里
    常见 < NUL 重定向），因此再用 GetConsoleMode 确认是真实控制台；
    POSIX 直接采用 isatty 的结果。
    """
    if not sys.stdin.isatty():
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            import msvcrt

            console_mode = ctypes.c_uint()
            handle = msvcrt.get_osfhandle(sys.stdin.fileno())
            return bool(ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(console_mode)))
        except (OSError, ValueError, AttributeError):
            return False
    return True


def require_interactive_tty(reason: str) -> None:
    """需要交互且 stdin 未连接真实终端时抛出 ConfigError。"""
    if not stdin_is_interactive():
        raise ConfigError(f"{reason}；当前环境无交互终端，请改用 --config 指定已准备好的配置文件")


def require_interactive_for_missing_passwords(config: AppConfig) -> None:
    """配置标记了需要密码但未保存密码时，无头环境无法补问，提前报错。"""
    if not stdin_is_interactive() and any(
        layer.password_set and not layer.password for layer in config.layers
    ):
        raise ConfigError(
            "配置中有层标记为需要密码但未保存密码（persist_passwords=false），"
            "当前环境无交互终端无法补问；请使用保存了密码的配置文件"
        )
