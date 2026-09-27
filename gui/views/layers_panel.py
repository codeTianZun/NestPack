"""压缩层级面板：卡片集合、配置读写、名称联动与概览统计。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QScrollArea,
    QSizePolicy,
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

    def __init__(self) -> None:
        super().__init__(
            "压缩层级",
            "列表顺序就是执行顺序：第一层在最里面，最后一层是最终压缩包。",
        )
        self.cards: list[LayerCard] = []

        self.add_button = PushButton("添加一层", None, FluentIcon.ADD)
        self.add_button.clicked.connect(self.add_requested.emit)
        self.actions.addWidget(self.add_button)

        self.layer_scroll = QScrollArea()
        self.layer_scroll.setWidgetResizable(True)
        self.layer_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.layer_container = QWidget()
        self.layers_layout = QVBoxLayout(self.layer_container)
        self.layers_layout.setContentsMargins(0, 0, SPACE_XS, 0)
        self.layers_layout.setSpacing(SPACE_SM)
        self.layers_layout.addStretch(1)
        self.layer_scroll.setWidget(self.layer_container)
        self.body_layout.addWidget(self.layer_scroll)
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
        self._append_card(value)
        self._renumber()

    def _append_card(self, layer: LayerConfig) -> None:
        """建立卡片及动作接线，集合变更完成后统一编号。"""
        card = LayerCard(layer)
        card.changed.connect(self.card_changed.emit)
        card.remove_requested.connect(self._remove_card)
        card.move_requested.connect(self._move_card)
        self.cards.append(card)
        self.layers_layout.insertWidget(len(self.cards) - 1, card)

    def set_cards(self, layers: list[LayerConfig]) -> None:
        """整体替换卡片集合（载入配置用）。"""
        for card in self.cards:
            self.layers_layout.removeWidget(card)
            card.hide()
            card.deleteLater()
        self.cards.clear()
        for layer in layers:
            self._append_card(layer)
        self._renumber()

    def retemplate_defaults(self, stem: str) -> None:
        """来源变化后，把仍使用默认模板的层名刷新为第一个来源的名字。"""
        for index, card in enumerate(self.cards, start=1):
            card.retemplate_default(stem, index)

    def set_names_editable(self, editable: bool) -> None:
        """设置全部层级名称输入框的可编辑状态。"""
        for card in self.cards:
            card.set_name_editable(editable)

    def set_editable(self, editable: bool) -> None:
        """压缩运行期间锁定层级面板：禁止增删层与修改各层参数。

        滚动区整体禁用会让所有卡片的控件一并失效；恢复时各控件回到
        各自的独立状态（如 separate 模式的层名、非 rar 的恢复记录）。
        """
        self.add_button.setEnabled(editable)
        self.layer_scroll.setEnabled(editable)

    def _remove_card(self, card: LayerCard) -> None:
        """删除卡片；压缩任务至少保留一层。"""
        if len(self.cards) == 1:
            show_info(self, "至少保留一层", "压缩任务至少需要一个层级。")
            return
        self.cards.remove(card)
        self.layers_layout.removeWidget(card)
        card.hide()
        card.deleteLater()
        self._renumber()

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
            card.set_number(index)
            self.layers_layout.insertWidget(index - 1, card)
        self.cards_changed.emit()

    def collect(self, *, strict: bool = True) -> list[LayerConfig]:
        """按显示顺序收集层参数；执行时校验名称及重复，草稿保留未完成输入。"""
        layers: list[LayerConfig] = []
        used_names: set[str] = set()
        for index, card in enumerate(self.cards, start=1):
            try:
                layer = card.collect(index, strict=strict)
            except ValueError as error:
                raise ValueError(f"第 {index} 层：{error}") from error
            folded_name = layer.archive_name.casefold()
            if strict and folded_name in used_names:
                raise ValueError(f"第 {index} 层：压缩包名称与其他层重复")
            used_names.add(folded_name)
            layers.append(layer)
        return layers

    def counts(self) -> tuple[int, int, int]:
        """返回层数、已填写密码数与恢复记录数。"""
        layers = self.collect(strict=False)
        return (
            len(layers),
            sum(bool(layer.password) for layer in layers),
            sum(layer.recovery_percent is not None for layer in layers),
        )

    def passwords(self) -> list[str]:
        """按层顺序返回去重后的已填写密码。"""
        return list(dict.fromkeys(
            layer.password for layer in self.collect(strict=False) if layer.password
        ))
