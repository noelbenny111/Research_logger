"""
Main editor panel: markdown text editor with auto-save and live preview toggle.
"""
import os
from datetime import date, datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QSplitter, QFrame, QSizePolicy, QStackedWidget,
    QToolBar
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import (
    QFont, QTextCharFormat, QColor, QSyntaxHighlighter,
    QTextDocument, QKeySequence, QAction
)

try:
    import markdown2
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


# ─── Markdown Syntax Highlighter ──────────────────────────────────────────────

class MarkdownHighlighter(QSyntaxHighlighter):
    """Lightweight syntax highlighter for Markdown."""

    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self._rules = []

        def _add(pattern, color, bold=False, italic=False):
            import re
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(700)
            if italic:
                fmt.setFontItalic(True)
            self._rules.append((re.compile(pattern), fmt))

        _add(r"^#{1,6}\s.+$",         "#1565c0", bold=True)   # headings
        _add(r"\*\*[^*]+\*\*",        "#000000", bold=True)   # bold
        _add(r"\*[^*]+\*",            "#555555", italic=True) # italic
        _add(r"`[^`]+`",              "#c62828")              # inline code
        _add(r"^```.*$",              "#c62828")              # code fence
        _add(r"^[-*+]\s",             "#2e7d32")              # list bullet
        _add(r"^\d+\.\s",             "#2e7d32")              # ordered list
        _add(r"<!--.*?-->",           "#9e9e9e", italic=True) # comment
        _add(r"\[([^\]]+)\]\([^\)]+\)", "#1976d2")           # link
        _add(r"^>\s.+$",              "#6d4c41", italic=True) # blockquote
        _add(r"^-{3,}$",              "#9e9e9e")              # hr

    def highlightBlock(self, text: str):
        import re
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


# ─── Editor Panel ─────────────────────────────────────────────────────────────

class EditorPanel(QWidget):
    content_changed = Signal()
    save_requested = Signal(str)  # emits current content

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._current_date: str = date.today().isoformat()
        self._dirty = False
        self._preview_mode = False
        self._use_webengine = False  # set properly in _build_ui

        self._build_ui()
        self._setup_autosave()

    # ─── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        topbar = QWidget()
        topbar.setObjectName("editorTopbar")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(12, 6, 12, 6)

        self.date_label = QLabel()
        self.date_label.setObjectName("dateLabel")
        topbar_layout.addWidget(self.date_label)
        topbar_layout.addStretch()

        self.preview_btn = QPushButton("👁 Preview")
        self.preview_btn.setCheckable(True)
        self.preview_btn.setFixedHeight(28)
        self.preview_btn.clicked.connect(self._toggle_preview)
        topbar_layout.addWidget(self.preview_btn)

        self.save_status = QLabel("✓ Saved")
        self.save_status.setObjectName("saveStatus")
        topbar_layout.addWidget(self.save_status)

        layout.addWidget(topbar)

        # Stacked widget: editor / preview
        self.stack = QStackedWidget()

        # ── Markdown editor ───────────────────────────────────────────────────
        self.editor = QTextEdit()
        self.editor.setObjectName("mainEditor")
        font = QFont("Consolas", 11) if os.name == "nt" else QFont("Monospace", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.editor.setFont(font)
        self.editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.editor.setAcceptDrops(True)
        self.editor.textChanged.connect(self._on_text_changed)
        self._highlighter = MarkdownHighlighter(self.editor.document())
        self.stack.addWidget(self.editor)

        # ── HTML preview (WebEngine preferred, QTextBrowser fallback) ─────────
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self.preview = QWebEngineView()
            self._use_webengine = True
        except (ImportError, Exception):
            from PySide6.QtWidgets import QTextBrowser
            self.preview = QTextBrowser()
            self.preview.setOpenExternalLinks(True)
            self._use_webengine = False
        self.stack.addWidget(self.preview)

        layout.addWidget(self.stack)

    def _setup_autosave(self):
        interval_s = int(self.db.get_setting("auto_save_interval", "10"))
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(interval_s * 1000)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()

    # ─── Public API ────────────────────────────────────────────────────────────

    def load_entry(self, entry_date: str, content: str):
        self._current_date = entry_date
        self._dirty = False
        # Update date label
        try:
            d = datetime.strptime(entry_date, "%Y-%m-%d")
            self.date_label.setText(d.strftime("📓  %A, %B %d, %Y"))
        except ValueError:
            self.date_label.setText(f"📓  {entry_date}")

        # Block signals to avoid triggering _on_text_changed
        self.editor.blockSignals(True)
        self.editor.setPlainText(content)
        self.editor.blockSignals(False)
        self._set_save_status(True)

    def get_content(self) -> str:
        return self.editor.toPlainText()

    def insert_text(self, text: str):
        cursor = self.editor.textCursor()
        cursor.insertText(text)
        self.editor.setFocus()

    # ─── Internal ──────────────────────────────────────────────────────────────

    def _on_text_changed(self):
        self._dirty = True
        self._set_save_status(False)
        self.content_changed.emit()

    def _set_save_status(self, saved: bool):
        if saved:
            self.save_status.setText("✓ Saved")
            self.save_status.setStyleSheet("color: #2e7d32;")
        else:
            self.save_status.setText("● Unsaved")
            self.save_status.setStyleSheet("color: #e65100;")

    def _autosave(self):
        if self._dirty:
            self.save_requested.emit(self.editor.toPlainText())
            self._dirty = False
            self._set_save_status(True)

    def _toggle_preview(self, checked: bool):
        if checked:
            self._render_preview()
            self.stack.setCurrentIndex(1)
            self.preview_btn.setText("✏️ Edit")
        else:
            self.stack.setCurrentIndex(0)
            self.preview_btn.setText("👁 Preview")

    def _render_preview(self):
        md_text = self.editor.toPlainText()
        if HAS_MARKDOWN:
            body = markdown2.markdown(
                md_text,
                extras=["fenced-code-blocks", "tables", "strike", "task_list"]
            )
        else:
            # Minimal fallback
            import re
            body = "<pre>" + md_text.replace("<", "&lt;").replace(">", "&gt;") + "</pre>"

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          font-size: 15px; line-height: 1.7; max-width: 800px;
          margin: 30px auto; color: #222; padding: 0 20px; }}
  h1 {{ color: #1565c0; border-bottom: 2px solid #dce9ff; padding-bottom: 6px; }}
  h2 {{ color: #16213e; }}
  h3 {{ color: #0f3460; }}
  code {{ background: #f5f5f5; padding: 2px 5px; border-radius: 3px; font-size: 0.9em; }}
  pre  {{ background: #f5f5f5; padding: 14px; border-radius: 5px; overflow-x: auto; }}
  blockquote {{ border-left: 4px solid #90caf9; margin: 0; padding-left: 14px; color: #555; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
  th {{ background-color: #f0f4ff; }}
  hr {{ border: none; border-top: 1px solid #ddd; }}
</style>
</head>
<body>{body}</body>
</html>"""
        if self._use_webengine:
            self.preview.setHtml(html)
        else:
            # QTextBrowser: render HTML directly (limited CSS support)
            self.preview.setHtml(html)
