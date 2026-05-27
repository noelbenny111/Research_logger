"""
Claude assistant dialog for Research Logger.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel,
    QMessageBox, QComboBox, QPlainTextEdit
)

from utils.claude import ask_claude
from utils.richtext import content_to_plain_text


PROMPTS = {
    "Summarize": "Summarize the following notes in a concise, useful way.",
    "Polish": "Rewrite the following notes into clearer, well-structured prose.",
    "Extract tasks": "Extract concrete action items and next steps from the following notes.",
    "Ask custom": "Use the prompt below to guide your response.",
}


class ClaudeDialog(QDialog):
    def __init__(self, db, entry_text: str = "", selection_text: str = "", parent=None):
        super().__init__(parent)
        self.db = db
        self.entry_text = entry_text or ""
        self.selection_text = selection_text or ""
        self.response_text = ""
        self.setWindowTitle("🤖 Claude Assistant")
        self.resize(760, 640)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(PROMPTS.keys())
        self.mode_combo.currentTextChanged.connect(self._update_prompt_hint)
        layout.addWidget(self.mode_combo)

        self.prompt_hint = QLabel()
        self.prompt_hint.setWordWrap(True)
        layout.addWidget(self.prompt_hint)

        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText("Add extra instructions for Claude here...")
        layout.addWidget(self.prompt_edit)

        layout.addWidget(QLabel("Context sent to Claude:"))
        self.context_preview = QTextEdit()
        self.context_preview.setReadOnly(True)
        self.context_preview.setPlainText(self._compose_context_preview())
        layout.addWidget(self.context_preview, 1)

        layout.addWidget(QLabel("Response:"))
        self.response_view = QTextEdit()
        self.response_view.setReadOnly(True)
        layout.addWidget(self.response_view, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ask_btn = QPushButton("Ask Claude")
        ask_btn.clicked.connect(self._ask_claude)
        insert_btn = QPushButton("Insert into Editor")
        insert_btn.clicked.connect(self._accept_response)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(ask_btn)
        btn_row.addWidget(insert_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._update_prompt_hint(self.mode_combo.currentText())

    def _compose_context_preview(self) -> str:
        pieces = []
        if self.selection_text.strip():
            pieces.append("Selected text:\n" + self.selection_text.strip())
        if self.entry_text.strip():
            pieces.append("Full entry text:\n" + content_to_plain_text(self.entry_text).strip())
        return "\n\n---\n\n".join(pieces) or "No context available."

    def _build_prompt(self) -> str:
        mode = self.mode_combo.currentText()
        base = PROMPTS.get(mode, "Use the context below.")
        extra = self.prompt_edit.toPlainText().strip()
        context = self.selection_text.strip() or content_to_plain_text(self.entry_text).strip()
        prompt_parts = [base]
        if extra:
            prompt_parts.append(extra)
        prompt_parts.append("Context:\n" + context)
        return "\n\n".join(prompt_parts).strip()

    def _update_prompt_hint(self, mode: str):
        self.prompt_hint.setText(PROMPTS.get(mode, ""))

    def _ask_claude(self):
        if self.db.get_setting("claude_enabled", "false") != "true":
            QMessageBox.information(self, "Claude", "Claude is disabled in settings.")
            return

        api_key = self.db.get_setting("claude_api_key", "").strip()
        model = self.db.get_setting("claude_model", "claude-3-5-sonnet-20240620").strip()
        if not api_key:
            QMessageBox.warning(self, "Claude", "Set your Claude API key in Settings first.")
            return

        prompt = self._build_prompt()
        self.response_view.setPlainText("Thinking...")
        try:
            response = ask_claude(api_key, model, prompt)
        except Exception as exc:
            QMessageBox.critical(self, "Claude Error", str(exc))
            self.response_view.clear()
            return

        self.response_view.setPlainText(response)

    def _accept_response(self):
        text = self.response_view.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Claude", "Ask Claude first.")
            return
        self.response_text = text
        self.accept()