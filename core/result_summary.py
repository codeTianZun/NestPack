"""从压缩计划与结果生成完成摘要、密码清单与机器可读 manifest。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.compression import CompressionPlan, CompressionResult
from core.models import COMPRESS_MODE_SEPARATE

MANIFEST_SCHEMA_VERSION = 1


def describe_layer_files(files: tuple[Path, ...]) -> str:
    """弹窗里描述一层生成的文件：单文件直书，分卷显示数量。"""
    if len(files) == 1:
        return files[0].name
    return f"{files[0].name} 等 {len(files)} 个分卷"


@dataclass(frozen=True)
class SuccessReport:
    """压缩完成弹窗的文案。"""

    headline: str
    detail_lines: list[str]
    final_archive_text: str
    warning: str


def build_success_report(result: CompressionResult) -> SuccessReport:
    """从每个任务的实际层产物生成弹窗文案。"""
    config = result.plan.config
    if config.compress_mode == COMPRESS_MODE_SEPARATE:
        if config.delete_inner_after_verify:
            headline = f"已打包 {len(result.tasks)} 个来源，中间层已删除，仅保留最外层！\n\n"
        else:
            headline = f"已打包 {len(result.tasks)} 个来源，全部打好啦！\n\n"
    else:
        if config.delete_inner_after_verify:
            headline = "已打包完成，中间层已删除，仅保留最外层！\n\n"
        else:
            headline = "已打包完成，全部打好啦！\n\n"

    detail_lines: list[str] = []
    multiple = len(result.tasks) > 1
    for task in result.tasks:
        if multiple:
            detail_lines.append(f"来源：{task.plan.sources[0].name}")
        for index, layer in enumerate(task.layers, start=1):
            names = describe_layer_files(layer.files)
            password = layer.plan.config.password
            password_text = f"密码：{password}" if password else "无密码"
            detail_lines.append(f"  第 {index} 层：{names}（{password_text}）")
        if multiple:
            detail_lines.append("")

    warning = ""
    if not config.persist_passwords:
        warning = "\n\n注意：配置未保存密码，关闭本窗口后请立即复制并妥善保存密码清单！"
    return SuccessReport(
        headline=headline,
        detail_lines=detail_lines,
        final_archive_text="\n".join(str(path) for path in result.final_files),
        warning=warning,
    )


def build_password_clipboard(result: CompressionResult) -> str:
    """生成可发给接收方的明文清单（文件名 + 密码 + 最外层路径）。"""
    lines = ["NestPack 打包清单"]
    multiple = len(result.tasks) > 1
    for task in result.tasks:
        if multiple:
            lines.append(f"来源：{task.plan.sources[0].name}")
        for index, layer in enumerate(task.layers, start=1):
            names = "、".join(path.name for path in layer.files)
            password_text = layer.plan.config.password or "（无密码）"
            lines.append(f"第 {index} 层：{names} 密码：{password_text}")
        if multiple:
            lines.append("")
    lines.append("最外层文件：")
    lines.extend(str(path) for path in result.final_files)
    lines.append("解包方法：把最外层文件交给 NestPack 解包，或逐层用密码解压。")
    return "\n".join(lines)


def build_manifest(
    result: CompressionResult,
    *,
    include_passwords: bool = True,
) -> dict[str, Any]:
    """序列化压缩结果，保持 --json 清单字段；可选择清空密码字段。"""
    config = result.plan.config
    manifest_groups: list[dict[str, Any]] = []
    for task in result.tasks:
        layers_json = []
        for layer in task.layers:
            settings = layer.plan.config
            layers_json.append(
                {
                    "name": layer.files[0].name,
                    "format": settings.format,
                    "files": [str(path) for path in layer.files],
                    "password": settings.password if include_passwords else "",
                    "recovery_percent": settings.recovery_percent,
                    "volume_size": settings.volume_size,
                }
            )
        manifest_groups.append(
            {
                "source": str(task.plan.sources[0]) if len(result.tasks) > 1 else "",
                "layers": layers_json,
                "final": [str(path) for path in task.final_files],
            }
        )
    return {
        "tool": "nestpack",
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "status": "ok",
        "mode": "compress",
        "compress_mode": config.compress_mode,
        "delete_inner_after_verify": config.delete_inner_after_verify,
        "warnings": list(result.plan.warnings),
        "groups": manifest_groups,
    }


def build_plan_manifest(plan: CompressionPlan) -> dict[str, Any]:
    """序列化执行计划，分卷以首卷路径预览，密码仅输出设置标记。

    随机层名在 dry-run 时由调用方保持未应用，manifest 中保留该配置标记。
    """
    config = plan.config
    manifest_groups: list[dict[str, Any]] = []
    for task in plan.tasks:
        layers_json = []
        for layer in task.layers:
            files = layer.output_paths()
            settings = layer.config
            layers_json.append(
                {
                    "name": files[0].name,
                    "format": settings.format,
                    "expected_files": [str(path) for path in files],
                    "password_set": bool(settings.password) or settings.password_set,
                    "recovery_percent": settings.recovery_percent,
                    "compression_level": settings.compression_level,
                    "volume_size": settings.volume_size,
                }
            )
        manifest_groups.append(
            {
                "source": str(task.sources[0]) if len(plan.tasks) > 1 else "",
                "layers": layers_json,
                "final": [str(path) for path in task.layers[-1].output_paths()],
            }
        )
    return {
        "tool": "nestpack",
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "status": "plan",
        "mode": "compress",
        "compress_mode": config.compress_mode,
        "config_path": str(plan.config_path) if plan.config_path is not None else None,
        "sources": [str(source) for source in plan.sources],
        "output_directory": str(plan.output_directory),
        "winrar": str(plan.winrar) if plan.winrar else None,
        "sevenzip": str(plan.sevenzip) if plan.sevenzip else None,
        "overwrite_existing": config.overwrite_existing,
        "delete_inner_after_verify": config.delete_inner_after_verify,
        "disguise_outer_extension": config.disguise_outer_extension,
        "randomize_layer_names": config.randomize_layer_names,
        "warnings": list(plan.warnings),
        "groups": manifest_groups,
    }
