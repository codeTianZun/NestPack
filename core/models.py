"""配置模型与共享常量。"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

if getattr(sys, "frozen", False):
    # PyInstaller 打包后 __file__ 指向临时解包目录，改用 exe 所在目录，
    # 保证默认配置与 GUI 状态文件落在 exe 旁边（便携分发）。
    SCRIPT_DIRECTORY = Path(sys.executable).resolve().parent
else:
    # 源码运行时以项目根目录为默认配置位置。
    SCRIPT_DIRECTORY = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = SCRIPT_DIRECTORY / "nestpack_config.json"
CONFIG_VERSION = 1
# 工具版本号：CLI --version 输出与问题排查时对齐版本用。
APP_VERSION = "1.0.0"

# 压缩级别：auto 首层采样、后续层仅存储；整数 0-5 由各格式后端映射为工具参数。
COMPRESSION_AUTO = "auto"
COMPRESSION_LEVEL_MIN = 0
COMPRESSION_LEVEL_MAX = 5

# 多来源打包方式：combined 全部一起压缩成一个压缩包；
# separate 每个来源分别压缩成各自的压缩包（输出目录下按来源分目录）。
COMPRESS_MODE_COMBINED = "combined"
COMPRESS_MODE_SEPARATE = "separate"

# 受支持的压缩格式；逐层独立选择，可混合嵌套（RAR 套 7z 等）。
# zip 由 7-Zip 工具创建（-tzip），与 7z 共用同一命令行程序。
FORMAT_RAR = "rar"
FORMAT_7Z = "7z"
FORMAT_ZIP = "zip"


class ConfigError(ValueError):
    """表示 JSON 配置内容缺失、类型错误或取值无效。"""


@dataclass(frozen=True)
class LayerConfig:
    """单层压缩参数；None 表示不创建恢复记录。"""

    archive_name: str
    password: str
    recovery_percent: int | None
    compression_level: str | int = COMPRESSION_AUTO
    # 默认层名的来源模板：形如 "{stem}_1"，separate 模式运行时按各来源替换。
    # 用户自定义过文件名时该字段为 None，运行时不替换，保留原名。
    name_template: str | None = None
    # 分卷大小（如 "500m"）；None 表示不分卷。
    volume_size: str | None = None
    # 该层是否本应设置密码。persist_passwords=false 时密码不落盘，
    # 该标记随配置保存，命令行运行前据此交互补问缺失的密码。
    password_set: bool = False
    # 压缩格式："rar" / "7z" / "zip"；缺省 rar。
    format: str = FORMAT_RAR

    def to_json_dict(self) -> dict[str, Any]:
        """转换成适合 GUI 编辑和 JSON 保存的显式结构。"""
        return {
            "archive_name": self.archive_name,
            "format": self.format,
            "password": self.password,
            "recovery_record": {
                "enabled": self.recovery_percent is not None,
                "percent": self.recovery_percent or 3,
            },
            "compression_level": self.compression_level,
            "name_template": self.name_template,
            "volume_size": self.volume_size,
            "password_set": self.password_set or bool(self.password),
        }


@dataclass(frozen=True)
class AppConfig:
    """整个压缩任务的可持久化配置。"""

    winrar_path: str
    source_path: str
    output_directory: str
    overwrite_existing: bool
    confirm_before_start: bool
    show_winrar_gui: bool
    layers: list[LayerConfig]
    add_padding: bool = False
    randomize_layer_names: bool = False
    hide_source_name: bool = False
    disguise_outer_extension: bool = False
    verify_after_compress: bool = True
    cleanup_on_failure: bool = False
    persist_passwords: bool = True
    delete_inner_after_verify: bool = True
    # 多来源：source_paths 为空时回退到 source_path（旧配置兼容）。
    # compress_mode 决定多个来源是一起打包还是一个来源一套压缩包。
    source_paths: list[str] = field(default_factory=list)
    compress_mode: str = COMPRESS_MODE_COMBINED
    # 伪装用的扩展名（以点开头，如 ".bin"）；disguise_outer_extension 开启时生效。
    disguise_extension: str = ".bin"
    # 完成后把最外层文件的修改时间改为随机值，避免时间戳成为关联特征。
    randomize_timestamps: bool = False
    # 7-Zip 命令行工具路径，语义同 winrar_path（auto 表示自动检测）；
    # 只在配置里存在 7z 或 zip 层时解析。
    sevenzip_path: str = "auto"

    def effective_source_paths(self) -> list[str]:
        """返回实际生效的来源列表，兼容只填了 source_path 的旧配置。"""
        return self.source_paths or ([self.source_path] if self.source_path else [])

    def to_json_dict(self) -> dict[str, Any]:
        """生成供配置文件和 GUI 使用的 JSON 字段。"""
        return {
            "config_version": CONFIG_VERSION,
            "winrar_path": self.winrar_path,
            "sevenzip_path": self.sevenzip_path,
            "source_path": self.source_path,
            "source_paths": list(self.source_paths),
            "compress_mode": self.compress_mode,
            "output_directory": self.output_directory,
            "overwrite_existing": self.overwrite_existing,
            "confirm_before_start": self.confirm_before_start,
            "show_winrar_gui": self.show_winrar_gui,
            "layers": [layer.to_json_dict() for layer in self.layers],
            "add_padding": self.add_padding,
            "randomize_layer_names": self.randomize_layer_names,
            "hide_source_name": self.hide_source_name,
            "disguise_outer_extension": self.disguise_outer_extension,
            "disguise_extension": self.disguise_extension,
            "randomize_timestamps": self.randomize_timestamps,
            "verify_after_compress": self.verify_after_compress,
            "cleanup_on_failure": self.cleanup_on_failure,
            "persist_passwords": self.persist_passwords,
            "delete_inner_after_verify": self.delete_inner_after_verify,
        }

    def without_passwords(self) -> AppConfig:
        """返回密码全部清空的副本（persist_passwords=false 时用于落盘）。

        password_set 标记保留，命令行加载这类配置时可以交互补问。
        """
        return replace(
            self,
            layers=[
                replace(
                    layer,
                    password="",
                    password_set=layer.password_set or bool(layer.password),
                )
                for layer in self.layers
            ],
        )
