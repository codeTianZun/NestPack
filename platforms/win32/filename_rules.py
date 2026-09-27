"""Windows 文件名校验。"""

from __future__ import annotations

# Windows 不允许这些字符或保留名称出现在普通文件名中。
INVALID_FILENAME_CHARS = set('<>:"/\\|?*')
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
    *(f"COM{number}" for number in "¹²³"),
    *(f"LPT{number}" for number in "¹²³"),
}


def validate_filename(raw_name: str) -> str:
    """校验文件名合法性；扩展名补全由 core 按格式处理。"""
    if any(ord(character) < 32 for character in raw_name):
        raise ValueError("文件名不能包含控制字符（U+0000–U+001F）")
    name = raw_name.strip()
    if not name:
        raise ValueError("文件名不能为空")
    if name in {".", ".."}:
        raise ValueError("文件名无效")
    if any(character in INVALID_FILENAME_CHARS for character in name):
        raise ValueError('文件名不能包含 < > : " / \\ | ? *')
    if name.endswith((" ", ".")):
        raise ValueError("文件名不能以空格或句点结尾")

    stem = name.split(".", 1)[0].rstrip(" ").upper()
    if stem in WINDOWS_RESERVED_NAMES:
        raise ValueError("该名称是 Windows 保留名称")
    return name
