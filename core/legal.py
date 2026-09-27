"""CLI 与 GUI 共用的版权、许可证及源码获取说明。"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_URL = "https://github.com/codeTianZun/NestPack"
LICENSE_SUMMARY = (
    "Copyright (C) 2026 codeTianZun · GPL-3.0-only\n"
    "本程序不提供担保；你可以按 GPL 第 3 版修改和再分发。"
)
LEGAL_DOCUMENTS = ("LICENSE", "THIRD_PARTY_NOTICES.md")


def license_text() -> str:
    """读取源码目录或冻结程序资源中的法律文档。"""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    documents = [root / name for name in LEGAL_DOCUMENTS]
    documents.extend(path for path in sorted((root / "licenses").rglob("*")) if path.is_file())
    return f"{LICENSE_SUMMARY}\n源码：{PROJECT_URL}\n\n" + "\n\n".join(
        f"===== {path.relative_to(root).as_posix()} =====\n"
        + path.read_text(encoding="utf-8", errors="replace")
        for path in documents
    )
