"""自解压模板解析、资源规划与 Windows SFX 脚本生成。"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass
from pathlib import Path

from core.config.sfx import validate_sfx_config
from core.filesystem import normalize_user_path
from core.models import ConfigError, SfxConfig
from core.rar_content import MAX_SFX_SIZE, rar_signature_offset
from platforms.tools import tool_directory_candidates


@dataclass(frozen=True)
class SfxPlan:
    """经过校验的品牌模块快照及本机可用的图片资源。"""

    template: Path
    module: bytes
    icon: Path | None = None
    logo: Path | None = None

    @property
    def resources(self) -> tuple[Path, ...]:
        """归档发布需要保护的原始模板与素材。"""
        return tuple(path for path in (self.template, self.icon, self.logo) if path is not None)


def _read_module(path: Path, target: str) -> bytes:
    """从原生模块或已有品牌样包中读取归档前的可执行部分。"""
    if not path.is_file():
        raise ConfigError(f"自解压模板不存在或不是文件：{path}")
    offset = rar_signature_offset(path)
    size = offset if offset is not None else path.stat().st_size
    if not 0 < size <= MAX_SFX_SIZE:
        raise ConfigError(f"自解压模板的可执行模块应在 1 MiB 以内：{path}")
    with path.open("rb") as stream:
        module = stream.read(size)
    if target == "windows":
        if len(module) < 64 or not module.startswith(b"MZ"):
            raise ConfigError(f"Windows 目标需要 Windows GUI 自解压模板：{path}")
        pe_offset = struct.unpack_from("<I", module, 60)[0]
        if (pe_offset + 94 > len(module)
                or module[pe_offset:pe_offset + 4] != b"PE\0\0"
                or struct.unpack_from("<H", module, pe_offset + 92)[0] != 2):
            raise ConfigError(f"所选文件不是 Windows GUI 自解压模块：{path}")
    elif len(module) < 20 or not module.startswith(b"\x7fELF"):
        raise ConfigError(f"Linux 目标需要 ELF 自解压模板：{path}")
    return module


def resolve_sfx(settings: SfxConfig, tool: Path, base: Path) -> SfxPlan:
    """根据交付目标查找模板，制作端仅决定本机工具和资源修改能力。"""
    validate_sfx_config(settings)
    raw = settings.template_path.strip()
    if raw.casefold() == "auto":
        name = "Default.SFX" if settings.target == "windows" else "default.sfx"
        directories = [tool.parent, *tool_directory_candidates("rar")]
        if settings.target == "linux":
            directories.extend((Path.home(), Path("/usr/local/lib"), Path("/usr/lib")))
        template = next((directory / name for directory in directories
                         if (directory / name).is_file()), None)
        if template is None:
            raise ConfigError(
                f"未找到 {settings.target} 自解压模板；请在 sfx.template_path 指定品牌样包"
                f"或官方 {name} 模块的路径"
            )
    else:
        template = normalize_user_path(raw, base)
    module = _read_module(template, settings.target)
    if settings.icon_path or settings.logo_path:
        if sys.platform != "win32" or tool.name.casefold() != "winrar.exe":
            raise ConfigError(
                "修改自解压图标和 Logo 需要 Windows WinRAR.exe；"
                "请在 Windows 制作品牌样包，再由服务器通过 sfx.template_path 复用"
            )
    resources: list[Path | None] = []
    for label, value, signatures in (
        ("图标", settings.icon_path, (b"\0\0\x01\0",)),
        ("Logo", settings.logo_path, (b"\x89PNG\r\n\x1a\n", b"BM")),
    ):
        path = normalize_user_path(value, base) if value else None
        if path is not None:
            if not path.is_file():
                raise ConfigError(f"自解压{label}文件不存在：{path}")
            with path.open("rb") as stream:
                if not stream.read(8).startswith(signatures):
                    raise ConfigError(f"自解压{label}格式无效，请使用 ICO 图标或 PNG / BMP Logo")
        resources.append(path)
    return SfxPlan(template.resolve(), module, *resources)


def sfx_script(settings: SfxConfig) -> str:
    """由本次配置生成 Windows GUI SFX 注释脚本。"""
    lines = [";NestPack 自解压设置"]
    for key, value in (("Title", settings.title), ("Path", settings.extract_path),
                       ("Setup", settings.setup)):
        if value:
            lines.append(f"{key}={value}")
    if settings.text:
        lines.extend(("Text", "{", settings.text.replace("\r\n", "\n").replace("\r", "\n"), "}"))
    lines.append("Overwrite=" + {"ask": "0", "overwrite": "1", "skip": "2"}[settings.overwrite])
    lines.append("Silent=" + {"show": "0", "hide_all": "1", "hide_start": "2"}[settings.silent])
    return "\r\n".join(lines) + "\r\n"


def prepare_sfx_options(plan: SfxPlan, settings: SfxConfig, work: Path) -> list[str]:
    """在本层工作目录写入模块与脚本，返回归档工具的附加开关。"""
    module = work / "module.sfx"
    module.write_bytes(plan.module)
    options = [f"-sfx{module}"]
    if settings.target == "windows":
        comment = work / "sfx-comment.txt"
        comment.write_text(sfx_script(settings), encoding="utf-16", newline="")
        options.extend(("-scuc", f"-z{comment}"))
    if plan.icon is not None:
        options.append(f"-iicon{plan.icon}")
    if plan.logo is not None:
        options.append(f"-iimg{plan.logo}")
    return options
