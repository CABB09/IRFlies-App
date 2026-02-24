# app/ui/widgets/SpeciesSelector.py
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton


class SpeciesSelector(QWidget):
    sig_changed = Signal(str)  # key

    def __init__(self, species_keys: list[str]):
        super().__init__()
        self.keys = species_keys
        self.current: str | None = None
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.btns: list[QPushButton] = []
        for k in self.keys:
            b = QPushButton(k)
            b.setCheckable(True)
            b.clicked.connect(lambda checked, key=k: self._set_current(key))
            self.btns.append(b)
            lay.addWidget(b)

    def _set_current(self, key: str):
        self.current = key
        for b in self.btns:
            b.setChecked(b.text() == key)
        self.sig_changed.emit(key)