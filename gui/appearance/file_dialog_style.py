"""文件选择器的 Fluent 浅色样式。"""

# 非原生 QFileDialog 使用与主窗口一致的 Fluent 浅色配色。
FILE_DIALOG_STYLE = """
QFileDialog { background: #FCFAFE; }
QFileDialog QLabel { color: #2D3249; }
QFileDialog QSplitter {
    background: transparent;
    border: none;
}
QFileDialog QSplitter::handle:horizontal {
    background: #DAD2E6;
    width: 6px;
    border: none;
    border-radius: 3px;
    margin: 4px 1px;
}
QFileDialog QSplitter::handle:horizontal:hover { background: #BAAFC9; }
QFileDialog QToolBar, QFileDialog QToolBar::separator {
    background: transparent;
    border: none;
    spacing: 2px;
}
QFileDialog QHeaderView,
QFileDialog QHeaderView::section,
QFileDialog QFrame {
    border: none;
    background: transparent;
}
QFileDialog QListView, QFileDialog QTreeView {
    background: #FFFFFF;
    border: 1px solid #DAD2E6;
    border-radius: 8px;
    selection-background-color: #E8DDF1;
    selection-color: #725196;
    outline: 0;
}
QFileDialog QListView::item, QFileDialog QTreeView::item {
    padding: 4px 6px;
    border-radius: 4px;
}
QFileDialog QListView::item:selected,
QFileDialog QTreeView::item:selected {
    background: #E8DDF1;
    color: #725196;
}
QFileDialog QScrollBar:vertical,
QFileDialog QScrollBar:horizontal {
    background: transparent;
    border: none;
    margin: 0;
}
QFileDialog QScrollBar:vertical { width: 10px; }
QFileDialog QScrollBar:horizontal { height: 10px; }
QFileDialog QScrollBar::handle:vertical {
    background: #BAAFC9;
    border-radius: 4px;
    min-height: 28px;
}
QFileDialog QScrollBar::handle:horizontal {
    background: #BAAFC9;
    border-radius: 4px;
    min-width: 28px;
}
QFileDialog QScrollBar::handle:vertical:hover,
QFileDialog QScrollBar::handle:horizontal:hover {
    background: #725196;
}
QFileDialog QScrollBar::add-line,
QFileDialog QScrollBar::sub-line {
    height: 0;
    width: 0;
    background: transparent;
    border: none;
}
QFileDialog QScrollBar::add-page,
QFileDialog QScrollBar::sub-page {
    background: transparent;
}
QFileDialog QListView#sidebar {
    background: #F0EAF7;
    border: 1px solid #BAAFC9;
    border-radius: 8px;
}
QFileDialog QListView#sidebar::item {
    height: 22px;
    padding: 4px 8px;
    border-radius: 6px;
    color: #2D3249;
}
QFileDialog QListView#sidebar::item:hover { background: #E8DDF1; }
QFileDialog QListView#sidebar::item:selected {
    background: #E8DDF1;
    color: #725196;
}
QFileDialog QComboBox {
    border: 1px solid #DAD2E6;
    border-radius: 6px;
    padding: 4px 8px;
    background: #FFFFFF;
    color: #2D3249;
}
QFileDialog QComboBox:hover {
    border-color: #725196;
}
QFileDialog QComboBox::drop-down {
    border: none;
    width: 20px;
}
QFileDialog QComboBox::drop-down:editable {
    border: none;
}
QFileDialog QLineEdit#pathEdit {
    border: 1px solid #DAD2E6;
    border-radius: 6px;
    padding: 4px 8px;
    background: #FFFFFF;
    color: #2D3249;
    selection-background-color: #E8DDF1;
    selection-color: #725196;
}
QFileDialog QLineEdit#pathEdit:focus {
    border-color: #725196;
}
QFileDialog QLineEdit#fileNameEdit {
    border: 1px solid #DAD2E6;
    border-radius: 6px;
    padding: 4px 8px;
    background: #FFFFFF;
    color: #2D3249;
    selection-background-color: #E8DDF1;
    selection-color: #725196;
}
QFileDialog QLineEdit#fileNameEdit:focus {
    border-color: #725196;
}
QFileDialog QToolButton,
QFileDialog QToolBar QToolButton {
    background: transparent;
    border: 1px solid transparent;
    padding: 6px;
    border-radius: 6px;
}
QFileDialog QToolButton:hover,
QFileDialog QToolBar QToolButton:hover {
    background: #E8DDF1;
    border-color: #725196;
}
QFileDialog QToolButton:pressed, QFileDialog QToolButton:checked {
    background: #E8DDF1;
    border-color: #BAAFC9;
}
QFileDialog QToolButton:disabled,
QFileDialog QToolBar QToolButton:disabled {
    background: transparent;
    border: none;
}
QFileDialog QDialogButtonBox QPushButton {
    border-radius: 6px;
    padding: 6px 18px;
    background: #FFFFFF;
    color: #725196;
    border: 1px solid #BAAFC9;
}
QFileDialog QDialogButtonBox QPushButton#primaryButton {
    background: #725196;
    color: #FFFFFF;
    border: 1px solid #725196;
}
QFileDialog QDialogButtonBox QPushButton#primaryButton:hover {
    background: #8664AA;
    border-color: #8664AA;
}
QFileDialog QDialogButtonBox QPushButton:hover {
    background: #E8DDF1;
    border-color: #725196;
}
"""
