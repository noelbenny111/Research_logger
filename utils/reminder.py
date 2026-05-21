"""
Reminder system for Research Logger.
Uses Qt timers — no external scheduler needed.
"""
from datetime import datetime, time
from PySide6.QtCore import QTimer, QObject, Signal
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QPixmap, QColor


class ReminderManager(QObject):
    reminder_triggered = Signal()

    def __init__(self, main_window, db=None):
        super().__init__()
        self.main_window = main_window
        self.db = db or main_window.db
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_reminder)
        self._last_reminder_date = None

    def start(self):
        """Start the 60-second polling timer."""
        self._timer.start(60_000)  # check every minute

    def stop(self):
        self._timer.stop()

    def _check_reminder(self):
        enabled = self.db.get_setting("reminder_enabled", "true") == "true"
        if not enabled:
            return

        reminder_time_str = self.db.get_setting("reminder_time", "20:00")
        try:
            h, m = map(int, reminder_time_str.split(":"))
        except ValueError:
            return

        now = datetime.now()
        today = now.date()

        # Fire only once per day, within the minute window
        if (now.hour == h and now.minute == m and
                self._last_reminder_date != today):
            self._last_reminder_date = today
            self._fire_reminder()

    def _fire_reminder(self):
        """Show system notification + in-app dialog."""
        # Try system tray notification first
        tray = self.main_window.tray_icon
        if tray and tray.isVisible():
            tray.showMessage(
                "Research Logger",
                "⏰ Time to log today's research activity!",
                QSystemTrayIcon.MessageIcon.Information,
                8000
            )
        else:
            self._show_qt_reminder()

    def _show_qt_reminder(self):
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self.main_window)
        msg.setWindowTitle("Research Logger Reminder")
        msg.setText("⏰  Time to log today's research activity!")
        msg.setInformativeText("Open today's log entry now?")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Later
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.main_window.open_today()
