"""文件选择器的 Fluent 浅色样式。"""

# 非原生 QFileDialog 使用与主窗口一致的 Fluent 浅色配色。
FILE_DIALOG_STYLE = """
QFileDialog { background: #F4F8FD; }
QFileDialog QLabel { color: #33475F; }
QFileDialog QSplitter, QFileDialog QSplitter::handle {
    background: transparent;
    border: none;
}
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
    border: 1px solid #E4EDF8;
    border-radius: 8px;
    selection-background-color: #DCEEFB;
    selection-color: #2F74B5;
    outline: 0;
}
QFileDialog QListView::item, QFileDialog QTreeView::item {
    padding: 4px 6px;
    border-radius: 4px;
}
QFileDialog QListView::item:selected,
QFileDialog QTreeView::item:selected {
    background: #DCEEFB;
    color: #2F74B5;
}
QFileDialog QScrollBar:vertical,
QFileDialog QScrollBar:horizontal {
    background: transparent;
    border: none;
    margin: 0;
}
QFileDialog QScrollBar::handle:vertical {
    background: #B5C7DA;
    border-radius: 4px;
    min-height: 28px;
}
QFileDialog QScrollBar::handle:horizontal {
    background: #B5C7DA;
    border-radius: 4px;
    min-width: 28px;
}
QFileDialog QScrollBar::handle:vertical:hover,
QFileDialog QScrollBar::handle:horizontal:hover {
    background: #5EB2EF;
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
    background: #F5F9FE;
    border: 1px solid #B5C7DA;
    border-radius: 8px;
}
QFileDialog QListView#sidebar::item {
    padding: 8px 10px;
    border-radius: 6px;
    color: #33475F;
}
QFileDialog QListView#sidebar::item:selected {
    background: #DCEEFB;
    color: #2F74B5;
}
QFileDialog QComboBox {
    border: 1px solid #E4EDF8;
    border-radius: 6px;
    padding: 4px 8px;
    background: #FFFFFF;
    color: #33475F;
}
QFileDialog QComboBox:hover {
    border-color: #5EB2EF;
}
QFileDialog QComboBox::drop-down {
    border: none;
    width: 20px;
}
QFileDialog QComboBox::drop-down:editable {
    border: none;
}
QFileDialog QLineEdit#fileNameEdit {
    border: 1px solid #E4EDF8;
    border-radius: 6px;
    padding: 4px 8px;
    background: #FFFFFF;
    color: #33475F;
}
QFileDialog QLineEdit#fileNameEdit:focus {
    border-color: #5EB2EF;
}
QFileDialog QToolButton,
QFileDialog QToolBar QToolButton {
    background: #FFFFFF;
    border: 1px solid #98B5D2;
    padding: 4px;
    border-radius: 6px;
}
QFileDialog QToolButton:hover,
QFileDialog QToolBar QToolButton:hover {
    background: #DCEEFB;
    border-color: #5EB2EF;
}
QFileDialog QToolButton:pressed,
QFileDialog QToolBar QToolButton:pressed {
    background: #5EB2EF;
    color: #FFFFFF;
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
    color: #2F74B5;
    border: 1px solid #B5C7DA;
}
QFileDialog QDialogButtonBox QPushButton#primaryButton {
    background: #5EB2EF;
    color: #FFFFFF;
    border: 1px solid #5EB2EF;
}
QFileDialog QDialogButtonBox QPushButton#primaryButton:hover {
    background: #7CC2F4;
    border-color: #7CC2F4;
}
QFileDialog QDialogButtonBox QPushButton:hover {
    background: #DCEEFB;
    border-color: #5EB2EF;
}
"""
