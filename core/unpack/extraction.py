"""单层解压：候选密码、交互补问与失败尝试的现场清理。"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from pathlib import Path

from core.backends import ArchiveBackend, describe_exit_code
from core.cancellation import Cancellation
from core.filesystem import cleanup_path
from core.process import run_command

# 未加密层的探针密码：解密命令必须始终带 -p，否则 WinRAR 遇到加密层
# 会弹出密码对话框卡住进程；对未加密层 -p 会被忽略（已实测），
# 对加密层错误密码只会快速失败。进程内随机，避免恰好命中真实密码。
NO_PASSWORD_PROBE = f"nestpack-no-password-{uuid.uuid4().hex[:12]}"


def _clear_directory(directory: Path) -> None:
    """删除目录内的全部条目，保留目录本身（密码试错后重置现场）。"""
    try:
        entries = list(directory.iterdir())
    except OSError:
        return
    for entry in entries:
        cleanup_path(entry)


def _try_extract(
    tool: Path,
    backend: ArchiveBackend,
    archive: Path,
    destination: Path,
    password: str,
    cancellation: Cancellation,
    output_cb: Callable[[str], None] | None,
) -> bool:
    """用给定密码尝试解压一层，成功返回 True（密码对未加密层无影响）。"""
    command = backend.build_extract_command(tool, archive, password)

    def fail(message: str) -> bool:
        if output_cb is not None:
            # 加前缀与 rar 正常输出区分，便于在日志里一眼定位失败原因。
            output_cb(f"[失败] {message}")
        return False

    return_code = run_command(
        command, cwd=destination, cancellation=cancellation,
        capture_output=True, output_cb=output_cb, hide_console=True,
    )
    cancellation.check()
    if return_code != 0:
        return fail(describe_exit_code(return_code, tool, backend.exit_codes))
    return True


def extract_layer(
    tool: Path,
    backend: ArchiveBackend,
    archive: Path,
    destination: Path,
    candidates: Sequence[str],
    known_passwords: list[str],
    password_prompt: Callable[[int], str] | None,
    layer_index: int,
    cancellation: Cancellation,
    output_cb: Callable[[str], None] | None,
) -> None:
    """解压一层：先试探针密码与已知密码，再试候选列表，最后交互补问。

    探针密码用于未加密层（-p 对未加密层无效，被直接忽略）；加密层
    遇到错误密码只会返回非零退出码，不会弹窗，因此可以安全地逐个尝试。
    只加密内容（非全加密头）的第三方包密码错时可能已解出一部分文件，
    每次尝试失败后清空目标目录，避免残留物干扰下一层的内容识别。
    """
    attempts = list(
        dict.fromkeys([NO_PASSWORD_PROBE, *known_passwords, *candidates])
    )
    for password in attempts:
        cancellation.check()
        if _try_extract(
            tool, backend, archive, destination, password, cancellation, output_cb
        ):
            if password != NO_PASSWORD_PROBE and password not in known_passwords:
                # 同一密码常被多层复用，之后每层优先尝试。
                known_passwords.append(password)
            return
        cancellation.check()
        _clear_directory(destination)
    while password_prompt is not None:
        cancellation.check()
        password = password_prompt(layer_index)
        if not password:
            break
        if _try_extract(
            tool, backend, archive, destination, password, cancellation, output_cb
        ):
            known_passwords.append(password)
            return
        cancellation.check()
        _clear_directory(destination)
    raise RuntimeError(
        f"第 {layer_index} 层解压失败：密码错误或压缩包损坏（{archive.name}）"
    )
