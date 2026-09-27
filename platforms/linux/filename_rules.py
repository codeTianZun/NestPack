"""Linux 文件名校验。"""

from __future__ import annotations


def validate_filename(raw_name: str) -> str:
    """校验文件名合法性；.rar / .7z / .zip 后缀由 core 按格式补全。"""
    name = raw_name.strip()
    if not name:
        raise ValueError("文件名不能为空")
    if name in {".", ".."}:
        raise ValueError("文件名无效")
    if "/" in name:
        raise ValueError('文件名不能包含 "/"')
    if "\x00" in name:
        raise ValueError("文件名不能包含 NUL 字符")
    return name
