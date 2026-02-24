from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy


class ImagePreview(QWidget):
    def __init__(self):
        super().__init__()
        self._pixmap: QPixmap | None = None
        self._path: str | None = None
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        self.lbl_img = QLabel("Sin vista previa")
        self.lbl_img.setAlignment(Qt.AlignCenter)
        self.lbl_img.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_img.setStyleSheet("border:1px solid #ddd; background:#fafafa;")

        self.lbl_meta = QLabel("")
        self.lbl_meta.setStyleSheet("color:#666;")
        self.lbl_meta.setWordWrap(True)

        lay.addWidget(self.lbl_img, 1)
        lay.addWidget(self.lbl_meta, 0)

    def clear(self):
        self._pixmap = None
        self._path = None
        self.lbl_img.setPixmap(QPixmap())
        self.lbl_img.setText("Sin vista previa")
        self.lbl_meta.setText("")

    def set_image(self, path: str):
        self._path = path
        pm = QPixmap(path)
        if pm.isNull():
            self.clear()
            self.lbl_img.setText("No se pudo abrir la imagen.")
            return
        self._pixmap = pm
        self._update_view()

    def resizeEvent(self, _e):
        self._update_view()

    def _update_view(self):
        if not self._pixmap:
            return
        w, h = self.lbl_img.width(), self.lbl_img.height()
        scaled = self._pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_img.setPixmap(scaled)
        self.lbl_img.setText("")

        p = Path(self._path) if self._path else None
        meta = f"<b>{(p.name if p else '')}</b><br>Tamaño: {self._pixmap.width()}×{self._pixmap.height()} px"
        if p:
            meta += f"<br>Ruta: {str(p)}"
        self.lbl_meta.setText(meta)