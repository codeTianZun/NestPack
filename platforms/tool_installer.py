"""提供 RAR 官网安装指引，并下载和安装 7-Zip 命令行工具。

本模块只依赖 Python 标准库，可由源码入口、CLI 与 PyInstaller 打包后的
GUI 共同调用。下载内容经 SHA256 校验后写入软件同目录的
``dependencies/7z``，保留随包许可与说明。
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from platforms.tools import TOOLS_DIRECTORY

OutputCallback = Callable[[str], None]

SEVENZIP_VERSION = "26.02"
SEVENZIP_RELEASE = "2602"
SEVENZIP_SOURCE_URL = "https://github.com/ip7z/7zip/archive/refs/tags/26.02.tar.gz"

RAR_DOWNLOAD_URL = "https://www.rarlab.com/download.htm"
RAR_LICENSE_URL = "https://www.rarlab.com/license.htm"

# 7-Zip 官方发布；安装时保留包内许可和说明文件。
SEVENZIP_WINDOWS_URL = (
    f"https://github.com/ip7z/7zip/releases/download/{SEVENZIP_VERSION}/7zr.exe"
)
SEVENZIP_WINDOWS_SHA256 = (
    "56b8cc9f4971cef253644fafe54063ed7fdca551d4dee0f8c6baa81b855acd72"
)
SEVENZIP_EXTRA_URL = (
    f"https://github.com/ip7z/7zip/releases/download/"
    f"{SEVENZIP_VERSION}/7z{SEVENZIP_RELEASE}-extra.7z"
)
SEVENZIP_EXTRA_SHA256 = (
    "081df9e9311dfd9c9e0e98c1c80180b99bb51e4cb24156b5f3057fe3c259d70a"
)
SEVENZIP_LINUX_URL = (
    f"https://github.com/ip7z/7zip/releases/download/"
    f"{SEVENZIP_VERSION}/7z{SEVENZIP_RELEASE}-linux-x64.tar.xz"
)
SEVENZIP_LINUX_SHA256 = (
    "41aaba7b1235304ab5aa0624530c67ae829496cd29e875925271efdccc28c03e"
)

SUPPORTED_TOOLS = ("rar", "7z", "all")
SUPPORTED_PLATFORMS = ("win32", "linux")
DOWNLOAD_TIMEOUT_SECONDS = 60


class ToolInstallError(RuntimeError):
    """表示外部压缩工具下载或安装失败。"""


class ToolChecksumError(ToolInstallError):
    """表示下载包未通过 SHA256 校验。"""


class UnsupportedPlatformError(ToolInstallError):
    """表示当前平台没有可用的官方下载包。"""


@dataclass(frozen=True)
class InstallPlanItem:
    """一次官方下载及其预期落盘位置。"""

    tool: str
    component: str
    version: str
    url: str
    sha256: str
    target: Path


def _resolve_request(tool: str, platform: str | None) -> tuple[tuple[str, ...], str]:
    if tool not in SUPPORTED_TOOLS:
        expected = " / ".join(SUPPORTED_TOOLS)
        raise ToolInstallError(f"不支持的工具选择：{tool}（应为 {expected}）")
    platform_name = platform or sys.platform
    if platform_name not in SUPPORTED_PLATFORMS:
        raise UnsupportedPlatformError(
            f"不支持的平台：{platform_name}；NestPack 仅支持 Windows 与 Linux。"
        )
    selected = ("rar", "7z") if tool == "all" else (tool,)
    return selected, platform_name


def _resolve_destination(destination: Path | str | None) -> Path:
    return Path(destination) if destination is not None else TOOLS_DIRECTORY


def get_install_plan(
    tool: str = "all",
    *,
    destination: Path | str | None = None,
    platform: str | None = None,
) -> tuple[InstallPlanItem, ...]:
    """返回指定平台与工具的下载计划，不联网也不创建目录。"""
    selected, platform_name = _resolve_request(tool, platform)
    root = _resolve_destination(destination)
    plan: list[InstallPlanItem] = []
    if "7z" in selected:
        if platform_name == "win32":
            plan.extend(
                (
                    InstallPlanItem(
                        "7z",
                        "7zr",
                        SEVENZIP_VERSION,
                        SEVENZIP_WINDOWS_URL,
                        SEVENZIP_WINDOWS_SHA256,
                        root / "7z" / "7zr.exe",
                    ),
                    InstallPlanItem(
                        "7z",
                        "7za",
                        SEVENZIP_VERSION,
                        SEVENZIP_EXTRA_URL,
                        SEVENZIP_EXTRA_SHA256,
                        root / "7z" / "7za.exe",
                    ),
                )
            )
        else:
            plan.append(
                InstallPlanItem(
                    "7z",
                    "7zz",
                    SEVENZIP_VERSION,
                    SEVENZIP_LINUX_URL,
                    SEVENZIP_LINUX_SHA256,
                    root / "7z" / "7zz",
                )
            )
    return tuple(plan)


def format_install_plan(
    tool: str = "all",
    *,
    destination: Path | str | None = None,
    platform: str | None = None,
) -> str:
    """把下载计划格式化为适合终端或 GUI 展示的中文文本。"""
    root = _resolve_destination(destination)
    plan = get_install_plan(tool, destination=root, platform=platform)
    lines = [rar_install_guide(platform)] if tool in ("rar", "all") else []
    if plan:
        lines.append(f"7-Zip 目标目录：{root}（软件同目录的 dependencies）")
    for item in plan:
        lines.append(f"[{item.component} {item.version}] {item.url}")
        lines.append(f"    → {item.target}")
    return "\n".join(lines)


def emit_install_plan(
    tool: str = "all",
    output_cb: OutputCallback = print,
    *,
    destination: Path | str | None = None,
    platform: str | None = None,
) -> tuple[InstallPlanItem, ...]:
    """通过回调展示下载计划，并返回结构化计划。"""
    plan = get_install_plan(tool, destination=destination, platform=platform)
    output_cb(format_install_plan(tool, destination=destination, platform=platform))
    return plan


def rar_install_guide(platform: str | None = None) -> str:
    """提供官方安装步骤、试用期限与许可入口。"""
    platform_name = platform or sys.platform
    steps = (
        "下载适合本机的 WinRAR 安装程序并按向导安装；随后重新打开 NestPack，"
        "或在运行环境中选择 WinRAR.exe / Rar.exe。"
        if platform_name == "win32"
        else "下载适合本机架构的 Linux RAR 包，按包内说明安装；"
        "将 rar 加入 PATH，或用 --rar-path 指定可执行文件。"
    )
    return (
        f"RAR / WinRAR 官网安装指引\n{RAR_DOWNLOAD_URL}\n{steps}\n"
        "RAR / WinRAR 是专有试用软件，最长免费试用 40 天，"
        f"之后继续使用需要购买许可。\n许可条款：{RAR_LICENSE_URL}"
    )


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, destination: Path) -> None:
    """下载到目标路径；校验由调用方在下载完成后统一执行。"""
    with urllib.request.urlopen(
        url, timeout=DOWNLOAD_TIMEOUT_SECONDS
    ) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def _verify(path: Path, expected_sha256: str) -> None:
    actual = _sha256_of(path)
    if actual == expected_sha256:
        return
    path.unlink(missing_ok=True)
    raise ToolChecksumError(
        f"SHA256 校验失败：{path.name}\n"
        f"期望：{expected_sha256}\n实际：{actual}\n"
        "官方包可能已更新，请核对来源后更新程序中的校验值。"
    )


def _download_verified(
    url: str,
    expected_sha256: str,
    destination: Path,
    output_cb: OutputCallback,
) -> None:
    output_cb(f"下载中：{url}")
    _download(url, destination)
    _verify(destination, expected_sha256)
    output_cb(f"SHA256 校验通过：{destination.name}")


def _extract_tarball(tarball: Path, destination: Path) -> None:
    """解压 tar 包；运行时支持 data 过滤器时启用该过滤器。"""
    try:
        with tarfile.open(tarball) as archive:
            archive.extractall(destination, filter="data")
    except TypeError:
        with tarfile.open(tarball) as archive:
            archive.extractall(destination)


def _mark_executable(directory: Path, names: tuple[str, ...]) -> None:
    for name in names:
        candidate = directory / name
        if candidate.is_file():
            candidate.chmod(candidate.stat().st_mode | 0o111)


def _replace_file(source: Path, destination: Path) -> None:
    """把已校验文件原子替换到目标，失败时保留原版本。"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}-",
            suffix=".part",
            delete=False,
        ) as staged:
            staged_path = Path(staged.name)
            with source.open("rb") as source_stream:
                shutil.copyfileobj(source_stream, staged)
        os.replace(staged_path, destination)
    finally:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)


