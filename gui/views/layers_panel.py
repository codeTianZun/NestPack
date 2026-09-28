"""压缩层级面板：卡片集合、配置读写、名称联动与概览统计。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import FluentIcon, PushButton

from core.models import LayerConfig
from gui.appearance.theme import SPACE_SM, SPACE_XS
from gui.views.dialogs import show_info
from gui.views.layer_card import LayerCard
from gui.views.widgets import SectionCard


class LayersPanel(SectionCard):
    """「压缩层级」卡片：列表顺序即执行顺序，第一层在最里面。"""

    #: 用户点击「＋ 添加一层」；默认层名需要来源信息，由主窗口生成。
    add_requested = Signal()
    #: 任一层级卡片的字段被编辑。
    card_changed = Signal()
    #: 卡片集合结构变化（新增/删除/移动后的重编号完成）。
    cards_changed = Signal()
    selection_changed = Signal()

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
        self._config_dir = Path.cwd()

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
        """追加一张层级卡片；未给定配置时按来源名与序号生成默认模板。"""
        number = len(self.cards) + 1
        value = layer or LayerConfig(
            archive_name=f"{default_stem}_{number}.rar",
            password="",
            recovery_percent=None,
            name_template=f"{{stem}}_{number}",
        )
        card = self._append_card(value)
        self._renumber()
        self._select_card(card)

    def _append_card(self, layer: LayerConfig) -> LayerCard:
        """建立卡片及动作接线，集合变更完成后统一编号。"""
        card = LayerCard(layer)
        card.editor.set_config_directory(self._config_dir)
        card.editor.disguise.set_sources(self._sources, self._separate)
        card.set_editable(self._editable)
        card.selected.connect(self._select_card)
        card.changed.connect(self.card_changed.emit)
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

    def set_cards(self, layers: list[LayerConfig]) -> None:
        """整体替换卡片集合（载入配置用）。"""
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

    def retemplate_defaults(self, stem: str) -> None:
        """来源变化后，把仍使用默认模板的层名刷新为第一个来源的名字。"""
        for index, card in enumerate(self.cards, start=1):
            card.editor.retemplate_default(stem, index)

    def set_names_editable(self, editable: bool) -> None:
        """设置全部层级名称输入框的可编辑状态。"""
        for card in self.cards:
            card.editor.set_name_editable(editable)

    def set_editable(self, editable: bool) -> None:
        """按任务状态锁定各层参数及增删、移动操作。"""
        self._editable = editable
        self.add_button.setEnabled(editable)
        for card in self.cards:
            card.set_editable(editable)

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
        self.selection_changed.emit()

    def set_sources(self, sources: list[str], separate: bool) -> None:
        """更新各层可用的逐来源视频选择。"""
        self._sources, self._separate = list(sources), separate
        for card in self.cards:
            card.editor.disguise.set_sources(sources, separate)

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
        self.cards_changed.emit()

    def collect(self, *, strict: bool = True) -> list[LayerConfig]:
        """按显示顺序收集层参数；执行时校验名称及重复，草稿保留未完成输入。"""
        layers: list[LayerConfig] = []
        used_names: set[str] = set()
        for index, card in enumerate(self.cards, start=1):
            try:
                layer = card.collect(strict=strict)
            except ValueError as error:
                raise ValueError(f"第 {index} 层：{error}") from error
            folded_name = layer.archive_name.casefold()
            if strict and folded_name in used_names:
                raise ValueError(f"第 {index} 层：压缩包名称与其他层重复")
            used_names.add(folded_name)
            layers.append(layer)
        return layers

    def passwords(self) -> list[str]:
        """按层顺序返回去重后的已填写密码。"""
        return list(dict.fromkeys(
            layer.password for layer in self.collect(strict=False) if layer.password
        ))
