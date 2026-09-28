"""识别伪装分卷，并以标准卷名接入解包工作目录。"""

from __future__ import annotations

from pathlib import Path

from core.backends import ArchiveBackend, iter_backends
from core.cancellation import Cancellation
from core.filesystem import link_or_copy_file
from core.models import FORMAT_RAR
from core.rar_content import rar_signature_offset


def find_disguised_volume_set(
    archive: Path,
) -> tuple[list[Path], str, ArchiveBackend] | None:
    """识别被伪装扩展名改名的成套分卷，返回 (按卷号升序的卷, 基准名, 后端)。

    条件：同目录、同基准名、同伪装扩展名，卷号从 1 连续，且每个
    文件都带该格式的文件头。rar 伪装名形如 foo.part1.bin，
    7z / zip 伪装名形如 foo.bin.001（两者同形，靠文件头区分）。
    """
    for backend in iter_backends():
        parsed = backend.parse_disguised_volume(archive.name)
        if parsed is None:
            continue
        base, _number, extension = parsed
        sfx = backend.format_name == FORMAT_RAR and (rar_signature_offset(archive) or 0) > 0
        try:
            siblings = list(archive.parent.iterdir())
        except OSError:
            return None
        found: list[tuple[int, Path]] = []
        for path in siblings:
            standard = backend.volume_name_pattern.fullmatch(path.name) if sfx else None
            if (standard is not None and standard.group(1).casefold() == base.casefold()
                    and int(standard.group(2)) > 1):
                found.append((int(standard.group(2)), path))
                continue
            sibling = backend.parse_disguised_volume(path.name)
            if (
                sibling is not None
                and sibling[0].casefold() == base.casefold()
                and sibling[2].casefold() == extension.casefold()
            ):
                found.append((sibling[1], path))
        if not found:
            continue
        found.sort()
        numbers = [number for number, _path in found]
        if numbers != list(range(1, len(found) + 1)):
            continue
        if not all(backend.looks_like(path) for _number, path in found):
            continue
        return [path for _number, path in found], base, backend
    return None


def stage_volume_set(
    volumes: list[Path], base: str, backend: ArchiveBackend, staging: Path,
    cancellation: Cancellation,
) -> Path:
    """把分卷套以标准卷名接入暂存目录（硬链接优先），返回第一卷。

    优先硬链接，链接失败时按块复制，原文件保持不动。
    暂存目录随工作目录在解包成功后清理，失败或取消时保留。
    """
    staging.mkdir(parents=True, exist_ok=True)
    staged: list[Path] = []
    for number, volume in enumerate(volumes, start=1):
        target = staging / backend.standard_volume_name(base, number)
        link_or_copy_file(volume, target, cancellation)
        staged.append(target)
    return staged[0]
