"""解包工作区：最外层文件、候选密码、层数与输出目录。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import PlainTextEdit, PushButton, SpinBox

from core.filesystem import normalize_user_path
from gui.config.paths import selection_directory
from gui.views.file_dialog import pick_archive, pick_directory
from gui.views.widgets import CollapsibleSection, SectionCard, text_field


class UnpackPanel(QWidget):
    """工作区切换时保留解包表单，执行输入由应用收集为快照。"""

    extract_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._config_dir = Path.cwd()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        form = SectionCard("解包", "选择最外层文件，逐层恢复原始内容。")
        archive_box, self.archive_edit, row = text_field("最外层文件", "")
        browse = PushButton("选择文件…")
        browse.clicked.connect(self._choose_archive)
        row.addWidget(browse)
        self.archive_edit.setPlaceholderText("归档、分卷首卷或伪装 MP4")
        form.body_layout.addWidget(archive_box)
        hint = QLabel("分卷请选择第一卷；伪装扩展名会按文件内容识别。")
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        form.body_layout.addWidget(hint)
        form.body_layout.addWidget(QLabel("候选密码（每行一个）"))
        self.password_edit = PlainTextEdit()
        self.password_edit.setPlaceholderText("也会尝试当前配置中填写的各层密码。")
        self.password_edit.setMinimumHeight(100)
        form.body_layout.addWidget(self.password_edit)
        options = CollapsibleSection("解包选项")
        layers_row = QHBoxLayout()
        layers_row.addWidget(QLabel("解包层数"))
        self.layers_spin = SpinBox()
        self.layers_spin.setRange(0, 99)
        self.layers_spin.setSpecialValueText("自动识别")
        self.layers_spin.setToolTip("原始内容本身是归档时，可指定层数以保留该归档。")
        layers_row.addWidget(self.layers_spin)
        layers_row.addStretch(1)
        options.body_layout.addLayout(layers_row)
        form.body_layout.addWidget(options)
        layout.addWidget(form)
        extract = SectionCard("提取原归档", "从伪装 MP4 恢复原来的压缩包，保留其内容和密码。")
        extract_button = PushButton("仅提取原归档…")
        extract_button.clicked.connect(self.extract_requested.emit)
        extract.body_layout.addWidget(extract_button)
        layout.addWidget(extract)
        layout.addStretch(1)

        self.output_panel = SectionCard("输出", "解包恢复的文件保存到以下目录。")
        output_box, self.output_edit, row = text_field("输出目录", "")
        browse_output = PushButton("浏览…")
        browse_output.clicked.connect(self._choose_output)
        row.addWidget(browse_output)
        self.output_panel.body_layout.addWidget(output_box)
        self.result_label = QLabel()
        self.result_label.setObjectName("muted")
        self.result_label.setWordWrap(True)
        self.output_panel.body_layout.addWidget(self.result_label)

    def set_config_directory(self, directory: Path) -> None:
        if directory != self._config_dir:
            for editor in (self.archive_edit, self.output_edit):
                if editor.text().strip():
                    editor.setText(str(normalize_user_path(editor.text(), self._config_dir)))
        self._config_dir = directory

    def _choose_archive(self) -> None:
        selected = pick_archive(
            self.window(), str(selection_directory(self.archive_edit.text(), self._config_dir))
        )
        if selected:
            self.archive_edit.setText(selected)
            if not self.output_directory():
                path = Path(selected)
                self.output_edit.setText(str(path.parent / f"{path.stem}_unpacked"))

    def _choose_output(self) -> None:
        raw = self.output_directory()
        selected = pick_directory(
            self.window(), title="选择解包输出目录",
            start_path=str(selection_directory(raw, self._config_dir)),
            default_output=str(normalize_user_path(raw, self._config_dir)) if raw else "",
        )
        if selected:
            self.output_edit.setText(selected)

    def output_directory(self) -> str:
        return self.output_edit.text().strip()

    def collect(self, preset_candidates: list[str]) -> tuple[Path, Path, list[str], int | None]:
        raw = self.archive_edit.text().strip()
        if not raw:
            raise ValueError("请选择最外层文件。")
        archive = normalize_user_path(raw, self._config_dir)
        output = (
            normalize_user_path(self.output_directory(), self._config_dir)
            if self.output_directory() else archive.parent / f"{archive.stem}_unpacked"
        )
        self.output_edit.setText(str(output))
        candidates = list(dict.fromkeys([
            line for line in self.password_edit.toPlainText().splitlines() if line
        ] + preset_candidates))
        return archive, output, candidates, self.layers_spin.value() or None

    def set_editable(self, editable: bool) -> None:
        self.setEnabled(editable)
        self.output_panel.setEnabled(editable)

    def show_result(self, entries: list[Path], output: Path) -> None:
        self.result_label.setText(f"已恢复 {len(entries)} 个条目\n{output}")
