"""
Summary dialog: display and export weekly/monthly summaries.
"""
import os
from datetime import date, timedelta
import calendar as cal_module

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTextEdit, QFrame, QFileDialog, QMessageBox,
    QTabWidget, QWidget, QSpinBox
)
from PySide6.QtCore import Qt


class SummaryDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("📊 Research Summaries")
        self.resize(700, 560)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.tabs = QTabWidget()

        # ── Weekly tab ────────────────────────────────────────────────────────
        weekly_widget = QWidget()
        weekly_layout = QVBoxLayout(weekly_widget)

        wctrl = QHBoxLayout()
        wctrl.addWidget(QLabel("Show week of:"))
        self.week_offset = QSpinBox()
        self.week_offset.setRange(-52, 0)
        self.week_offset.setValue(0)
        self.week_offset.setSuffix(" weeks ago")
        self.week_offset.valueChanged.connect(self._load_weekly)
        wctrl.addWidget(self.week_offset)
        wctrl.addStretch()
        export_weekly_btn = QPushButton("📥 Export PDF")
        export_weekly_btn.clicked.connect(lambda: self._export("weekly"))
        wctrl.addWidget(export_weekly_btn)
        weekly_layout.addLayout(wctrl)

        self.weekly_text = QTextEdit()
        self.weekly_text.setReadOnly(True)
        self.weekly_text.setObjectName("summaryText")
        weekly_layout.addWidget(self.weekly_text)

        self.tabs.addTab(weekly_widget, "📅 Weekly")

        # ── Monthly tab ───────────────────────────────────────────────────────
        monthly_widget = QWidget()
        monthly_layout = QVBoxLayout(monthly_widget)

        mctrl = QHBoxLayout()
        mctrl.addWidget(QLabel("Month:"))
        self.month_combo = QComboBox()
        for m in range(1, 13):
            self.month_combo.addItem(cal_module.month_name[m], m)
        today = date.today()
        self.month_combo.setCurrentIndex(today.month - 1)
        self.month_combo.currentIndexChanged.connect(self._load_monthly)
        mctrl.addWidget(self.month_combo)

        mctrl.addWidget(QLabel("Year:"))
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(today.year)
        self.year_spin.valueChanged.connect(self._load_monthly)
        mctrl.addWidget(self.year_spin)
        mctrl.addStretch()
        export_monthly_btn = QPushButton("📥 Export PDF")
        export_monthly_btn.clicked.connect(lambda: self._export("monthly"))
        mctrl.addWidget(export_monthly_btn)
        monthly_layout.addLayout(mctrl)

        self.monthly_text = QTextEdit()
        self.monthly_text.setReadOnly(True)
        self.monthly_text.setObjectName("summaryText")
        monthly_layout.addWidget(self.monthly_text)

        self.tabs.addTab(monthly_widget, "📆 Monthly")

        layout.addWidget(self.tabs)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        hrow = QHBoxLayout()
        hrow.addStretch()
        hrow.addWidget(close_btn)
        layout.addLayout(hrow)

        # Load initial summaries
        self._load_weekly()
        self._load_monthly()

    def _load_weekly(self):
        from utils.summarizer import build_weekly_summary
        today = date.today()
        offset_weeks = abs(self.week_offset.value())
        end = today - timedelta(weeks=offset_weeks)
        # Go to end of that week (Sunday)
        start = end - timedelta(days=end.weekday())
        end = start + timedelta(days=6)
        if end > today:
            end = today

        entries = self.db.get_entries_in_range(start.isoformat(), end.isoformat())
        if not entries:
            self.weekly_text.setPlainText("No entries found for this week.")
            return

        summary = build_weekly_summary(entries)
        header = f"Weekly Summary: {start.isoformat()} → {end.isoformat()}\n{'='*50}\n\n"
        self.weekly_text.setPlainText(header + summary)
        self._weekly_range = (start.isoformat(), end.isoformat())

    def _load_monthly(self):
        from utils.summarizer import build_monthly_summary
        month = self.month_combo.currentData()
        year = self.year_spin.value()

        _, last_day = cal_module.monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, last_day)

        entries = self.db.get_entries_in_range(start.isoformat(), end.isoformat())
        if not entries:
            self.monthly_text.setPlainText("No entries found for this month.")
            return

        summary = build_monthly_summary(entries, year, month)
        self.monthly_text.setPlainText(summary)
        self._monthly_info = (year, month)

    def _export(self, mode: str):
        from utils.exporter import export_summary_to_pdf
        if mode == "weekly":
            text = self.weekly_text.toPlainText()
            start, end = getattr(self, "_weekly_range", ("", ""))
            default_name = f"weekly_summary_{start}_{end}.pdf"
            title = f"Weekly Research Summary\n{start} → {end}"
        else:
            text = self.monthly_text.toPlainText()
            year, month = getattr(self, "_monthly_info", (date.today().year, date.today().month))
            import calendar as cm
            default_name = f"monthly_summary_{year}_{cm.month_name[month]}.pdf"
            title = f"Monthly Summary — {cm.month_name[month]} {year}"

        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", default_name, "PDF Files (*.pdf)"
        )
        if not path:
            return

        ok = export_summary_to_pdf(title, text, path)
        if ok:
            QMessageBox.information(self, "Export Complete", f"PDF saved to:\n{path}")
        else:
            QMessageBox.warning(self, "Export Failed", "Could not generate PDF. Check reportlab is installed.")
