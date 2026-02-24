from __future__ import annotations
from typing import Dict, List

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar


class AgeProbsBars(QWidget):
    def __init__(self):
        super().__init__()
        self.classes: List[str] = []
        self.bars: Dict[str, QProgressBar] = {}
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(4)

    def set_classes(self, classes: List[str]):
        # recrea layout
        for i in reversed(range(self._root.count())):
            item = self._root.itemAt(i).widget()
            if item:
                item.setParent(None)
        self.classes = classes
        self.bars = {}
        for c in classes:
            row = QHBoxLayout()
            lab = QLabel(c)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            row.addWidget(lab, 0)
            row.addWidget(bar, 1)
            cont = QWidget()
            cont.setLayout(row)
            self._root.addWidget(cont)
            self.bars[c] = bar

    def set_probs(self, probs: Dict[str, float]):
        if not self.classes:
            return
        for c in self.classes:
            p = probs.get(c, 0.0)
            self.bars[c].setValue(int(round(p * 100)))