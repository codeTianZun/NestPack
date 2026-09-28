"""数字向导与完整任务编辑器，菜单和 --init 共用。"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from cli.configuration import new_config, validate_config, write_task_config
from cli.prompts import (
    ask_archive_format,
    ask_archive_name,
    ask_layer_config,
    ask_menu,
    ask_output_directory,
    ask_password,
    ask_positive_integer,
    ask_source_paths,
    ask_yes_no,
)
from cli.sfx import edit_sfx
from core.backends import get_backend
from core.config import validate_disguise_extension, validate_password, validate_volume_size
from core.filesystem import normalize_user_path
from core.models import FORMAT_RAR, AppConfig, ConfigError, DisguiseConfig, LayerConfig
from platforms import get_archive_platform


def ask_config_path(default: Path) -> Path:
    """读取配置路径，空输入沿用当前路径。"""
    while True:
        value = input(f"配置文件路径（回车使用 {default}）：").strip()
        try:
            return normalize_user_path(value) if value else default
        except (ValueError, OSError, RuntimeError) as error:
            print(f"路径无效：{error}")


def print_task_settings(config: AppConfig) -> None:
    """在工具或来源尚不可用时也能展示和编辑任务。"""
    print("\n当前任务：")
    for source in config.effective_source_paths():
        print(f"  来源：{source}")
    print(f"  输出：{config.output_directory or '尚未设置'}")
    print(f"  打包：{'分别打包' if config.compress_mode == 'separate' else '合并打包'}")
    for index, layer in enumerate(config.layers, start=1):
        state = "已设置" if layer.password else "待补充" if layer.password_set else "无"
        print(
            f"  第 {index} 层：{layer.archive_name}（{layer.format}），密码：{state}，"
            f"级别：{layer.compression_level}，分卷：{layer.volume_size or '关闭'}"
        )
        if layer.disguise.mode == "extension":
            print(f"    伪装扩展名：{layer.disguise.extension}")
        elif layer.disguise.mode == "video":
            print(f"    视频伪装：默认 {layer.disguise.video_path or '尚未设置'}")
            for source, video in layer.disguise.source_video_paths.items():
                print(f"      {source} → {video}")
        if layer.sfx.enabled:
            print(f"    自解压：{layer.sfx.target}，模板：{layer.sfx.template_path}")


def _ask_mode() -> str:
    return (
        "separate"
        if ask_menu("打包方式", {1: "全部来源合并打包", 2: "每个来源分别打包"}, default=1) == 2
        else "combined"
    )


def _source_stem(config: AppConfig) -> str:
    sources = config.effective_source_paths()
    return Path(sources[0]).stem or "archive" if sources else "archive"


def create_config_interactively() -> AppConfig:
    """收集基础设置，再允许编辑所有高级选项。"""
    print("\n新建压缩任务。可随时按 Ctrl+C 取消。")
    sources = ask_source_paths("来源路径（多个文件或文件夹用分号 ; 分隔）：")
    config = new_config(sources)
    output = ask_output_directory(sources[0].parent / "archives")
    mode = _ask_mode()
    count = ask_positive_integer("嵌套层数（至少 1）：")
    layers: list[LayerConfig] = []
    names: set[str] = set()
    for number in range(1, count + 1):
        layer = ask_layer_config(number, _source_stem(config), names)
        layers.append(layer)
        names.add(layer.archive_name.casefold())
    config = replace(config, output_directory=str(output), compress_mode=mode, layers=layers)
    print("默认逐层自检并删除中间层，保留原始来源和最外层归档；高级设置可调整。")
    if ask_yes_no("是否设置分卷、压缩级别、隐私或其他高级选项"):
        config = edit_config(config)
    return config


def _ask_level(current: str | int) -> str | int:
    while True:
        raw = input(f"压缩级别 auto 或 0–5（回车保留 {current}）：").strip().lower()
        if not raw:
            return current
        if raw == "auto":
            return raw
        if raw in {"0", "1", "2", "3", "4", "5"}:
            return int(raw)
        print("请输入 auto 或 0–5，0 为仅存储，5 为最高压缩。")


def _ask_volume(current: str | None) -> str | None:
    while True:
        raw = input(f"分卷大小，如 100m（回车保留 {current or '关闭'}，- 关闭）：").strip()
        if not raw:
            return current
        if raw == "-":
            return None
        try:
            validate_volume_size(raw)
            return raw
        except ValueError as error:
            print(error)


def _edit_layer(
    layer: LayerConfig, index: int, forbidden: set[str], config: AppConfig,
) -> LayerConfig:
    while True:
        print(f"\n第 {index} 层：{layer.archive_name}（{layer.format}）")
        choice = ask_menu(
            "层设置",
            {
                1: "压缩格式",
                2: "文件名",
                3: "密码",
                4: f"压缩级别：{layer.compression_level}",
                5: f"分卷：{layer.volume_size or '关闭'}",
                6: f"恢复记录：{layer.recovery_percent or '关闭'}",
                7: f"分别打包的层名模板：{layer.name_template or '使用固定文件名'}",
                8: f"自解压：{layer.sfx.target if layer.sfx.enabled else '关闭'}",
                9: "伪装方式与载体视频",
                0: "返回",
            },
            default=0,
        )
        if choice == 0:
            return layer
        if choice == 1:
            archive_format = ask_archive_format(index)
            password = layer.password
            try:
                validate_password(password, archive_format)
            except ValueError as error:
                print(error)
                password = ask_password(index, archive_format)
            extension = get_backend(archive_format).archive_extension
            layer = replace(
                layer,
                format=archive_format,
                archive_name=Path(layer.archive_name).stem + extension,
                password=password,
                password_set=bool(password) or (layer.password_set and not layer.password),
                recovery_percent=layer.recovery_percent if archive_format == FORMAT_RAR else None,
            )
        elif choice == 2:
            name = ask_archive_name(
                index, layer.archive_name, forbidden, layer.format,
                sfx_extension=layer.sfx.extension if layer.sfx.enabled else None,
            )
            layer = replace(layer, archive_name=name, name_template=None)
        elif choice == 3:
            password = ask_password(index, layer.format)
            layer = replace(layer, password=password, password_set=bool(password))
        elif choice == 4:
            layer = replace(layer, compression_level=_ask_level(layer.compression_level))
        elif choice == 5:
            layer = replace(layer, volume_size=_ask_volume(layer.volume_size))
        elif choice == 6:
            if layer.format != FORMAT_RAR:
                print("恢复记录适用于 RAR；当前格式使用压缩后自检。")
            else:
                enabled = ask_yes_no("启用恢复记录", default=layer.recovery_percent is not None)
                percent = (
                    ask_positive_integer("恢复记录比例 1–100：", maximum=100) if enabled else None
                )
                layer = replace(layer, recovery_percent=percent)
        elif choice == 7:
            raw = input("层名模板，例如 {stem}_1（回车保留，- 使用固定文件名）：").strip()
            if raw:
                layer = replace(layer, name_template=None if raw == "-" else raw)
        elif choice == 8:
            sfx = edit_sfx(layer.sfx)
            extension = (
                sfx.extension if sfx.enabled else get_backend(layer.format).archive_extension
            )
            layer = replace(layer, sfx=sfx, archive_name=Path(layer.archive_name).stem + extension)
        elif choice == 9:
            layer = replace(layer, disguise=_edit_disguise(layer.disguise, config))


def _select_layer(layers: list[LayerConfig]) -> int:
    return ask_menu("选择压缩层", {i: layer.archive_name for i, layer in enumerate(layers, 1)}) - 1


def _edit_layers(config: AppConfig) -> AppConfig:
    layers = list(config.layers)
    while True:
        for index, layer in enumerate(layers, start=1):
            print(f"  {index}. {layer.archive_name}（{layer.format}）")
        choice = ask_menu(
            "层列表（从内到外）",
            {
                1: "添加外层",
                2: "编辑一层",
                3: "删除一层",
                4: "移动一层",
                0: "返回",
            },
            default=0,
        )
        if choice == 0:
            return replace(config, layers=layers)
        if choice == 1:
            layers.append(
                ask_layer_config(
                    len(layers) + 1,
                    _source_stem(config),
                    {layer.archive_name.casefold() for layer in layers},
                )
            )
        elif choice == 2:
            index = _select_layer(layers)
            forbidden = {
                item.archive_name.casefold() for i, item in enumerate(layers) if i != index
            }
            layers[index] = _edit_layer(layers[index], index + 1, forbidden, config)
        elif choice == 3:
            if len(layers) == 1:
                print("任务至少需要保留一层。")
            else:
                del layers[_select_layer(layers)]
        elif choice == 4:
            index = _select_layer(layers)
            position = ask_positive_integer(
                f"移动到第几层（1–{len(layers)}）：", maximum=len(layers)
            )
            layers.insert(position - 1, layers.pop(index))


ARCHIVE_SETTINGS = {
    "overwrite_existing": "覆盖已有归档",
    "verify_after_compress": "每层压缩后自检",
    "delete_inner_after_verify": "自检后删除中间层",
    "cleanup_on_failure": "失败时清理本任务产物",
    "persist_passwords": "保存配置时保留明文密码",
    "confirm_before_start": "参数调用时运行前确认",
}
PRIVACY_SETTINGS = {
    "add_padding": "添加随机填充",
    "randomize_layer_names": "随机层名",
    "hide_source_name": "来源根名称使用随机别名",
    "randomize_timestamps": "随机化最外层修改时间",
}


def _edit_switches(
    config: AppConfig, labels: dict[str, str]
) -> AppConfig:
    fields = list(labels)
    while True:
        options = {
            i: f"{labels[field]}：{'开启' if getattr(config, field) else '关闭'}"
            for i, field in enumerate(fields, start=1)
        }
        options[0] = "返回"
        choice = ask_menu("选择要修改的设置", options, default=0)
        if choice == 0:
            return config
        field = fields[choice - 1]
        enabled = not getattr(config, field)
        updates: dict[str, Any] = {field: enabled}
        if field == "delete_inner_after_verify" and enabled:
            updates["verify_after_compress"] = True
            print("已同时开启自检。")
        if field == "verify_after_compress" and not enabled:
            updates["delete_inner_after_verify"] = False
            print("关闭自检后保留中间层。")
        config = replace(config, **updates)


def _edit_tools(config: AppConfig) -> AppConfig:
    while True:
        options = {1: f"RAR：{config.winrar_path}", 2: f"7-Zip：{config.sevenzip_path}", 0: "返回"}
        if sys.platform == "win32":
            options[3] = f"显示 WinRAR 界面：{'是' if config.show_winrar_gui else '否'}"
        choice = ask_menu("工具设置", options, default=0)
        if choice == 0:
            return config
        if choice == 3:
            config = replace(config, show_winrar_gui=not config.show_winrar_gui)
            continue
        raw = input("工具路径或 auto（回车保留）：").strip()
        if not raw:
            continue
        field, kind = ("winrar_path", "rar") if choice == 1 else ("sevenzip_path", "7z")
        try:
            value = (
                "auto"
                if raw.lower() == "auto"
                else str(get_archive_platform().resolve_tool(raw, Path.cwd(), kind=kind))
            )
            updates: dict[str, Any] = {field: value}
            config = replace(config, **updates)
        except (ConfigError, OSError, ValueError) as error:
            print(f"工具路径无效：{error}")


def edit_config(config: AppConfig) -> AppConfig:
    """所有任务设置的数字编辑入口，支持修正失效路径。"""
    while True:
        print_task_settings(config)
        choice = ask_menu(
            "编辑任务",
            {
                1: "来源文件 / 文件夹",
                2: "输出目录",
                3: "打包方式",
                4: "压缩层",
                5: "归档与保存选项",
                6: "隐私选项",
                7: "工具路径与界面",
                0: "完成编辑",
            },
            default=0,
        )
        if choice == 0:
            return config
        if choice == 1:
            sources = ask_source_paths("来源路径（多个用分号 ; 分隔）：")
            config = replace(
                config, source_path=str(sources[0]), source_paths=[str(path) for path in sources]
            )
        elif choice == 2:
            default = (
                normalize_user_path(config.output_directory)
                if config.output_directory
                else Path.cwd() / "archives"
            )
            config = replace(config, output_directory=str(ask_output_directory(default)))
        elif choice == 3:
            config = replace(config, compress_mode=_ask_mode())
        elif choice == 4:
            config = _edit_layers(config)
        elif choice == 5:
            config = _edit_switches(config, ARCHIVE_SETTINGS)
        elif choice == 6:
            config = _edit_switches(config, PRIVACY_SETTINGS)
        elif choice == 7:
            config = _edit_tools(config)


def _edit_disguise(disguise: DisguiseConfig, config: AppConfig) -> DisguiseConfig:
    """编辑本层的扩展名或视频；分别打包时可逐来源覆盖载体。"""
    modes = ("none", "extension", "video")
    choice = ask_menu(
        "本层伪装", {1: "原扩展名", 2: "修改扩展名", 3: "视频伪装（MP4）"},
        default=modes.index(disguise.mode) + 1,
    )
    disguise = replace(disguise, mode=modes[choice - 1])
    if disguise.mode == "extension":
        while True:
            raw = input(f"伪装扩展名（回车保留 {disguise.extension}）：").strip()
            try:
                validate_disguise_extension(raw or disguise.extension)
                return replace(disguise, extension=raw or disguise.extension)
            except ValueError as error:
                print(error)
    if disguise.mode != "video":
        return disguise
    print("视频伪装使用本层完整单文件归档；分卷和自解压可设置在其他层。")
    raw = input(f"本层默认 MP4 视频（回车保留 {disguise.video_path or '空'}）：").strip()
    video = str(normalize_user_path(raw)) if raw else disguise.video_path
    overrides = dict(disguise.source_video_paths)
    if config.compress_mode == "separate" and ask_yes_no("是否按来源分别指定视频"):
        for source in config.effective_source_paths():
            current = overrides.get(source, "使用默认视频")
            raw = input(f"{source} 的 MP4（回车保留 {current}，- 使用默认）：").strip()
            if raw == "-":
                overrides.pop(source, None)
            elif raw:
                overrides[source] = str(normalize_user_path(raw))
    return replace(disguise, video_path=video, source_video_paths=overrides)


def initialize_config(
    config_path: Path, force_request: bool, assume_yes: bool = False
) -> AppConfig | None:
    """交互创建并保存配置；已有文件在创建前确认替换。"""
    if config_path.exists() and force_request and not assume_yes:
        if not ask_yes_no(f"是否重新创建配置：{config_path}"):
            return None
    config = create_config_interactively()
    while True:
        try:
            config = validate_config(config)
            write_task_config(config_path, config, None)
            print(f"配置已保存：{config_path}")
            return config
        except (ConfigError, OSError) as error:
            print(f"配置尚无法保存：{error}")
            config = edit_config(config)
