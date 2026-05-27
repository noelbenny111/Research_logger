"""
Dialog for editing inline image size or crop settings.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QComboBox, QSpinBox, QCheckBox, QPushButton
)


class ImagePropertiesDialog(QDialog):
    def __init__(self, filename: str, width: int, height: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🖼 Image Properties")
        self.setMinimumWidth(380)
        self._build_ui(filename, width, height)

    def _build_ui(self, filename: str, width: int, height: int):
        layout = QVBoxLayout(self)

        info = QLabel(f"{filename}\nCurrent size: {width} x {height}px")
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Resize", "Crop to square"])
        form.addRow("Action:", self.mode_combo)

        self.resize_width = QSpinBox()
        self.resize_width.setRange(1, 10000)
        self.resize_width.setValue(width)
        form.addRow("Width:", self.resize_width)

        self.resize_height = QSpinBox()
        self.resize_height.setRange(1, 10000)
        self.resize_height.setValue(height)
        form.addRow("Height:", self.resize_height)

        self.keep_ratio = QCheckBox("Keep aspect ratio")
        self.keep_ratio.setChecked(True)
        form.addRow(self.keep_ratio)

        layout.addLayout(form)

        hint = QLabel("Crop to square keeps the center portion of the image.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("Apply")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def result_data(self) -> dict:
        return {
            "mode": self.mode_combo.currentText(),
            "width": self.resize_width.value(),
            "height": self.resize_height.value(),
            "keep_ratio": self.keep_ratio.isChecked(),
        }