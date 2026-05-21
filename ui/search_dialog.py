"""
Search dialog: full-text + tag search across all entries.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QListWidget, QListWidgetItem,
    QTextEdit, QSplitter, QWidget, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont


class SearchDialog(QDialog):
    entry_selected = Signal(str)  # emits entry_date

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("🔍 Search Research Logs")
        self.resize(720, 500)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Search bar row
        search_row = QHBoxLayout()

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Search keywords...")
        self.query_input.setFixedHeight(34)
        self.query_input.textChanged.connect(self._debounce_search)
        search_row.addWidget(self.query_input, 3)

        self.tag_filter = QComboBox()
        self.tag_filter.setFixedHeight(34)
        self.tag_filter.addItem("Any tag", "")
        for tag in self.db.get_all_tags():
            self.tag_filter.addItem(f"#{tag}", tag)
        self.tag_filter.currentIndexChanged.connect(self._run_search)
        search_row.addWidget(self.tag_filter, 1)

        self.search_btn = QPushButton("Search")
        self.search_btn.setFixedHeight(34)
        self.search_btn.clicked.connect(self._run_search)
        search_row.addWidget(self.search_btn)

        layout.addLayout(search_row)

        # Results + preview splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Results list
        results_pane = QWidget()
        results_layout = QVBoxLayout(results_pane)
        results_layout.setContentsMargins(0, 0, 0, 0)
        self.result_count = QLabel("Type to search…")
        self.result_count.setStyleSheet("color: grey; font-size: 11px;")
        results_layout.addWidget(self.result_count)
        self.results_list = QListWidget()
        self.results_list.currentItemChanged.connect(self._on_result_selected)
        self.results_list.itemDoubleClicked.connect(self._open_entry)
        results_layout.addWidget(self.results_list)
        splitter.addWidget(results_pane)

        # Snippet preview
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setObjectName("searchPreview")
        splitter.addWidget(self.preview)
        splitter.setSizes([260, 440])

        layout.addWidget(splitter)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        open_btn = QPushButton("Open Entry")
        open_btn.setDefault(True)
        open_btn.clicked.connect(self._open_entry)
        btn_row.addWidget(open_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        # Debounce timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self._run_search)

        # Auto-focus
        self.query_input.setFocus()

    def _debounce_search(self):
        self._timer.start()

    def _run_search(self):
        query = self.query_input.text().strip()
        tag = self.tag_filter.currentData()

        if not query and not tag:
            self.results_list.clear()
            self.result_count.setText("Type to search…")
            return

        results = self.db.search(query, tag if tag else None)
        self.results_list.clear()
        self.result_count.setText(f"{len(results)} result{'s' if len(results) != 1 else ''} found")

        for r in results:
            item = QListWidgetItem(f"📄 {r['entry_date']}")
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.results_list.addItem(item)

        if results:
            self.results_list.setCurrentRow(0)

    def _on_result_selected(self, item):
        if not item:
            return
        r = item.data(Qt.ItemDataRole.UserRole)
        snippet = r.get("snippet", r.get("content", ""))[:800]
        self.preview.setPlainText(f"Date: {r['entry_date']}\n\n{snippet}")

    def _open_entry(self, *_):
        item = self.results_list.currentItem()
        if not item:
            return
        r = item.data(Qt.ItemDataRole.UserRole)
        self.entry_selected.emit(r["entry_date"])
        self.accept()
