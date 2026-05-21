"""
Settings dialog: reminder time, auto-save interval, theme.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QCheckBox, QSpinBox, QComboBox, QPushButton,
    QGroupBox, QTimeEdit
)
from PySide6.QtCore import Qt, QTime


class SettingsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("⚙️ Settings")
        self.setFixedSize(400, 380)
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # ── Reminder ──────────────────────────────────────────────────────────
        reminder_group = QGroupBox("⏰ Daily Reminder")
        reminder_form = QFormLayout(reminder_group)

        self.reminder_enabled = QCheckBox("Enable daily reminder")
        reminder_form.addRow(self.reminder_enabled)

        self.reminder_time = QTimeEdit()
        self.reminder_time.setDisplayFormat("HH:mm")
        reminder_form.addRow("Reminder time:", self.reminder_time)

        layout.addWidget(reminder_group)

        # ── Editor ────────────────────────────────────────────────────────────
        editor_group = QGroupBox("✏️ Editor")
        editor_form = QFormLayout(editor_group)

        self.autosave_interval = QSpinBox()
        self.autosave_interval.setRange(5, 120)
        self.autosave_interval.setSuffix(" seconds")
        editor_form.addRow("Auto-save every:", self.autosave_interval)

        self.morning_summary = QCheckBox("Show morning summary on startup")
        editor_form.addRow(self.morning_summary)

        layout.addWidget(editor_group)

        # ── Appearance ────────────────────────────────────────────────────────
        appear_group = QGroupBox("🎨 Appearance")
        appear_form = QFormLayout(appear_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        appear_form.addRow("Theme:", self.theme_combo)

        layout.addWidget(appear_group)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _load_settings(self):
        enabled = self.db.get_setting("reminder_enabled", "true") == "true"
        self.reminder_enabled.setChecked(enabled)

        time_str = self.db.get_setting("reminder_time", "20:00")
        try:
            h, m = map(int, time_str.split(":"))
            self.reminder_time.setTime(QTime(h, m))
        except ValueError:
            self.reminder_time.setTime(QTime(20, 0))

        interval = int(self.db.get_setting("auto_save_interval", "10"))
        self.autosave_interval.setValue(interval)

        morning = self.db.get_setting("morning_summary", "true") == "true"
        self.morning_summary.setChecked(morning)

        theme = self.db.get_setting("theme", "light")
        idx = self.theme_combo.findText(theme.capitalize())
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

    def _save_settings(self):
        self.db.set_setting("reminder_enabled", "true" if self.reminder_enabled.isChecked() else "false")
        t = self.reminder_time.time()
        self.db.set_setting("reminder_time", f"{t.hour():02d}:{t.minute():02d}")
        self.db.set_setting("auto_save_interval", str(self.autosave_interval.value()))
        self.db.set_setting("morning_summary", "true" if self.morning_summary.isChecked() else "false")
        self.db.set_setting("theme", self.theme_combo.currentText().lower())
        self.accept()
