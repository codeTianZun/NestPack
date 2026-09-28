"""主窗口右侧栏：任务概览卡片、动作卡片与压缩过程日志。

应用控制器连接任务动作，主窗口负责概览与界面联动。
侧栏通过动作信号通知调用方，并用展示方法更新任务状态；它位于
独立滚动区里，窗口高度不足时内容可以滚动而不是被裁切。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    PlainTextEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    ScrollArea,
)

from core.moji import SIGNATURE
from gui.appearance.theme import (
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    apply_accent_glow,
    apply_card_shadow,
    apply_danger_style,
)
from gui.views.widgets import SectionCard, stat_box


class SidePanel(ScrollArea):
    """任务概览 + 开始/取消动作 + 实时日志组成的右侧栏。"""

    run_requested = Signal()
    cancel_requested = Signal()
    save_requested = Signal()
    unpack_requested = Signal()
    video_requested = Signal()
    open_output_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        column = QVBoxLayout(container)
        column.setContentsMargins(0, 0, SPACE_SM, 0)
        column.setSpacing(SPACE_MD)

        # ---- 任务概览卡片 ----
        summary_card = SectionCard("任务概览", "开始前快速核对关键参数。")
        stats = QHBoxLayout()
        stats.setSpacing(SPACE_SM)
        self.source_stat = stat_box("0 个来源", "来源")
        self.layer_stat = stat_box("0 层", "层级")
        self.password_stat = stat_box("0 个密码", "加密")
        self.recovery_stat = stat_box("0 个恢复记录", "恢复")
        stats.addWidget(self.source_stat[0], 1)
        stats.addWidget(self.layer_stat[0], 1)
        stats.addWidget(self.password_stat[0], 1)
        stats.addWidget(self.recovery_stat[0], 1)
        summary_card.body_layout.addLayout(stats)
        column.addWidget(summary_card)

        # ---- 动作卡片 ----
        action_card = QFrame()
        action_card.setObjectName("actionCard")
        apply_card_shadow(action_card)
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(SPACE_LG, SPACE_MD, SPACE_LG, SPACE_MD)
        action_layout.setSpacing(SPACE_SM)
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        action_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        action_layout.addWidget(self.status_label)

        self.run_button = PrimaryPushButton("开始压缩")
        apply_accent_glow(self.run_button)
        self.cancel_button = PushButton("取消")
        apply_danger_style(self.cancel_button)
        self.cancel_button.hide()
        # 主操作行：开始压缩与取消同位切换，独占一行保持位置稳定。
        primary_row = QHBoxLayout()
        primary_row.setSpacing(SPACE_SM)
        primary_row.addWidget(self.run_button, 1)
        primary_row.addWidget(self.cancel_button, 1)
        action_layout.addLayout(primary_row)

        self.save_button = PushButton("保存配置")
        self.unpack_button = PushButton("解包…")
        self.unpack_button.setToolTip(
            "反向操作：选择嵌套压缩包，逐层解开并释放原始文件；"
            "支持伪装扩展名与分卷（伪装的分卷套会自动识别）。"
        )
        self.open_output_button = PushButton("打开输出目录")
        # 次要操作行：保存/解包/打开目录横排，主操作与次要操作视觉分组。
        secondary_row = QHBoxLayout()
        secondary_row.setSpacing(SPACE_SM)
        secondary_row.addWidget(self.save_button)
        secondary_row.addWidget(self.unpack_button)
        secondary_row.addWidget(self.open_output_button)
        action_layout.addLayout(secondary_row)
        self.video_button = PushButton("视频融合 / 提取原归档…")
        self.video_button.clicked.connect(self.video_requested)
        action_layout.addWidget(self.video_button)
        column.addWidget(action_card)

        # ---- 压缩过程日志卡片 ----
        progress_card = SectionCard(
            "压缩过程", "实时显示正在压缩的文件与历史步骤。"
        )
        self.progress_log = PlainTextEdit()
        self.progress_log.setReadOnly(True)
        self.progress_log.setMaximumBlockCount(500)
        self.progress_log.setPlaceholderText("开始压缩后，这里会显示每个文件的处理进度。")
        self.progress_log.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        progress_card.body_layout.addWidget(self.progress_log)
        column.addWidget(progress_card, 1)

        signature = QLabel(SIGNATURE)
        signature.setObjectName("muted")
        signature.setAlignment(Qt.AlignmentFlag.AlignCenter)
        column.addWidget(signature)
        self.setWidget(container)
        self.run_button.clicked.connect(self.run_requested)
        self.cancel_button.clicked.connect(self.cancel_requested)
        self.save_button.clicked.connect(self.save_requested)
        self.unpack_button.clicked.connect(self.unpack_requested)
        self.open_output_button.clicked.connect(self.open_output_requested)

    def update_stats(
        self,
        source_count: int,
        layer_count: int,
        password_count: int,
        recovery_count: int,
    ) -> None:
        """刷新任务概览的四个统计数字（计数由主窗口计算）。"""
        self.source_stat[1].setText(f"{source_count} 个来源")
        self.layer_stat[1].setText(f"{layer_count} 层")
        self.password_stat[1].setText(f"{password_count} 个密码")
        self.recovery_stat[1].setText(f"{recovery_count} 个恢复记录")

    def set_compressing(self, active: bool) -> None:
        """更新压缩期间的动作展示。"""
        self.run_button.setVisible(not active)
        self.save_button.setEnabled(not active)
        self.video_button.setEnabled(not active)
        self.cancel_button.setVisible(active)
        self.cancel_button.setEnabled(True)

    def set_installing(self, active: bool) -> None:
        """更新安装期间的可用动作。"""
        self.run_button.setEnabled(not active)
        self.unpack_button.setEnabled(not active)
        self.video_button.setEnabled(not active)

    def show_cancelling(self) -> None:
        """取消请求发出后等待任务结束。"""
        self.cancel_button.setEnabled(False)

    def set_progress(self, value: int, total: int) -> None:
        """更新确定进度。"""
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(value)

    def set_status(self, message: str) -> None:
        self.status_label.setText(message)

    def clear_log(self) -> None:
        self.progress_log.clear()

    def append_log(self, line: str) -> None:
        """追加一行并滚动到日志末尾。"""
        text = line.strip()
        if not text:
            return
        self.progress_log.appendPlainText(text)
        cursor = self.progress_log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.progress_log.setTextCursor(cursor)
        self.progress_log.ensureCursorVisible()


__all__ = ["SidePanel"]
