"""主窗口视图：面板组装、来源与层名联动、状态展示和用户动作信号。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget
from qfluentwidgets import FluentIcon, PushButton, ToggleToolButton

from core.filesystem import normalize_user_path
from core.models import COMPRESS_MODE_SEPARATE
from core.moji import KAOMOJI
from gui.appearance.logo import LogoState, render_logo
from gui.appearance.theme import (
    APP_NAME,
    FONT_FAMILY,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    STYLE_SHEET,
    create_app_icon,
    load_application_fonts,
)
from gui.views.dialogs import show_error, show_info, show_licenses
from gui.views.layers_panel import LayersPanel
from gui.views.settings_dialog import SettingsDialog
from gui.views.side_panel import SidePanel
from gui.views.source_panel import SourcePanel

LOGO_SIZE = 86
HEADER_BUTTON_HEIGHT = 34


class MainWindow(QMainWindow):
    """展示编辑界面，通过信号交出文件操作与任务执行动作。"""

    load_requested = Signal()
    save_as_requested = Signal()
    close_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._config_dir = Path.cwd()
        self.setWindowTitle(f"{APP_NAME} · 多层嵌套压缩")
        self.setWindowIcon(create_app_icon())
        self.resize(1240, 820)
        self.setMinimumSize(940, 600)
        load_application_fonts()
        self.setStyleSheet(STYLE_SHEET)
        self._build_ui()
        self.source.paths_changed.connect(self._retemplate_default_layer_names)
        self.source.paths_changed.connect(self.update_summary)
        self.source.mode_changed.connect(self._on_mode_changed)
        self.layers.add_requested.connect(self.add_layer)
        self.layers.card_changed.connect(self.update_summary)
        self.layers.cards_changed.connect(self._on_cards_restructured)
        self.side.open_output_requested.connect(self.open_output_directory)

    def set_config_path(self, path: Path) -> None:
        """更新配置名称与路径选择器的起始位置。"""
        self._config_dir = path.parent
        self.source.set_config_directory(path.parent)
        self.settings.runtime.set_config_directory(path.parent)
        self.config_name_label.setText(path.name)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(SPACE_XL, SPACE_LG, SPACE_XL, SPACE_LG)
        root_layout.setSpacing(SPACE_LG)
        root_layout.addLayout(self._build_header())

        content = QHBoxLayout()
        content.setSpacing(SPACE_LG)
        main_column = QVBoxLayout()
        main_column.setSpacing(SPACE_MD)
        self.source = SourcePanel()
        main_column.addWidget(self.source)
        self.layers = LayersPanel()
        main_column.addWidget(self.layers, 1)
        content.addLayout(main_column, 3)
        self.side = SidePanel()
        content.addWidget(self.side, 2)
        root_layout.addLayout(content, 1)

    def _build_header(self) -> QHBoxLayout:
        """顶栏：项目 Logo、标题与配置载入/另存/设定按钮。"""
        header = QHBoxLayout()
        header.setSpacing(SPACE_MD)
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(LOGO_SIZE, LOGO_SIZE)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setPixmap(render_logo(
            LogoState.IDLE, LOGO_SIZE, device_pixel_ratio=self.devicePixelRatioF()
        ))
        self.logo_label.setToolTip("NestPack 项目 Logo")
        header.addWidget(self.logo_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(SPACE_XS)
        title = QLabel("多层嵌套压缩")
        title.setObjectName("title")
        title_font = QFont(FONT_FAMILY, 22, QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
        title.setFont(title_font)
        subtitle = QLabel("RAR、7z、ZIP 自由组合，逐层打包与解包。")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)

        config_box = QVBoxLayout()
        config_box.setSpacing(SPACE_XS)
        self.config_name_label = QLabel()
        self.config_name_label.setObjectName("muted")
        self.config_name_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        config_box.addWidget(self.config_name_label)
        config_buttons = QHBoxLayout()
        config_buttons.setSpacing(SPACE_SM)
        config_buttons.addStretch(1)
        license_button = PushButton("关于/许可")
        license_button.setFixedHeight(HEADER_BUTTON_HEIGHT)
        license_button.clicked.connect(lambda: show_licenses(self))
        config_buttons.addWidget(license_button)
        load_button = PushButton("载入配置")
        load_button.setFixedHeight(HEADER_BUTTON_HEIGHT)
        load_button.clicked.connect(self.load_requested.emit)
        save_as_button = PushButton("另存配置")
        save_as_button.setFixedHeight(HEADER_BUTTON_HEIGHT)
        save_as_button.clicked.connect(self.save_as_requested.emit)
        config_buttons.addWidget(load_button)
        config_buttons.addWidget(save_as_button)
        self.settings = SettingsDialog(self)
        self.settings_button = ToggleToolButton(FluentIcon.SETTING)
        self.settings_button.setFixedSize(HEADER_BUTTON_HEIGHT, HEADER_BUTTON_HEIGHT)
        self.settings_button.setToolTip("打开运行环境、任务选项与混淆加固设定")
        self.settings_button.toggled.connect(self._toggle_settings)
        # 对话框被 X 关闭时同步齿轮的选中态，避免按钮卡在“打开中”。
        self.settings.rejected.connect(lambda: self.settings_button.setChecked(False))
        config_buttons.addWidget(self.settings_button)
        config_box.addLayout(config_buttons)
        header.addLayout(config_box)
        return header

    def _toggle_settings(self, checked: bool) -> None:
        """根据齿轮按钮的选中状态显示或隐藏设定对话框。"""
        if checked:
            self.settings.show()
        else:
            self.settings.hide()

    def _retemplate_default_layer_names(self) -> None:
        """来源变化后刷新仍使用默认模板的层名，改为第一个来源的名字。"""
        sources = self.source.paths()
        if sources:
            self.layers.retemplate_defaults(Path(sources[0]).stem)

    def _on_mode_changed(self) -> None:
        """切换打包方式后调整各层名称可编辑状态并刷新默认层名。"""
        self.layers.set_names_editable(
            self.source.mode() != COMPRESS_MODE_SEPARATE
        )
        self._retemplate_default_layer_names()

    def add_layer(self) -> None:
        """「＋ 添加一层」：按第一个来源名生成默认层并追加卡片。"""
        sources = self.source.paths()
        stem = Path(sources[0]).stem if sources else "layer"
        self.layers.add_card(default_stem=stem)

    def _on_cards_restructured(self) -> None:
        """层级集合结构变化后刷新名称可编辑状态与概览。"""
        self.layers.set_names_editable(
            self.source.mode() != COMPRESS_MODE_SEPARATE
        )
        self.update_summary()

    def update_summary(self) -> None:
        """按面板提供的统计刷新任务概览。"""
        layers, passwords, recovery = self.layers.counts()
        self.side.update_stats(len(self.source.paths()), layers, passwords, recovery)

    def set_compressing(self, active: bool) -> None:
        """按任务状态切换来源、层级与侧栏动作的可用性。"""
        self.side.set_compressing(active)
        self.source.set_editable(not active)
        self.layers.set_editable(not active)

    def set_installing(self, active: bool) -> None:
        self.side.set_installing(active)
        self.settings.runtime.set_installing(active)

    def set_status(self, message: str, state: LogoState | None = None) -> None:
        """更新状态栏文字；有任务状态时同步切换 Logo 图片与颜文字。"""
        if state is not None:
            message = f"{message} {KAOMOJI[state.value]}"
            self.logo_label.setPixmap(render_logo(
                state, LOGO_SIZE, device_pixel_ratio=self.devicePixelRatioF()
            ))
        self.side.set_status(message)

    def open_output_directory(self) -> None:
        """在系统资源管理器中打开输出目录。"""
        raw_path = self.source.output_directory()
        if not raw_path:
            show_info(self, "尚未设置", "请先选择输出目录。")
            return
        output_path = normalize_user_path(raw_path, self._config_dir)
        if not output_path.is_dir():
            show_error(self, "目录不存在", str(output_path))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_path)))

    def closeEvent(self, event: QCloseEvent) -> None:
        """由应用协调当前任务的关闭时机。"""
        self.close_requested.emit(event)
