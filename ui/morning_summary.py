"""
Morning summary popup — shown when app starts in the morning.
Displays what was written yesterday and the "Plan for Tomorrow".
"""
from datetime import date, timedelta
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFrame, QSplitter, QWidget
)
from PySide6.QtCore import Qt


class MorningSummaryDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("🌅 Good Morning — Yesterday's Summary")
        self.resize(680, 460)
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        greeting = QLabel()
        greeting.setObjectName("morningGreeting")
        today = date.today()
        yesterday = today - timedelta(days=1)
        greeting.setText(
            f"<b>Good morning! 🌤</b> &nbsp; Today is {today.strftime('%A, %B %d')}. "
            f"Here's a recap of yesterday ({yesterday.strftime('%B %d')}):"
        )
        greeting.setWordWrap(True)
        layout.addWidget(greeting)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: yesterday summary
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("📋 <b>What You Worked On</b>"))
        self.worked_text = QTextEdit()
        self.worked_text.setReadOnly(True)
        self.worked_text.setObjectName("morningSummaryBox")
        left_layout.addWidget(self.worked_text)
        splitter.addWidget(left)

        # Right: plan for tomorrow
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("🎯 <b>Plan for Today (from yesterday)</b>"))
        self.plan_text = QTextEdit()
        self.plan_text.setReadOnly(True)
        self.plan_text.setObjectName("morningSummaryBox")
        right_layout.addWidget(self.plan_text)
        splitter.addWidget(right)

        layout.addWidget(splitter)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        open_today_btn = QPushButton("📓 Open Today's Log")
        open_today_btn.setDefault(True)
        open_today_btn.clicked.connect(self.accept)
        btn_row.addWidget(open_today_btn)
        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.clicked.connect(self.reject)
        btn_row.addWidget(dismiss_btn)
        layout.addLayout(btn_row)

    def _load(self):
        import re
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        entry = self.db.get_entry(yesterday)

        if not entry or not entry.get("content"):
            self.worked_text.setPlainText("No entry found for yesterday.")
            self.plan_text.setPlainText("—")
            return

        content = entry["content"]

        # Extract "What I Worked On Today" section
        def extract_section(header: str) -> str:
            pattern = rf"##\s+{re.escape(header)}\s*\n(.*?)(?=##|\Z)"
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1).strip()
                # Remove template comments
                text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()
                return text if text else "—"
            return "—"

        worked = extract_section("What I Worked On Today")
        results = extract_section("Experiments / Results")
        plan = extract_section("Plan for Tomorrow")

        summary = ""
        if worked and worked != "—":
            summary += worked
        if results and results != "—":
            summary += f"\n\nResults:\n{results}"

        self.worked_text.setPlainText(summary if summary else "Nothing recorded.")
        self.plan_text.setPlainText(plan)
