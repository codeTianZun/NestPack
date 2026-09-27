"""界面路径选择的起始目录；路径展开复用核心的配置目录规则。"""

from pathlib import Path

from core.filesystem import normalize_user_path


def selection_directory(value: str, config_dir: Path) -> Path:
    """已有目录直接打开，文件或待创建路径从父目录开始选择。"""
    if not value.strip() or value.strip().lower() == "auto":
        return config_dir
    path = normalize_user_path(value, config_dir)
    return path if path.is_dir() else path.parent
