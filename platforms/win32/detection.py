"""Windows 上的 WinRAR / 7-Zip 命令行程序检测。"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from core.filesystem import normalize_user_path
from core.models import FORMAT_RAR, FORMAT_ZIP, ConfigError
from platforms.tools import tool_directory_candidates

RAR_TOOL_NAMES = ("WinRAR.exe", "Rar.exe")
ZIP_TOOL_NAMES = ("7z.exe", "7za.exe", "7zz.exe")
SEVENZIP_TOOL_NAMES = (*ZIP_TOOL_NAMES, "7zr.exe")


def executable_candidates(kind: str = "rar") -> tuple[str, ...]:
    """返回支持指定格式的 Windows 命令行程序名。"""
    if kind == FORMAT_RAR:
        return RAR_TOOL_NAMES
    return ZIP_TOOL_NAMES if kind == FORMAT_ZIP else SEVENZIP_TOOL_NAMES


def find_winrar_from_registry() -> Path | None:
    """读取 Windows 的 App Paths 注册表项，兼容 32 位和 64 位视图。"""
    if sys.platform != "win32":
        return None

    try:
        import winreg
    except ImportError:
        return None

    registry_locations = (
        (
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\WinRAR.exe",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\WinRAR.exe",
        ),
    )
    registry_views = (0, winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY)

    for root_key, subkey in registry_locations:
        for registry_view in registry_views:
            try:
                with winreg.OpenKey(
                    root_key,
                    subkey,
                    0,
                    winreg.KEY_READ | registry_view,
                ) as key:
                    executable = Path(winreg.QueryValue(key, None))
            except OSError:
                continue
            if executable.is_file():
                return executable.resolve()
    return None


def find_sevenzip_from_registry(names: tuple[str, ...]) -> Path | None:
    """读取 7-Zip 安装时写入的注册表安装目录。"""
    if sys.platform != "win32":
        return None

    try:
        import winreg
    except ImportError:
        return None

    for registry_view in (0, winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\7-Zip",
                0,
                winreg.KEY_READ | registry_view,
            ) as key:
                install_directory = Path(winreg.QueryValueEx(key, "Path")[0])
        except OSError:
            continue
        for name in names:
            candidate = install_directory / name
            if candidate.is_file():
                return candidate.resolve()
    return None


def _find_tool(kind: str, names: tuple[str, ...]) -> Path | None:
    """按目录优先级查找给定候选程序。"""
    # 优先查找程序同目录的 dependencies。
    for directory in tool_directory_candidates(kind):
        for name in names:
            candidate = directory / name
            if candidate.is_file():
                return candidate.resolve()

    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found).resolve()

    registry_result = (
        find_winrar_from_registry()
        if kind == FORMAT_RAR
        else find_sevenzip_from_registry(names)
    )
    if registry_result:
        return registry_result

    candidate_roots = [
        os.environ.get("ProgramW6432"),
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
    ]
    install_directory = "WinRAR" if kind == FORMAT_RAR else "7-Zip"
    for root in filter(None, candidate_roots):
        for name in names:
            candidate = Path(root) / install_directory / name
            if candidate.is_file():
                return candidate.resolve()
    return None


def find_tool(kind: str = "rar") -> Path | None:
    """按格式查找工具；7z 优先使用同时支持 ZIP 的完整程序。"""
    if kind == FORMAT_RAR:
        return _find_tool(kind, RAR_TOOL_NAMES)
    detected = _find_tool(kind, ZIP_TOOL_NAMES)
    if detected is not None or kind == FORMAT_ZIP:
        return detected
    return _find_tool(kind, ("7zr.exe",))


def resolve_tool(
    configured_path: str, config_directory: Path, kind: str = "rar"
) -> Path:
    """将 auto 或配置中的具体路径转换成可执行文件路径。"""
    if configured_path.strip().lower() == "auto":
        detected = find_tool(kind)
        if detected:
            return detected
        if kind != FORMAT_RAR:
            expected = " / ".join(executable_candidates(kind))
            raise ConfigError(
                f"sevenzip_path 为 auto，但没有找到支持 {kind} 的 7-Zip 命令行；"
                f"请安装 7-Zip，或填写 {expected} 路径"
            )
        raise ConfigError(
            "winrar_path 为 auto，但没有找到 WinRAR；请填写 WinRAR.exe 或 Rar.exe 路径"
        )

    executable = normalize_user_path(configured_path, config_directory)
    if not executable.is_file():
        raise ConfigError(f"找不到命令行程序：{executable}")
    if kind == FORMAT_ZIP and executable.name.lower() == "7zr.exe":
        raise ConfigError(
            "7zr.exe 仅支持 7z 格式；ZIP 需要 7z.exe / 7za.exe / 7zz.exe，"
            "请修改 sevenzip_path，或使用 CLI 的 --install-tools 7z 模式安装"
        )
    allowed = {name.lower() for name in executable_candidates(kind)}
    if executable.name.lower() not in allowed:
        expected = " / ".join(sorted(allowed))
        raise ConfigError(f"工具路径必须指向 {expected} 之一：{executable}")
    return executable
