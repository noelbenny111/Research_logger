"""
Rich-text editor panel for Research Logger.
"""
from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import (
    QAction, QColor, QFont, QGuiApplication, QImage, QTextCharFormat,
    QTextCursor, QTextDocument, QTextImageFormat, QTextListFormat,
    QTextTableFormat, QKeySequence
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QToolBar,
    QPushButton, QComboBox, QColorDialog, QInputDialog, QSpinBox
)

from utils.richtext import looks_like_html


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


class RichTextEdit(QTextEdit):
    """QTextEdit that pastes clipboard images into the entry attachments folder."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._current_date = date.today().isoformat()

    def set_entry_date(self, entry_date: str):
        self._current_date = entry_date

    def _insert_image_path(self, image_path: Path):
        cursor = self.textCursor()
        image_format = QTextImageFormat()
        image_format.setName(image_path.as_uri())
        cursor.insertImage(image_format)

    def _image_path_at_cursor(self, cursor: QTextCursor) -> Path | None:
        image_format = cursor.charFormat().toImageFormat()
        if not image_format.isValid():
            return None
        name = image_format.name().strip()
        if not name:
            return None
        if name.startswith("file:///"):
            from urllib.parse import unquote, urlparse
            parsed = urlparse(name)
            if parsed.path:
                return Path(unquote(parsed.path.lstrip("/")))
        return Path(name)

    def _reload_document_html(self):
        html = self.toHtml()
        self.blockSignals(True)
        self.setHtml(html)
        self.blockSignals(False)

    def _apply_image_edit(self, image_path: Path, mode: str, width: int, height: int, keep_ratio: bool):
        from PIL import Image

        with Image.open(image_path) as img:
            if mode == "Crop to square":
                side = min(img.width, img.height)
                left = max(0, (img.width - side) // 2)
                top = max(0, (img.height - side) // 2)
                edited = img.crop((left, top, left + side, top + side))
            else:
                target_width = max(1, width)
                target_height = max(1, height)
                if keep_ratio:
                    ratio = min(target_width / max(img.width, 1), target_height / max(img.height, 1))
                    target_width = max(1, round(img.width * ratio))
                    target_height = max(1, round(img.height * ratio))
                edited = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            edited.save(image_path)

        self._reload_document_html()

    def _save_clipboard_image(self, image: QImage) -> Path:
        from ui.attachments_panel import save_inline_image

        return save_inline_image(self._current_date, image)

    def _transform_saved_image(self, image_path: Path):
        from PIL import Image

        choice, ok = QInputDialog.getItem(
            self,
            "Paste Image",
            "How should the pasted image be inserted?",
            ["Original size", "Resize to width...", "Crop to square"],
            0,
            False,
        )
        if not ok:
            return

        if choice == "Resize to width...":
            width, ok = QInputDialog.getInt(
                self,
                "Resize Image",
                "Target width (px):",
                640,
                64,
                4000,
                1,
            )
            if not ok:
                return
            with Image.open(image_path) as img:
                ratio = width / max(img.width, 1)
                new_height = max(1, round(img.height * ratio))
                resized = img.resize((width, new_height), Image.Resampling.LANCZOS)
                resized.save(image_path)
            return

        if choice == "Crop to square":
            with Image.open(image_path) as img:
                side = min(img.width, img.height)
                left = (img.width - side) // 2
                top = (img.height - side) // 2
                cropped = img.crop((left, top, left + side, top + side))
                cropped.save(image_path)

    def canInsertFromMimeData(self, source):
        if source.hasImage() or source.hasUrls():
            return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage) and not image.isNull():
                saved = self._save_clipboard_image(image)
                self._transform_saved_image(saved)
                self._insert_image_path(saved)
                return

        if source.hasUrls():
            handled = False
            for url in source.urls():
                if not url.isLocalFile():
                    continue
                path = Path(url.toLocalFile())
                if path.suffix.lower() in IMAGE_EXTENSIONS:
                    self._insert_image_path(path)
                    handled = True
            if handled:
                return

        super().insertFromMimeData(source)

    def contextMenuEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        image_path = self._image_path_at_cursor(cursor)

        menu = self.createStandardContextMenu(event.pos())
        image_action = None
        if image_path and image_path.exists():
            menu.addSeparator()
            image_action = menu.addAction("🖼 Image Properties...")

        action = menu.exec(event.globalPos())
        if image_action and action == image_action:
            self._edit_inline_image(image_path)

    def _edit_inline_image(self, image_path: Path):
        from PIL import Image
        from ui.image_properties_dialog import ImagePropertiesDialog

        try:
            with Image.open(image_path) as img:
                width, height = img.size
        except Exception:
            return

        dlg = ImagePropertiesDialog(image_path.name, width, height, self)
        if not dlg.exec():
            return

        data = dlg.result_data()
        self._apply_image_edit(
            image_path,
            data["mode"],
            data["width"],
            data["height"],
            data["keep_ratio"],
        )


class EditorPanel(QWidget):
    content_changed = Signal()
    save_requested = Signal(str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._current_date = date.today().isoformat()
        self._dirty = False

        self._build_ui()
        self._setup_autosave()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        topbar = QWidget()
        topbar.setObjectName("editorTopbar")
        topbar_layout = QVBoxLayout(topbar)
        topbar_layout.setContentsMargins(12, 6, 12, 6)
        topbar_layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        self.date_label = QLabel()
        self.date_label.setObjectName("dateLabel")
        header_row.addWidget(self.date_label)
        header_row.addStretch()
        self.save_status = QLabel("✓ Saved")
        self.save_status.setObjectName("saveStatus")
        header_row.addWidget(self.save_status)
        topbar_layout.addLayout(header_row)

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        topbar_layout.addWidget(self.toolbar)

        self._build_toolbar_actions()
        layout.addWidget(topbar)

        self.editor = RichTextEdit(self.db)
        self.editor.setObjectName("mainEditor")
        font = QFont("Segoe UI", 11) if os.name == "nt" else QFont("Sans Serif", 11)
        self.editor.setFont(font)
        self.editor.setFontPointSize(int(self.db.get_setting("editor_font_size", "11")))
        self.editor.setAcceptRichText(True)
        self.editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.editor)

    def _build_toolbar_actions(self):
        bold_act = QAction("Bold", self)
        bold_act.setShortcut(QKeySequence.StandardKey.Bold)
        bold_act.triggered.connect(self._toggle_bold)
        self.toolbar.addAction(bold_act)

        italic_act = QAction("Italic", self)
        italic_act.setShortcut(QKeySequence.StandardKey.Italic)
        italic_act.triggered.connect(self._toggle_italic)
        self.toolbar.addAction(italic_act)

        bullet_act = QAction("Bullets", self)
        bullet_act.triggered.connect(self._insert_bullet_list)
        self.toolbar.addAction(bullet_act)

        number_act = QAction("Numbered", self)
        number_act.triggered.connect(self._insert_numbered_list)
        self.toolbar.addAction(number_act)

        self.toolbar.addSeparator()

        self.heading_combo = QComboBox()
        self.heading_combo.addItems(["Body", "H1", "H2", "H3"])
        self.heading_combo.currentIndexChanged.connect(self._apply_heading_style)
        self.toolbar.addWidget(self.heading_combo)

        color_act = QAction("Text Color", self)
        color_act.triggered.connect(self._choose_text_color)
        self.toolbar.addAction(color_act)

        self.toolbar.addSeparator()

        self.toolbar.addWidget(QLabel("Font size"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 32)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setValue(int(self.db.get_setting("editor_font_size", "11")))
        self.font_size_spin.valueChanged.connect(self._apply_font_size)
        self.toolbar.addWidget(self.font_size_spin)

        table_act = QAction("Table", self)
        table_act.triggered.connect(self._insert_table)
        self.toolbar.addAction(table_act)

        self.toolbar.addSeparator()

        force_html_act = QAction("Use Rich Text", self)
        force_html_act.triggered.connect(self._ensure_rich_text_mode)
        self.toolbar.addAction(force_html_act)

    def _setup_autosave(self):
        interval_s = int(self.db.get_setting("auto_save_interval", "10"))
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(interval_s * 1000)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()

    def load_entry(self, entry_date: str, content: str):
        self._current_date = entry_date
        self.editor.set_entry_date(entry_date)
        self._dirty = False

        try:
            d = datetime.strptime(entry_date, "%Y-%m-%d")
            self.date_label.setText(d.strftime("📓  %A, %B %d, %Y"))
        except ValueError:
            self.date_label.setText(f"📓  {entry_date}")

        self.editor.blockSignals(True)
        if looks_like_html(content):
            self.editor.setHtml(content)
        elif content.lstrip().startswith("#"):
            self.editor.setMarkdown(content)
        else:
            self.editor.setPlainText(content)
        self.editor.blockSignals(False)
        self._set_save_status(True)

    def get_content(self) -> str:
        return self.editor.toHtml()

    def insert_text(self, text: str):
        self.editor.textCursor().insertText(text)
        self.editor.setFocus()

    def insert_html(self, html: str):
        self.editor.textCursor().insertHtml(html)
        self.editor.setFocus()

    def _set_save_status(self, saved: bool):
        if saved:
            self.save_status.setText("✓ Saved")
            self.save_status.setStyleSheet("color: #2e7d32;")
        else:
            self.save_status.setText("● Unsaved")
            self.save_status.setStyleSheet("color: #e65100;")

    def _on_text_changed(self):
        self._dirty = True
        self._set_save_status(False)
        self.content_changed.emit()

    def _autosave(self):
        if self._dirty:
            self.save_requested.emit(self.get_content())
            self._dirty = False
            self._set_save_status(True)

    def _cursor(self) -> QTextCursor:
        return self.editor.textCursor()

    def _merge_char_format(self, fmt: QTextCharFormat):
        cursor = self._cursor()
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        else:
            self.editor.mergeCurrentCharFormat(fmt)

    def _toggle_bold(self):
        cursor = self._cursor()
        fmt = QTextCharFormat()
        current_weight = cursor.charFormat().fontWeight()
        fmt.setFontWeight(QFont.Weight.Bold if current_weight != QFont.Weight.Bold else QFont.Weight.Normal)
        self._merge_char_format(fmt)

    def _toggle_italic(self):
        cursor = self._cursor()
        fmt = QTextCharFormat()
        fmt.setFontItalic(not cursor.charFormat().fontItalic())
        self._merge_char_format(fmt)

    def _insert_bullet_list(self):
        cursor = self._cursor()
        fmt = QTextListFormat()
        fmt.setStyle(QTextListFormat.Style.ListDisc)
        cursor.insertList(fmt)

    def _insert_numbered_list(self):
        cursor = self._cursor()
        fmt = QTextListFormat()
        fmt.setStyle(QTextListFormat.Style.ListDecimal)
        cursor.insertList(fmt)

    def _apply_heading_style(self, index: int):
        sizes = {0: 11, 1: 20, 2: 16, 3: 13}
        cursor = self._cursor()
        char_fmt = QTextCharFormat()
        char_fmt.setFontPointSize(sizes.get(index, 11))
        char_fmt.setFontWeight(QFont.Weight.Bold if index else QFont.Weight.Normal)
        if cursor.hasSelection():
            cursor.mergeCharFormat(char_fmt)
        else:
            self.editor.mergeCurrentCharFormat(char_fmt)

    def _choose_text_color(self):
        color = QColorDialog.getColor(self.editor.textColor(), self, "Choose text color")
        if not color.isValid():
            return
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        self._merge_char_format(fmt)

    def _apply_font_size(self, size: int):
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        self._merge_char_format(fmt)

    def _insert_table(self):
        rows, ok = QInputDialog.getInt(self, "Insert Table", "Rows:", 2, 1, 20)
        if not ok:
            return
        cols, ok = QInputDialog.getInt(self, "Insert Table", "Columns:", 2, 1, 12)
        if not ok:
            return
        cursor = self._cursor()
        table_fmt = QTextTableFormat()
        table_fmt.setBorder(1)
        table_fmt.setCellPadding(4)
        table_fmt.setCellSpacing(0)
        cursor.insertTable(rows, cols, table_fmt)

    def _ensure_rich_text_mode(self):
        cursor = self._cursor()
        if not cursor.hasSelection():
            return
        selected = cursor.selection().toHtml()
        cursor.insertHtml(selected)