def _write_source_information(directory: Path) -> None:
    """为安装后的 7-Zip 记录版本与对应源码入口。"""
    (directory / "SOURCE.txt").write_text(
        f"7-Zip {SEVENZIP_VERSION}\nCopyright (C) 1999-2026 Igor Pavlov\n"
        f"对应源码：{SEVENZIP_SOURCE_URL}\n"
        "许可：见本目录 License.txt；使用与构建说明见 readme.txt。\n",
        encoding="utf-8",
    )


def _install_sevenzip_windows(
    force: bool,
    destination: Path,
    output_cb: OutputCallback,
) -> None:
    directory = destination / "7z"
    reduced = directory / "7zr.exe"
    standalone = directory / "7za.exe"
    directory.mkdir(parents=True, exist_ok=True)

    if not force and reduced.is_file():
        output_cb(f"7zr 已存在，跳过（{reduced}；强制安装可覆盖）")
    else:
        with tempfile.TemporaryDirectory(prefix="nestpack-fetch-") as temporary:
            downloaded = Path(temporary) / "7zr.exe"
            _download_verified(
                SEVENZIP_WINDOWS_URL,
                SEVENZIP_WINDOWS_SHA256,
                downloaded,
                output_cb,
            )
            _replace_file(downloaded, reduced)
        output_cb(f"7zr 安装完成：{reduced}")

    documents = ("License.txt", "readme.txt", "7-zip.chm")
    if not force and standalone.is_file() and all(
        (directory / name).is_file() for name in (*documents, "SOURCE.txt")
    ):
        output_cb(f"7za 已存在，跳过（{standalone}；强制安装可覆盖）")
        return

    with tempfile.TemporaryDirectory(prefix="nestpack-fetch-") as temporary:
        temporary_directory = Path(temporary)
        extra = temporary_directory / "7z-extra.7z"
        _download_verified(
            SEVENZIP_EXTRA_URL,
            SEVENZIP_EXTRA_SHA256,
            extra,
            output_cb,
        )
        extraction = subprocess.run(
            [
                str(reduced),
                "e",
                str(extra),
                "-y",
                f"-o{temporary_directory}",
                "x64/7za.exe",
                *documents,
            ],
            capture_output=True,
            check=False,
        )
        extracted = temporary_directory / "7za.exe"
        if extraction.returncode != 0 or not extracted.is_file() or not all(
            (temporary_directory / name).is_file() for name in documents
        ):
            raise ToolInstallError(
                "7-Zip extra 包提取失败，程序或许可材料不完整；请重试或手动安装。"
            )
        _replace_file(extracted, standalone)
        for name in documents:
            _replace_file(temporary_directory / name, directory / name)
        _write_source_information(directory)
    output_cb(f"7za 安装完成：{standalone}（支持 -tzip 创建 ZIP）")


