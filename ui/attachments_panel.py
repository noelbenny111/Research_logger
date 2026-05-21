"""
Right panel: attachments list with drag-and-drop and file browser support.
"""
import os
import shutil
from datetime import date
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QFileDialog, QMenu,
    QAbstractItemView, QFrame, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize, QUrl, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QColor, QImage


# ─── Base attachment dir ───────────────────────────────────────────────────────

def get_attachment_dir(entry_date: str) -> Path:
    base = Path(__file__).parent.parent / "attachments" / entry_date
    base.mkdir(parents=True, exist_ok=True)
    return base


def save_inline_image(entry_date: str, image: QImage, suggested_name: str = "pasted-image.png") -> Path:
    """Store a clipboard image in the attachment folder and return the saved path."""
    dest_dir = get_attachment_dir(entry_date)
    filename = Path(suggested_name).name or "pasted-image.png"
    stem = Path(filename).stem or "pasted-image"
    suffix = Path(filename).suffix or ".png"
    dest_path = dest_dir / f"{stem}{suffix}"

    counter = 1
    while dest_path.exists():
        dest_path = dest_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    image.save(str(dest_path))
    return dest_path


# ─── Attachment Item Widget ────────────────────────────────────────────────────

def _icon_for_type(file_type: str) -> str:
    icons = {
        "pdf": "📄", "image": "🖼", "video": "🎬",
        "audio": "🎵", "code": "💻", "archive": "📦",
        "file": "📎",
    }
    return icons.get(file_type, "📎")


def _detect_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"}:
        return "image"
    if ext in {".mp4", ".avi", ".mov", ".mkv"}:
        return "video"
    if ext in {".mp3", ".wav", ".flac", ".ogg"}:
        return "audio"
    if ext in {".py", ".js", ".cpp", ".c", ".h", ".java", ".rs", ".go", ".ts"}:
        return "code"
    if ext in {".zip", ".tar", ".gz", ".7z", ".rar"}:
        return "archive"
    return "file"


# ─── AttachmentsPanel ─────────────────────────────────────────────────────────

class AttachmentsPanel(QWidget):
    attachment_added = Signal(str)  # emits markdown link text

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._current_date = date.today().isoformat()
        self.setAcceptDrops(True)
        self.setFixedWidth(230)
        self._build_ui()

    # ─── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QLabel("📎  Attachments")
        header.setProperty("sidebarSection", True)
        layout.addWidget(header)

        # Drop zone hint
        self.drop_hint = QLabel("⬇ Drop files here\nor click Add")
        self.drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_hint.setObjectName("dropHint")
        self.drop_hint.setMinimumHeight(55)
        layout.addWidget(self.drop_hint)

        # File list
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.itemDoubleClicked.connect(self._open_attachment)
        self.list_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.list_widget)

        # Buttons
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("+ Add File")
        self.add_btn.setFixedHeight(28)
        self.add_btn.clicked.connect(self._browse_file)
        btn_row.addWidget(self.add_btn)

        self.open_dir_btn = QPushButton("📁 Folder")
        self.open_dir_btn.setFixedHeight(28)
        self.open_dir_btn.clicked.connect(self._open_attachment_dir)
        btn_row.addWidget(self.open_dir_btn)
        layout.addLayout(btn_row)

    # ─── Public API ────────────────────────────────────────────────────────────

    def load_attachments(self, entry_date: str, attachments: list):
        self._current_date = entry_date
        self.list_widget.clear()
        for att in attachments:
            self._add_list_item(att)

    # ─── Internal ──────────────────────────────────────────────────────────────

    def _add_list_item(self, att: dict):
        icon = _icon_for_type(att.get("file_type", "file"))
        item = QListWidgetItem(f"{icon} {att['filename']}")
        item.setData(Qt.ItemDataRole.UserRole, att)
        item.setToolTip(att.get("filepath", ""))
        self.list_widget.addItem(item)

    def _browse_file(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Attach Files", "",
            "All Files (*);;PDFs (*.pdf);;Images (*.png *.jpg *.jpeg *.gif);;Documents (*.doc *.docx *.txt)"
        )
        for path in paths:
            self._attach_file(path)

    def _attach_file(self, source_path: str):
        if not os.path.isfile(source_path):
            return
        filename = os.path.basename(source_path)
        dest_dir = get_attachment_dir(self._current_date)
        dest_path = dest_dir / filename

        # Copy file to attachments folder (avoid duplicate names)
        counter = 1
        while dest_path.exists():
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            dest_path = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        shutil.copy2(source_path, dest_path)

        file_type = _detect_type(filename)
        att_id = self.db.add_attachment(
            self._current_date,
            dest_path.name,
            str(dest_path),
            file_type
        )

        att = {
            "id": att_id,
            "filename": dest_path.name,
            "filepath": str(dest_path),
            "file_type": file_type
        }
        self._add_list_item(att)

        # Emit markdown link for insertion into editor
        rel_path = str(dest_path).replace("\\", "/")
        if file_type == "image":
            link_text = f'<p><img src="file:///{rel_path}" alt="{dest_path.name}"></p>'
        else:
            link_text = f'<p><a href="file:///{rel_path}">📎 {dest_path.name}</a></p>'
        self.attachment_added.emit(link_text)

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        att = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        open_action = menu.addAction("🗂 Open File")
        remove_action = menu.addAction("🗑 Remove")
        action = menu.exec(self.list_widget.mapToGlobal(pos))
        if action == open_action:
            self._open_file(att["filepath"])
        elif action == remove_action:
            self._remove_attachment(item, att)

    def _open_attachment(self, item: QListWidgetItem):
        att = item.data(Qt.ItemDataRole.UserRole)
        self._open_file(att["filepath"])

    def _open_file(self, filepath: str):
        import subprocess, sys
        if sys.platform == "win32":
            os.startfile(filepath)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", filepath])
        else:
            subprocess.Popen(["xdg-open", filepath])

    def _remove_attachment(self, item: QListWidgetItem, att: dict):
        reply = QMessageBox.question(
            self, "Remove Attachment",
            f"Remove '{att['filename']}' from this entry?\n(File will NOT be deleted from disk)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.remove_attachment(att["id"])
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)

    def _open_attachment_dir(self):
        att_dir = get_attachment_dir(self._current_date)
        self._open_file(str(att_dir))

    # ─── Drag and Drop ─────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_hint.setStyleSheet("background-color: #dce9ff; border-radius: 4px;")

    def dragLeaveEvent(self, event):
        self.drop_hint.setStyleSheet("")

    def dropEvent(self, event: QDropEvent):
        self.drop_hint.setStyleSheet("")
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self._attach_file(url.toLocalFile())
        event.acceptProposedAction()
