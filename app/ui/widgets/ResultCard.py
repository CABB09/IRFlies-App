from __future__ import annotations
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout

from core.predictor import Prediction
from .AgeProbsBars import AgeProbsBars


class ResultCard(QWidget):
    def __init__(self):
        super().__init__()
        self.classes: List[str] = []
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        self.lbl_title = QLabel("Resultado")
        self.lbl_title.setStyleSheet("font-weight:600; font-size:16px;")

        self.lbl_top = QLabel("—")
        self.lbl_top.setAlignment(Qt.AlignLeft)
        self.lbl_top.setStyleSheet("font-size:24px;")

        self.lbl_sub = QLabel("")
        self.lbl_sub.setStyleSheet("color:#666;")

        self.bars = AgeProbsBars()

        lay.addWidget(self.lbl_title)
        lay.addWidget(self.lbl_top)
        lay.addWidget(self.lbl_sub)
        lay.addWidget(self.bars)

    def set_classes(self, classes: List[str]):
        self.classes = classes
        self.bars.set_classes(classes)
        self.lbl_top.setText("—")
        self.lbl_sub.setText("")

    def set_prediction(self, p: Prediction):
        t1 = f"Edad: {p.top1_class}  |  {p.top1_prob*100:.1f}%"
        t2 = ""
        if p.top2_class is not None and p.top2_prob is not None:
            t2 = f"2ª mejor: {p.top2_class} ({p.top2_prob*100:.1f}%)  ·  gap {p.gap_pp*100:.1f} pp  ·  conf: {p.confidence}"
        self.lbl_top.setText(t1)
        self.lbl_sub.setText(t2)
        self.bars.set_probs(p.full_probs)