def _install_sevenzip_linux(
    force: bool,
    destination: Path,
    output_cb: OutputCallback,
) -> None:
    target = destination / "7z"
    executable = target / "7zz"
    if not force and executable.is_file() and all(
        (target / name).is_file() for name in ("License.txt", "readme.txt", "SOURCE.txt")
    ):
        output_cb(f"7z 已存在，跳过（{target}；强制安装可覆盖）")
        return

    with tempfile.TemporaryDirectory(prefix="nestpack-fetch-") as temporary:
        temporary_directory = Path(temporary)
        tarball = temporary_directory / "7z.tar.xz"
        extracted = temporary_directory / "extracted"
        _download_verified(
            SEVENZIP_LINUX_URL,
            SEVENZIP_LINUX_SHA256,
            tarball,
            output_cb,
        )
        extracted.mkdir()
        _extract_tarball(tarball, extracted)
        if not all(
            (extracted / name).is_file() for name in ("7zz", "License.txt", "readme.txt")
        ):
            raise ToolInstallError("7-Zip 官方包内容不完整：程序或许可材料缺失。")
        shutil.copytree(extracted, target, dirs_exist_ok=True)
        _write_source_information(target)
    _mark_executable(target, ("7zz", "7zzs"))
    output_cb(f"7z 安装完成：{executable}")


def install_requested_tools(
    tool: str = "all",
    force: bool = False,
    output_cb: OutputCallback = print,
    *,
    destination: Path | str | None = None,
    platform: str | None = None,
) -> None:
    """安装请求的工具；失败时抛 ToolInstallError。"""
    selected, platform_name = _resolve_request(tool, platform)
    root = _resolve_destination(destination)
    installers = {
        ("win32", "7z"): _install_sevenzip_windows,
        ("linux", "7z"): _install_sevenzip_linux,
    }
    for selected_tool in selected:
        if selected_tool == "rar":
            output_cb(rar_install_guide(platform_name))
            continue
        try:
            installers[(platform_name, selected_tool)](force, root, output_cb)
        except ToolInstallError:
            raise
        except (OSError, subprocess.SubprocessError, tarfile.TarError) as error:
            raise ToolInstallError(f"安装 {selected_tool} 失败：{error}") from error
    if "7z" in selected:
        output_cb("7-Zip 已就绪；主程序会优先使用 dependencies 中的工具。")
