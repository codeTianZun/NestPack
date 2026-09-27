"""菜单与参数入口共用的压缩预览、确认、保存和执行。"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from cli.configuration import validate_config, write_task_config
from cli.display import print_compression_progress, print_config_summary, print_json
from cli.prompts import (
    ask_yes_no,
    prompt_missing_passwords,
    require_interactive_for_missing_passwords,
    stdin_is_interactive,
)
from core.cancellation import CancelledError
from core.compression import build_compression_plan, run_compression
from core.config import randomized_layer_names
from core.models import AppConfig, ConfigError
from core.result_summary import build_manifest, build_plan_manifest


@dataclass(frozen=True)
class CompressionOptions:
    """本次 CLI 调用的展示、交互与保存方式。"""

    json_mode: bool = False
    dry_run: bool = False
    assume_yes: bool = False
    non_interactive: bool = False
    save_path: Path | None = None
    confirm: bool = False


def run_compress(config: AppConfig, config_path: Path | None, options: CompressionOptions) -> int:
    """执行完整任务；预览只读，确认完成后才保存配置并创建产物。"""
    stream = sys.stderr if options.json_mode or options.dry_run else sys.stdout
    if not options.dry_run:
        missing = any(layer.password_set and not layer.password for layer in config.layers)
        if missing and options.non_interactive:
            raise ConfigError(
                "配置有待补充的层密码；无交互模式请提供完整密码或使用 --layer-password-file"
            )
        require_interactive_for_missing_passwords(config)
        config = prompt_missing_passwords(config, output_stream=stream)
    config = validate_config(config)
    if config.randomize_layer_names and not options.dry_run:
        config = randomized_layer_names(config)
    plan = build_compression_plan(config, config_path)
    if options.dry_run:
        print_json(build_plan_manifest(plan))
        if not options.json_mode:
            from contextlib import redirect_stdout

            with redirect_stdout(sys.stderr):
                print_config_summary(plan)
                for warning in plan.warnings:
                    print(f"注意：{warning}")
                if config.randomize_layer_names:
                    print("实际运行时会生成新的随机层名。")
        return 0
    if not options.json_mode:
        print_config_summary(plan)
    for warning in plan.warnings:
        print(f"注意：{warning}", file=stream)
    if (config.confirm_before_start or options.confirm) and not options.assume_yes:
        if options.non_interactive or not stdin_is_interactive():
            raise ConfigError("任务需要运行前确认；请添加 --yes，或在交互菜单中运行")
        if not ask_yes_no("确认开始", default=True, output_stream=stream):
            raise CancelledError("已取消任务。")
    if options.save_path is not None:
        if options.save_path in (
            path for task in plan.tasks for layer in task.layers for path in layer.output_paths()
        ):
            raise ConfigError("配置保存路径与归档产物冲突，请选择其他配置文件名")
        if (
            options.save_path.exists()
            and options.save_path != config_path
            and not options.assume_yes
        ):
            if options.non_interactive or not stdin_is_interactive():
                raise ConfigError(
                    "要保存的配置文件已存在；添加 --yes 确认替换配置，或选择其他保存路径"
                )
            if not ask_yes_no(f"是否替换配置文件：{options.save_path}", output_stream=stream):
                raise CancelledError("已取消保存和运行。")
        write_task_config(options.save_path, config, config_path)
    result = run_compression(
        plan,
        output_cb=(lambda line: print(line, file=sys.stderr)) if options.json_mode else None,
        progress_cb=None if options.json_mode else print_compression_progress,
    )
    if options.json_mode:
        print_json(build_manifest(result))
    else:
        print("\n打包完成，交付文件：")
        for path in result.final_files:
            print(f"  {path}")
        if config.delete_inner_after_verify and len(config.layers) > 1:
            print("中间层已按设置删除；原始来源保留。")
    return 0
