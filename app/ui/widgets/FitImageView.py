from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QScrollArea, QLabel, QVBoxLayout, QSizePolicy

class FitImageView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._orig: QPixmap | None = None

        self._label = QLabel("Sin imagen")
        self._label.setAlignment(Qt.AlignCenter)
        # Claves para evitar loops:
        self._label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self._label.setScaledContents(True)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._label)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._scroll)

    def set_pixmap(self, pm: QPixmap | None):
        self._orig = pm
        if pm is None or pm.isNull():
            self._label.setText("Sin imagen")
            self._label.clear()
            return
        self._apply_fit()

    def resizeEvent(self, _e):
        self._apply_fit()

    def _apply_fit(self):
        if not self._orig or self._orig.isNull():
            return
        vw = max(1, self._scroll.viewport().width())
        vh = max(1, self._scroll.viewport().height())
        scaled = self._orig.scaled(vw, vh, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._label.setPixmap(scaled)
        # No llamar setText aquí

    # Evita zoom accidental por rueda:
    def wheelEvent(self, e):
        # Si quieres permitir scroll normal, deja pasar al scroll:
        e.ignore()