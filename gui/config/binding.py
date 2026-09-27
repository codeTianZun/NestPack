"""通过面板接口收集配置快照，并把配置回填到编辑界面。"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from core.models import AppConfig
from gui.config.storage import create_default_config

if TYPE_CHECKING:
    from gui.views.layers_panel import LayersPanel
    from gui.views.settings_dialog import SettingsDialog
    from gui.views.source_panel import SourcePanel


class ConfigBinding(QObject):
    """组合来源、层级和设置面板的配置读写接口。"""

    changed = Signal()

    def __init__(
        self, source: SourcePanel, layers: LayersPanel, settings: SettingsDialog
    ) -> None:
        super().__init__()
        self._source = source
        self._layers = layers
        self._settings = settings
        for signal in (
            source.paths_changed, source.mode_changed, source.output_changed,
            layers.card_changed, layers.cards_changed, settings.changed,
        ):
            signal.connect(self.changed)

    def collect(self, *, strict: bool = True) -> AppConfig:
        """收集独立配置快照；执行时严格校验，保存草稿时允许未完成输入。"""
        config = self._source.collect(create_default_config(), strict=strict)
        config = self._settings.collect(config, strict=strict)
        return replace(config, layers=self._layers.collect(strict=strict))

    def apply(self, config: AppConfig) -> None:
        """回填全部编辑面板，自动保存的挂起由配置会话负责。"""
        self._source.apply(config)
        self._settings.apply(config)
        self._layers.set_cards(config.layers)
