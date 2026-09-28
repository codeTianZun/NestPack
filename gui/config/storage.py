"""GUI 持久化纯逻辑：默认配置、最近路径与文件选择框尺寸。"""

from __future__ import annotations

import json
from pathlib import Path

from core.filesystem import atomic_write_text
from core.models import SCRIPT_DIRECTORY, AppConfig, LayerConfig

# 记录 GUI 上次使用的配置文件路径，下次启动时默认载入。
GUI_STATE_PATH = SCRIPT_DIRECTORY / "nestpack_gui_state.json"

# 初次启动的默认层数。
DEFAULT_LAYER_COUNT = 3


def create_default_config() -> AppConfig:
    """返回初次启动时使用的默认配置模板：3 层压缩。"""
    layers = [
        LayerConfig(
            archive_name=f"layer_{number}.rar",
            password="",
            recovery_percent=None,
            auto_name=True,
        )
        for number in range(1, DEFAULT_LAYER_COUNT + 1)
    ]
    return AppConfig(
        winrar_path="auto",
        source_path="",
        output_directory="",
        overwrite_existing=False,
        confirm_before_start=False,
        show_winrar_gui=True,
        verify_after_compress=True,
        delete_inner_after_verify=True,
        layers=layers,
    )


def load_remembered_config_path(state_path: Path = GUI_STATE_PATH) -> Path | None:
    """读取上次使用的配置文件路径；文件不存在或已失效时返回 None。"""
    raw = _load_gui_state(state_path)
    path_text = raw.get("last_config")
    if not isinstance(path_text, str) or not path_text.strip():
        return None
    path = Path(path_text).resolve()
    return path if path.is_file() else None


def remember_config_path(
    path: Path, state_path: Path = GUI_STATE_PATH
) -> None:
    """把当前使用的配置文件路径写入 GUI 状态文件。"""
    state = _load_gui_state(state_path)
    state["last_config"] = str(path.resolve())
    _save_gui_state(state_path, state)


def is_blank_template(config_path: Path) -> bool:
    """判断现有配置是否为尚未填写源路径的默认模板。"""
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    return (
        not raw.get("source_paths") and not raw.get("source_path")
    ) and not raw.get("output_directory")


def _load_gui_state(state_path: Path) -> dict:
    """读取 GUI 状态文件全部字段；文件损坏时返回空 dict。"""
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _save_gui_state(state_path: Path, payload: dict) -> None:
    """原子写入 GUI 状态文件；写入失败时静默放弃。"""
    try:
        content = (
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )
        atomic_write_text(state_path, content)
    except OSError:
        pass


def load_recent_output_dirs(state_path: Path = GUI_STATE_PATH) -> list[str]:
    """返回最近使用过的输出目录列表（仍存在的目录，去重）。"""
    raw = _load_gui_state(state_path)
    items = raw.get("recent_output_dirs")
    if not isinstance(items, list):
        return []
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            continue
        path = Path(item)
        if not path.is_dir():
            continue
        key = str(path.resolve()).casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(str(path.resolve()))
    return result


def remember_output_dir(
    path: Path, state_path: Path = GUI_STATE_PATH, max_n: int = 8
) -> None:
    """把一条输出目录记入最近列表顶部；去重后截断保留最多 max_n 条。"""
    if not path.is_dir():
        return
    target = str(path.resolve())
    state = _load_gui_state(state_path)
    existing = load_recent_output_dirs(state_path)
    remaining = [p for p in existing if p.casefold() != target.casefold()]
    state["recent_output_dirs"] = [target, *remaining][:max_n]
    _save_gui_state(state_path, state)


def load_file_dialog_size(state_path: Path = GUI_STATE_PATH) -> tuple[int, int] | None:
    """读取用户调整后的文件选择框宽高，缺省或无效时返回 None。"""
    size = _load_gui_state(state_path).get("file_dialog_size")
    if (
        not isinstance(size, list) or len(size) != 2
        or any(type(value) is not int or value <= 0 for value in size)
    ):
        return None
    return size[0], size[1]


def remember_file_dialog_size(
    width: int, height: int, state_path: Path = GUI_STATE_PATH,
) -> None:
    """保存所有文件选择框共用的宽高，保留其他 GUI 状态。"""
    state = _load_gui_state(state_path)
    state["file_dialog_size"] = [width, height]
    _save_gui_state(state_path, state)
