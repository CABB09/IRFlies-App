from __future__ import annotations
from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar


class BusyOverlay(QWidget):
    """
    Overlay semitransparente que cubre al padre y bloquea clicks.
    Uso:
        overlay = BusyOverlay(parent_widget)
        overlay.show_busy("Clasificando…")
        overlay.hide_busy()
    """
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,120);")
        self.setVisible(False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        self.lbl = QLabel("Trabajando…")
        self.lbl.setStyleSheet("color: white; font-size: 16px;")
        self.lbl.setAlignment(Qt.AlignHCenter)

        self.bar = QProgressBar()
        self.bar.setRange(0, 0)  # indeterminado
        self.bar.setTextVisible(False)
        self.bar.setFixedWidth(280)
        self.bar.setStyleSheet("QProgressBar {background: rgba(255,255,255,60);} QProgressBar::chunk {background: white;}")

        c = QWidget()
        c_lay = QVBoxLayout(c)
        c_lay.setContentsMargins(20, 20, 20, 20)
        c_lay.setSpacing(10)
        c_lay.addWidget(self.lbl, alignment=Qt.AlignHCenter)
        c_lay.addWidget(self.bar, alignment=Qt.AlignHCenter)

        lay.addStretch(1)
        lay.addWidget(c, alignment=Qt.AlignHCenter)
        lay.addStretch(1)

        # seguir el tamaño del padre
        self._resize_to_parent()
        parent.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if obj is self.parent() and ev.type() in (QEvent.Resize, QEvent.Move, QEvent.Show):
            self._resize_to_parent()
        return super().eventFilter(obj, ev)

    def _resize_to_parent(self):
        if self.parent():
            self.setGeometry(self.parent().rect())

    def show_busy(self, text: str = "Trabajando…"):
        self.lbl.setText(text)
        self.setVisible(True)
        self.raise_()

    def hide_busy(self):
        self.setVisible(False)