"""通过面板接口收集配置快照，并把配置回填到编辑界面。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from core.models import COMPRESS_MODE_SEPARATE, AppConfig
from gui.config.storage import create_default_config

if TYPE_CHECKING:
    from gui.views.config_bar import ConfigBar
    from gui.views.layers_panel import LayersPanel
    from gui.views.output_panel import OutputPanel
    from gui.views.settings_dialog import SettingsDialog
    from gui.views.source_panel import SourcePanel
    from gui.views.task_options import TaskOptionsPanel


class ConfigBinding(QObject):
    """组合来源、层级、输出、任务选项和运行环境的配置读写接口。"""

    changed = Signal()

    def __init__(
        self, source: SourcePanel, layers: LayersPanel, output: OutputPanel,
        options: TaskOptionsPanel, settings: SettingsDialog, config_bar: ConfigBar,
    ) -> None:
        super().__init__()
        self._source = source
        self._layers = layers
        self._settings = settings
        self._output = output
        self._options = options
        self._config_bar = config_bar
        for signal in (
            source.paths_changed, source.mode_changed, output.changed,
            layers.card_changed, layers.cards_changed, options.changed,
            settings.changed, config_bar.changed,
        ):
            signal.connect(self.changed)

    def collect(self, *, strict: bool = True) -> AppConfig:
        """收集独立配置快照；执行时严格校验，保存草稿时允许未完成输入。"""
        config = self._source.collect(create_default_config(), strict=strict)
        config = self._output.collect(config, strict=strict)
        config = self._options.collect(config)
        config = self._settings.collect(config, strict=strict)
        config = self._config_bar.collect(config)
        return self._layers.collect_config(config, strict=strict)

    def apply(self, config: AppConfig) -> None:
        """回填全部编辑面板，自动保存的挂起由配置会话负责。"""
        self._source.apply(config)
        self._output.apply(config)
        self._options.apply(config)
        self._settings.apply(config)
        self._config_bar.apply(config)
        self._layers.set_sources(
            self._source.paths(), config.compress_mode == COMPRESS_MODE_SEPARATE,
            self._source.selected_path(),
        )
        self._layers.apply(config)
