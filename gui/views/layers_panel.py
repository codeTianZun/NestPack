"""压缩层级面板：卡片集合、配置读写、名称联动与概览统计。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import FluentIcon, PushButton

from core.filesystem import normalize_user_path
from core.models import AppConfig, LayerConfig
from gui.appearance.theme import SPACE_SM, SPACE_XS
from gui.config.layers import LayerDrafts
from gui.views.dialogs import show_info
from gui.views.layer_card import LayerCard
from gui.views.widgets import SectionCard


class LayersPanel(SectionCard):
    """「压缩层级」卡片：列表顺序即执行顺序，第一层在最里面。"""

    #: 用户点击「＋ 添加一层」。
    add_requested = Signal()
    #: 任一层级卡片的字段被编辑。
    card_changed = Signal()
    #: 卡片集合结构变化（新增/删除/移动后的重编号完成）。
    cards_changed = Signal()
    selection_changed = Signal()
    view_changed = Signal()
    defaults_requested = Signal()

    def __init__(self) -> None:
        super().__init__(
            "压缩层", "从内到外，逐层包裹。选择一层，在右侧编辑。",
        )
        self.cards: list[LayerCard] = []
        self.editors = QStackedWidget()
        self._selected: LayerCard | None = None
        self._editable = True
        self._sources: list[str] = []
        self._separate = False
        self._random_names = False
        self._config_dir = Path.cwd()
        self._drafts = LayerDrafts()
        self._source: Path | None = None
        self._rendering = False

        self.scope_label = QLabel()
        self.scope_label.setTextFormat(Qt.TextFormat.PlainText)
        self.scope_label.setWordWrap(True)
        self.scope_label.setObjectName("fieldLabel")
        self.body_layout.addWidget(self.scope_label)
        self.scope_actions = QWidget()
        scope_row = QHBoxLayout(self.scope_actions)
        scope_row.setContentsMargins(0, 0, 0, 0)
        self.defaults_button = PushButton("编辑默认层设置")
        self.defaults_button.clicked.connect(self.defaults_requested.emit)
        self.reset_button = PushButton("恢复共用默认")
        self.reset_button.clicked.connect(self._reset_source)
        scope_row.addWidget(self.defaults_button)
        scope_row.addWidget(self.reset_button)
        scope_row.addStretch(1)
        self.body_layout.addWidget(self.scope_actions)

        self.add_button = PushButton("添加一层", None, FluentIcon.ADD)
        self.add_button.clicked.connect(self.add_requested.emit)
        self.actions.addWidget(self.add_button)

        self.layer_container = QWidget()
        self.layers_layout = QVBoxLayout(self.layer_container)
        self.layers_layout.setContentsMargins(0, 0, SPACE_XS, 0)
        self.layers_layout.setSpacing(SPACE_SM)
        self.layers_layout.addStretch(1)
        self.body_layout.addWidget(self.layer_container)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def add_card(self, layer: LayerConfig | None = None, default_stem: str = "layer") -> None:
        """追加一张层级卡片；未给定配置时按来源名与序号生成默认名称。"""
        number = len(self.cards) + 1
        value = layer or LayerConfig(
            archive_name=f"{default_stem}_{number}.rar",
            password="",
            recovery_percent=None,
            auto_name=True,
        )
        card = self._append_card(value)
        self._renumber()
        self._select_card(card)

    def _append_card(self, layer: LayerConfig) -> LayerCard:
        """建立卡片及动作接线，集合变更完成后统一编号。"""
        card = LayerCard(layer)
        card.editor.set_config_directory(self._config_dir)
        self._set_editor_context(card)
        card.editor.names.set_random_names(self._random_names)
        card.set_editable(self._editable)
        card.selected.connect(self._select_card)
        card.changed.connect(self._card_edited)
        card.remove_requested.connect(self._remove_card)
        card.move_requested.connect(self._move_card)
        self.cards.append(card)
        self.layers_layout.insertWidget(len(self.cards) - 1, card)
        self.editors.addWidget(card.page)
        return card

    def set_config_directory(self, directory: Path) -> None:
        """将素材路径选择器定位到当前配置目录。"""
        self._config_dir = directory
        for card in self.cards:
            card.editor.set_config_directory(directory)

    def _set_cards(self, layers: list[LayerConfig]) -> None:
        """整体替换卡片集合（载入配置用）。"""
        self._rendering = True
        selected_index = self.cards.index(self._selected) if self._selected in self.cards else 0
        for card in self.cards:
            self._dispose_card(card)
        self.cards.clear()
        self._selected = None
        for layer in layers:
            self._append_card(layer)
        self._renumber()
        if self.cards:
            self._select_card(self.cards[min(selected_index, len(self.cards) - 1)])
        self._rendering = False
        self._refresh_scope()
        self.view_changed.emit()

    def apply(self, config: AppConfig) -> None:
        """载入默认层及来源独立层，保持当前来源与层的选择。"""
        self._drafts.apply(config, self._config_dir)
        self._render_current()

    def collect_config(self, config: AppConfig, *, strict: bool = True) -> AppConfig:
        """收集全部来源的层设置，当前选择只控制显示范围。"""
        return self._drafts.collect(config, strict=strict)

    def _render_current(self) -> None:
        self._set_cards(self._drafts.layers_for(self._source, self._config_dir))

    def _store_current(self) -> None:
        self._drafts.store(self._source, self.collect(strict=False))
        self._refresh_scope()

    def _card_edited(self) -> None:
        if not self._rendering:
            self._store_current()
            self.card_changed.emit()

    def _refresh_scope(self) -> None:
        if self._source is not None:
            state = "独立设置" if self._source in self._drafts.sources else "共用默认 · 修改后独立"
            text = f"{self._source.name} · {state}"
        else:
            text = "默认层设置 · 应用于共用默认的来源" if self._separate else "合并打包 · 全部来源"
        self.scope_label.setText(text)
        self.scope_label.setToolTip(str(self._source) if self._source else text)
        for card in self.cards:
            card.editor.set_scope(text)
        self.scope_actions.setVisible(self._separate)
        self.defaults_button.setEnabled(self._source is not None)
        self.reset_button.setVisible(self._source is not None)
        self.reset_button.setEnabled(self._editable and self._source in self._drafts.sources)

    def _reset_source(self) -> None:
        if self._source in self._drafts.sources:
            self._drafts.reset(self._source)
            self._render_current()
            self.cards_changed.emit()

    def set_random_names(self, enabled: bool) -> None:
        """各层提示本次执行将重新生成名称。"""
        self._random_names = enabled
        for card in self.cards:
            card.editor.names.set_random_names(enabled)

    def set_editable(self, editable: bool) -> None:
        """按任务状态锁定各层参数及增删、移动操作。"""
        self._editable = editable
        self.add_button.setEnabled(editable)
        for card in self.cards:
            card.set_editable(editable)
        self._refresh_scope()

    def _remove_card(self, card: LayerCard) -> None:
        """删除卡片；压缩任务至少保留一层。"""
        if len(self.cards) == 1:
            show_info(self, "至少保留一层", "压缩任务至少需要一个层级。")
            return
        index = self.cards.index(card)
        self.cards.remove(card)
        self._dispose_card(card)
        self._renumber()
        if self._selected is card:
            self._select_card(self.cards[min(index, len(self.cards) - 1)])

    def _dispose_card(self, card: LayerCard) -> None:
        self.editors.removeWidget(card.page)
        card.page.hide()
        card.page.deleteLater()
        self.layers_layout.removeWidget(card)
        card.hide()
        card.deleteLater()

    def _select_card(self, card: LayerCard) -> None:
        self._selected = card
        for item in self.cards:
            item.select_button.setChecked(item is card)
        self.editors.setCurrentWidget(card.page)
        if not self._rendering:
            self.selection_changed.emit()

    def set_sources(self, sources: list[str], separate: bool, selected: str | None) -> None:
        """切换编辑范围，移除来源时一并清除它的独立设置。"""
        self._drafts.retain_sources(sources, self._config_dir)
        source = normalize_user_path(selected, self._config_dir) if separate and selected else None
        changed = (source, separate) != (self._source, self._separate)
        self._sources, self._separate, self._source = list(sources), separate, source
        if changed:
            self._render_current()
        else:
            for card in self.cards:
                self._set_editor_context(card)
                card.refresh_summary()
            self._refresh_scope()

    def _set_editor_context(self, card: LayerCard) -> None:
        sources = [str(self._source)] if self._source is not None else self._sources
        card.editor.set_sources(
            sources, self._separate, template=self._separate and self._source is None,
        )

    def _move_card(self, card: LayerCard, offset: int) -> None:
        """把卡片在列表中移动 offset 个位置，越界时忽略。"""
        current = self.cards.index(card)
        target = current + offset
        if not 0 <= target < len(self.cards):
            return
        self.cards[current], self.cards[target] = (
            self.cards[target],
            self.cards[current],
        )
        self._renumber()

    def _renumber(self) -> None:
        """按列表顺序重排控件并更新编号，完成后通知结构变化。"""
        for card in self.cards:
            self.layers_layout.removeWidget(card)
        for index, card in enumerate(self.cards, start=1):
            card.set_number(index, len(self.cards))
            self.layers_layout.insertWidget(index - 1, card)
        if not self._rendering:
            self._store_current()
            self.cards_changed.emit()

    def collect(self, *, strict: bool = True) -> list[LayerConfig]:
        """按显示顺序收集层参数；草稿保留未完成输入，路径冲突由压缩计划校验。"""
        layers: list[LayerConfig] = []
        for index, card in enumerate(self.cards, start=1):
            try:
                layer = card.collect(strict=strict)
            except ValueError as error:
                raise ValueError(f"第 {index} 层：{error}") from error
            layers.append(layer)
        return layers

    def passwords(self) -> list[str]:
        """按层顺序返回去重后的已填写密码。"""
        return self._drafts.passwords()
