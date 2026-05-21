"""
Left sidebar: calendar widget + recent entries + tag filter.
"""
from datetime import date, datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QCalendarWidget, QLineEdit, QComboBox,
    QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QDate, QSize
from PySide6.QtGui import QTextCharFormat, QColor, QFont, QBrush


class SidebarWidget(QWidget):
    date_selected = Signal(str)   # emitted with YYYY-MM-DD

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._entry_dates: set = set()
        self._build_ui()
        self.refresh()

    # ─── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setFixedWidth(260)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # ── Calendar ──────────────────────────────────────────────────────────
        cal_label = QLabel("📅  Calendar")
        cal_label.setProperty("sidebarSection", True)
        layout.addWidget(cal_label)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setNavigationBarVisible(True)
        self.calendar.setMinimumHeight(200)
        self.calendar.setMaximumHeight(230)
        self.calendar.clicked.connect(self._on_calendar_click)
        self.calendar.currentPageChanged.connect(self._highlight_entry_dates)
        layout.addWidget(self.calendar)

        # ── Tag filter ────────────────────────────────────────────────────────
        tag_label = QLabel("🏷  Filter by Tag")
        tag_label.setProperty("sidebarSection", True)
        layout.addWidget(tag_label)

        self.tag_combo = QComboBox()
        self.tag_combo.addItem("— All entries —", "")
        self.tag_combo.currentIndexChanged.connect(self._on_tag_filter)
        layout.addWidget(self.tag_combo)

        # ── Recent entries list ───────────────────────────────────────────────
        recent_label = QLabel("🗒  Recent Entries")
        recent_label.setProperty("sidebarSection", True)
        layout.addWidget(recent_label)

        self.recent_list = QListWidget()
        self.recent_list.setAlternatingRowColors(True)
        self.recent_list.itemClicked.connect(self._on_recent_click)
        self.recent_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.recent_list)

    # ─── Public API ────────────────────────────────────────────────────────────

    def refresh(self):
        """Reload calendar highlights and recent list from DB."""
        self._entry_dates = set(self.db.get_all_entry_dates())
        self._highlight_entry_dates()
        self._reload_recent_list()
        self._reload_tags()

    def set_current_date(self, date_str: str):
        """Programmatically select a date on the calendar."""
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            self.calendar.setSelectedDate(QDate(d.year, d.month, d.day))
        except ValueError:
            pass

    # ─── Internal helpers ──────────────────────────────────────────────────────

    def _highlight_entry_dates(self, *_):
        """Bold dates that have entries in the current month view."""
        # Clear existing formats first
        default_fmt = QTextCharFormat()
        self.calendar.setDateTextFormat(QDate(), default_fmt)

        has_entry_fmt = QTextCharFormat()
        has_entry_fmt.setFontWeight(QFont.Weight.Bold)
        has_entry_fmt.setBackground(QBrush(QColor("#dce9ff")))

        for date_str in self._entry_dates:
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
                qd = QDate(d.year, d.month, d.day)
                self.calendar.setDateTextFormat(qd, has_entry_fmt)
            except ValueError:
                pass

    def _reload_recent_list(self, dates: list = None):
        self.recent_list.clear()
        dates = dates or sorted(self._entry_dates, reverse=True)[:30]
        for date_str in dates:
            item = QListWidgetItem(f"📄 {date_str}")
            item.setData(Qt.ItemDataRole.UserRole, date_str)
            # Highlight today
            if date_str == date.today().isoformat():
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor("#1565c0"))
            self.recent_list.addItem(item)

    def _reload_tags(self):
        current = self.tag_combo.currentData()
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem("— All entries —", "")
        for tag in self.db.get_all_tags():
            self.tag_combo.addItem(f"#{tag}", tag)
        # Restore selection
        idx = self.tag_combo.findData(current)
        if idx >= 0:
            self.tag_combo.setCurrentIndex(idx)
        self.tag_combo.blockSignals(False)

    def _on_calendar_click(self, qdate: QDate):
        date_str = f"{qdate.year():04d}-{qdate.month():02d}-{qdate.day():02d}"
        self.date_selected.emit(date_str)

    def _on_recent_click(self, item: QListWidgetItem):
        date_str = item.data(Qt.ItemDataRole.UserRole)
        if date_str:
            self.date_selected.emit(date_str)

    def _on_tag_filter(self):
        tag = self.tag_combo.currentData()
        if tag:
            dates = self.db.get_entries_by_tag(tag)
            self._reload_recent_list(dates)
        else:
            self._reload_recent_list()
