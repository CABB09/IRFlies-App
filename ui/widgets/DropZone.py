from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFileDialog, QPushButton

from core.utils import iter_images_in_paths


class DropZone(QWidget):
    sig_file = Signal(str)
    sig_many = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        self.lbl = QLabel("Arrastra aquí imágenes\n(o haz clic en 'Seleccionar archivos…')")
        self.lbl.setAlignment(Qt.AlignCenter)
        self.lbl.setStyleSheet("border: 2px dashed #7a7a7a; padding: 30px; border-radius: 10px;")

        self.btn = QPushButton("Seleccionar archivos…")
        self.btn.clicked.connect(self._open_files)

        lay.addWidget(self.lbl)
        lay.addWidget(self.btn, alignment=Qt.AlignCenter)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        urls = e.mimeData().urls()
        paths = [u.toLocalFile() for u in urls]
        imgs = iter_images_in_paths(paths)
        if not imgs:
            return
        if len(imgs) == 1:
            self.sig_file.emit(imgs[0])
        else:
            self.sig_many.emit(imgs)

    def _open_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Selecciona imágenes", "", "Imágenes (*.jpg *.jpeg *.png *.bmp)")
        if not files:
            return
        imgs = iter_images_in_paths(files)
        if len(imgs) == 1:
            self.sig_file.emit(imgs[0])
        elif len(imgs) > 1:
            self.sig_many.emit(imgs)