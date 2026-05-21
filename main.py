"""
Research Logger — Main entry point.

A lightweight digital lab notebook for daily research logging.
Run with:  python main.py
"""
import sys
import os
from datetime import datetime

# Ensure the project root is on the path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QFont

from database.db_manager import DatabaseManager
from ui.main_window import MainWindow
from utils.reminder import ReminderManager


def load_stylesheet(app: QApplication, db: DatabaseManager) -> None:
    theme = db.get_setting("theme", "light")
    base_dir = os.path.dirname(__file__)
    if theme == "dark":
        qss_path = os.path.join(base_dir, "styles_dark.qss")
    else:
        qss_path = os.path.join(base_dir, "styles.qss")
    try:
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass


def main():
    # HiDPI support
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Research Logger")
    app.setApplicationDisplayName("🔬 Research Logger")
    app.setOrganizationName("ResearchLogger")

    # Font
    font = QFont("Segoe UI", 10) if sys.platform == "win32" else QFont("SF Pro Display", 10)
    app.setFont(font)

    # Database
    db = DatabaseManager()

    # Stylesheet
    load_stylesheet(app, db)

    # Main window
    window = MainWindow(db)
    window.show()

    # Show morning summary (if 6–11 AM)
    hour = datetime.now().hour
    if 6 <= hour <= 11:
        # Slight delay so window is fully rendered first
        from PySide6.QtCore import QTimer
        QTimer.singleShot(800, window.show_morning_summary)

    # Reminder system
    reminder = ReminderManager(window, db)
    reminder.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
