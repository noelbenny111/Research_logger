"""
Main window for Research Logger.
Coordinates: sidebar, editor, attachments panel, toolbar.
"""
import os
import sys
from datetime import date, datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QToolBar, QStatusBar, QSplitter, QLabel,
    QLineEdit, QFileDialog, QMessageBox, QSystemTrayIcon,
    QMenu, QInputDialog, QApplication, QFrame
)
from PySide6.QtCore import Qt, QSize, Signal, QTimer
from PySide6.QtGui import (
    QAction, QIcon, QPixmap, QColor, QFont, QKeySequence
)

from ui.sidebar import SidebarWidget
from ui.rich_editor_panel import EditorPanel
from ui.attachments_panel import AttachmentsPanel
from utils.templates import daily_template


# ─── Minimal inline icon helper ───────────────────────────────────────────────

def _color_icon(color_hex: str, size: int = 18) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(QColor(color_hex))
    return QIcon(pix)


# ─── Main Window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._current_date = date.today().isoformat()
        self.tray_icon = None

        self.setWindowTitle("🔬 Research Logger")
        self.setMinimumSize(1100, 700)
        self.resize(1300, 800)

        self._build_toolbar()
        self._build_central()
        self._build_status_bar()
        self._build_tray()

        # Load today on startup
        self.open_today()

        # Tags bottom bar
        self._setup_tag_bar()

    # ─── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setObjectName("mainToolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        # Today
        act_today = QAction("📅 Today", self)
        act_today.setShortcut(QKeySequence("Ctrl+T"))
        act_today.setStatusTip("Open today's log (Ctrl+T)")
        act_today.triggered.connect(self.open_today)
        tb.addAction(act_today)

        tb.addSeparator()

        # New entry
        act_new = QAction("📝 New Entry", self)
        act_new.setShortcut(QKeySequence("Ctrl+N"))
        act_new.setStatusTip("Create a new entry for a date (Ctrl+N)")
        act_new.triggered.connect(self._new_entry)
        tb.addAction(act_new)

        tb.addSeparator()

        # Search
        act_search = QAction("🔍 Search", self)
        act_search.setShortcut(QKeySequence("Ctrl+F"))
        act_search.setStatusTip("Search all logs (Ctrl+F)")
        act_search.triggered.connect(self._open_search)
        tb.addAction(act_search)

        tb.addSeparator()

        # Summary
        act_summary = QAction("📊 Summary", self)
        act_summary.setStatusTip("View weekly/monthly summaries")
        act_summary.triggered.connect(self._open_summary)
        tb.addAction(act_summary)

        tb.addSeparator()

        # Export
        act_export = QAction("📥 Export PDF", self)
        act_export.setShortcut(QKeySequence("Ctrl+E"))
        act_export.setStatusTip("Export current entry to PDF (Ctrl+E)")
        act_export.triggered.connect(self._export_current)
        tb.addAction(act_export)

        tb.addSeparator()

        # Settings
        act_settings = QAction("⚙️ Settings", self)
        act_settings.triggered.connect(self._open_settings)
        tb.addAction(act_settings)

        # Stretch spacer
        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().horizontalPolicy(),
            spacer.sizePolicy().verticalPolicy()
        )
        from PySide6.QtWidgets import QSizePolicy
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        # Current date display
        self.toolbar_date_label = QLabel()
        self.toolbar_date_label.setObjectName("toolbarDate")
        tb.addWidget(self.toolbar_date_label)
        self._update_toolbar_date()

        # Update date every minute
        date_timer = QTimer(self)
        date_timer.timeout.connect(self._update_toolbar_date)
        date_timer.start(60_000)

    def _update_toolbar_date(self):
        self.toolbar_date_label.setText(
            f"  {datetime.now().strftime('%a, %b %d  |  %H:%M')}  "
        )

    # ─── Central widget ────────────────────────────────────────────────────────

    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main splitter: sidebar | editor | attachments
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.sidebar = SidebarWidget(self.db, self)
        self.sidebar.date_selected.connect(self._load_entry_for_date)
        self.splitter.addWidget(self.sidebar)

        # Editor + tag bar in a column
        editor_container = QWidget()
        editor_vbox = QVBoxLayout(editor_container)
        editor_vbox.setContentsMargins(0, 0, 0, 0)
        editor_vbox.setSpacing(0)

        self.editor = EditorPanel(self.db, self)
        self.editor.save_requested.connect(self._do_save)
        self.editor.content_changed.connect(self._on_content_changed)
        editor_vbox.addWidget(self.editor)

        # Tag input bar (bottom of editor)
        self.tag_bar = self._create_tag_bar()
        editor_vbox.addWidget(self.tag_bar)

        self.splitter.addWidget(editor_container)

        self.attachments = AttachmentsPanel(self.db, self)
        self.attachments.attachment_added.connect(self.editor.insert_html)
        self.splitter.addWidget(self.attachments)

        self.splitter.setSizes([260, 800, 230])
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(2, True)

        layout.addWidget(self.splitter)

    def _create_tag_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("tagBar")
        bar.setFixedHeight(36)
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 4, 12, 4)
        h.setSpacing(8)
        h.addWidget(QLabel("🏷 Tags:"))
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("comma-separated tags  (e.g. ml, experiment, paper-review)")
        self.tag_input.setFixedHeight(26)
        self.tag_input.editingFinished.connect(self._save_tags)
        h.addWidget(self.tag_input)
        return bar

    def _setup_tag_bar(self):
        pass  # tag_bar already built in _build_central

    # ─── Status bar ────────────────────────────────────────────────────────────

    def _build_status_bar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    # ─── System Tray ───────────────────────────────────────────────────────────

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        pix = QPixmap(16, 16)
        pix.fill(QColor("#1565c0"))
        self.tray_icon = QSystemTrayIcon(QIcon(pix), self)
        self.tray_icon.setToolTip("Research Logger")

        menu = QMenu()
        act_show = menu.addAction("Show Window")
        act_show.triggered.connect(self.show_and_raise)
        act_today = menu.addAction("Open Today")
        act_today.triggered.connect(self.open_today)
        menu.addSeparator()
        act_quit = menu.addAction("Quit")
        act_quit.triggered.connect(QApplication.quit)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_and_raise()

    def show_and_raise(self):
        self.show()
        self.activateWindow()
        self.raise_()

    # ─── Entry loading ─────────────────────────────────────────────────────────

    def open_today(self):
        self._load_entry_for_date(date.today().isoformat())

    def _load_entry_for_date(self, entry_date: str):
        # Auto-save current entry first
        if self._current_date:
            self._do_save(self.editor.get_content())

        self._current_date = entry_date
        entry = self.db.get_or_create_entry(entry_date, daily_template(entry_date))
        self.editor.load_entry(entry_date, entry["content"])
        self.attachments.load_attachments(entry_date, entry.get("attachments", []))
        self.sidebar.set_current_date(entry_date)

        # Load tags
        tags = entry.get("tags") or self.db.get_entry_tags(entry.get("id", -1)) or []
        self.tag_input.setText(", ".join(tags))

        self.status.showMessage(f"Loaded: {entry_date}", 3000)

    def _on_content_changed(self):
        pass  # handled by autosave

    def _do_save(self, content: str):
        if not self._current_date:
            return
        self.db.save_entry(self._current_date, content)
        self.sidebar.refresh()
        self.status.showMessage(f"Saved {self._current_date}", 2000)

    def _save_tags(self):
        raw = self.tag_input.text()
        tags = [t.strip() for t in raw.split(",") if t.strip()]
        self.db.set_entry_tags(self._current_date, tags)
        self.sidebar.refresh()

    # ─── Toolbar actions ───────────────────────────────────────────────────────

    def _new_entry(self):
        from PySide6.QtWidgets import QDialog, QCalendarWidget, QDialogButtonBox, QVBoxLayout
        from PySide6.QtCore import QDate
        dlg = QDialog(self)
        dlg.setWindowTitle("Pick Date for New Entry")
        dlg.setFixedSize(320, 280)
        v = QVBoxLayout(dlg)
        cal = QCalendarWidget()
        cal.setSelectedDate(QDate.currentDate())
        v.addWidget(cal)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        v.addWidget(btns)
        if dlg.exec():
            qd = cal.selectedDate()
            date_str = f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}"
            self._load_entry_for_date(date_str)

    def _open_search(self):
        from ui.search_dialog import SearchDialog
        dlg = SearchDialog(self.db, self)
        dlg.entry_selected.connect(self._load_entry_for_date)
        dlg.exec()

    def _open_summary(self):
        from ui.summary_dialog import SummaryDialog
        dlg = SummaryDialog(self.db, self)
        dlg.exec()

    def _export_current(self):
        from utils.exporter import export_entry_to_pdf
        # Save first
        self._do_save(self.editor.get_content())
        entry = self.db.get_entry(self._current_date)
        if not entry:
            QMessageBox.warning(self, "Export", "No entry to export.")
            return
        default_name = f"research_log_{self._current_date}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Entry to PDF", default_name, "PDF Files (*.pdf)"
        )
        if not path:
            return
        ok = export_entry_to_pdf(entry, path)
        if ok:
            QMessageBox.information(self, "Export Complete", f"PDF saved:\n{path}")
        else:
            QMessageBox.warning(self, "Export Failed",
                                "Could not generate PDF.\nMake sure reportlab is installed.")

    def _open_settings(self):
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.db, self)
        dlg.exec()

    # ─── Morning summary ───────────────────────────────────────────────────────

    def show_morning_summary(self):
        enabled = self.db.get_setting("morning_summary", "true") == "true"
        if not enabled:
            return
        # Check if yesterday had an entry
        from datetime import timedelta
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        entry = self.db.get_entry(yesterday)
        if not entry:
            return
        from ui.morning_summary import MorningSummaryDialog
        dlg = MorningSummaryDialog(self.db, self)
        if dlg.exec():
            self.open_today()

    # ─── Close event ───────────────────────────────────────────────────────────

    def closeEvent(self, event):
        # Save on close
        self._do_save(self.editor.get_content())
        self._save_tags()
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            self.db.close()
            event.accept()
