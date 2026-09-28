"""终端自解压设置编辑器。"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from cli.configuration import read_utf8_text
from cli.prompts import ask_menu, ask_yes_no
from core.filesystem import normalize_user_path
from core.models import SfxConfig


def edit_sfx(settings: SfxConfig) -> SfxConfig:
    """编辑全部自解压字段，保留用户尚未解决的配置冲突。"""
    fields = {
        3: ("template_path", "品牌样包 / 模块路径，auto 自动查找"),
        4: ("icon_path", "Windows 制作端 ICO 图标路径"),
        5: ("logo_path", "Windows 制作端 PNG / BMP Logo 路径"),
        6: ("title", "Windows 自解压标题"),
        7: ("text", "Windows 自解压说明文字"),
        8: ("extract_path", "接收者默认解压路径"),
        9: ("setup", "成功解压后运行的 Windows 命令"),
    }
    while True:
        choice = ask_menu("自解压设置（交付目标独立于制作系统）", {
            1: f"启用：{'是' if settings.enabled else '否'}",
            2: f"交付目标：{settings.target}",
            **{number: f"{label}：{getattr(settings, key) or '留空'}"
               for number, (key, label) in fields.items()},
            10: f"接收者覆盖策略：{settings.overwrite}",
            11: f"接收者界面显示：{settings.silent}",
            12: "从 UTF-8 文件读取说明文字",
            0: "返回层设置",
        }, default=0)
        if choice == 0:
            return settings
        if choice == 1:
            settings = replace(settings, enabled=ask_yes_no("启用自解压", settings.enabled))
        elif choice == 2:
            selected = ask_menu("接收者系统", {1: "Windows 图形自解压", 2: "Linux 终端自解压"})
            settings = replace(settings, target="windows" if selected == 1 else "linux")
        elif choice in fields:
            key, label = fields[choice]
            raw = input(f"{label}（回车保留，- 清空）：")
            if raw:
                changes: dict[str, Any] = {key: "" if raw == "-" else raw}
                settings = replace(settings, **changes)
        elif choice == 10:
            selected = ask_menu("覆盖策略", {1: "询问", 2: "覆盖", 3: "跳过"})
            settings = replace(settings, overwrite=("ask", "overwrite", "skip")[selected - 1])
        elif choice == 11:
            selected = ask_menu("显示方式", {1: "正常显示", 2: "隐藏起始窗口", 3: "全部隐藏"})
            settings = replace(settings, silent=("show", "hide_start", "hide_all")[selected - 1])
        elif choice == 12:
            path = input("UTF-8 说明文件路径（回车取消）：").strip()
            if path:
                text = read_utf8_text(normalize_user_path(path), "说明文件")
                settings = replace(settings, text=text)
